from sqlalchemy.orm import Session
from sqlalchemy import func, or_
from datetime import datetime
from . import models, schemas

def get_deals(db: Session, status=None, search=None, skip=0, limit=100):
    query = db.query(models.Deal)
    if status: query = query.filter(models.Deal.status == status)
    if search: query = query.filter(or_(models.Deal.name.ilike(f"%{search}%"), models.Deal.broker_name.ilike(f"%{search}%")))
    deals = query.order_by(models.Deal.updated_at.desc()).offset(skip).limit(limit).all()
    for d in deals:
        d.document_count = len(d.documents)
        d.task_count = len([t for t in d.tasks if t.status != "completed"])
    return deals

def get_deal_stats(db: Session):
    stats = {"vetting": 0, "pipeline": 0, "due_diligence": 0, "current_operations": 0, "on_hold": 0, "total": 0, "total_value": 0, "total_beds": 0, "total_properties": 0}
    for r in db.query(models.Deal.status, func.count(models.Deal.id), func.sum(models.Deal.asking_price), func.sum(models.Deal.total_beds)).group_by(models.Deal.status).all():
        if r[0] in stats:
            stats[r[0]] = r[1]
            stats["total"] += r[1]
            if r[2]: stats["total_value"] += r[2]
            if r[3]: stats["total_beds"] += r[3]
    # Count total properties across all deals
    stats["total_properties"] = db.query(func.count(models.Property.id)).scalar() or 0
    return stats

def get_deal(db: Session, deal_id: int):
    deal = db.query(models.Deal).filter(models.Deal.id == deal_id).first()
    if deal:
        deal.document_count = len(deal.documents)
        deal.task_count = len([t for t in deal.tasks if t.status != "completed"])
    return deal

def create_deal(db: Session, deal: schemas.DealCreate):
    db_deal = models.Deal(**deal.model_dump())
    db.add(db_deal)
    db.commit()
    db.refresh(db_deal)
    log_activity(db, db_deal.id, "created", f"Deal '{db_deal.name}' created")
    if db_deal.asking_price and db_deal.total_beds:
        db_deal.price_per_bed = db_deal.asking_price / db_deal.total_beds
        db.commit()
    return db_deal

def update_deal(db: Session, deal_id: int, deal: schemas.DealUpdate):
    db_deal = db.query(models.Deal).filter(models.Deal.id == deal_id).first()
    if not db_deal: return None
    data = deal.model_dump(exclude_unset=True)
    if "status" in data and data["status"] != db_deal.status:
        log_activity(db, deal_id, "status_changed", f"Status: {db_deal.status} -> {data['status']}")
        db_deal.stage_changed_at = datetime.utcnow()
    for k, v in data.items(): setattr(db_deal, k, v)
    db_deal.updated_at = datetime.utcnow()
    if db_deal.asking_price and db_deal.total_beds: db_deal.price_per_bed = db_deal.asking_price / db_deal.total_beds
    db.commit()
    db.refresh(db_deal)
    return db_deal

def update_deal_status(db: Session, deal_id: int, status: str):
    db_deal = db.query(models.Deal).filter(models.Deal.id == deal_id).first()
    if not db_deal: return None
    old = db_deal.status
    db_deal.status = status
    db_deal.stage_changed_at = datetime.utcnow()
    db_deal.updated_at = datetime.utcnow()
    db.commit()
    log_activity(db, deal_id, "status_changed", f"Status: {old} -> {status}")
    return db_deal

def delete_deal(db: Session, deal_id: int):
    db_deal = db.query(models.Deal).filter(models.Deal.id == deal_id).first()
    if not db_deal: return False
    db.delete(db_deal)
    db.commit()
    return True

def create_property(db: Session, deal_id: int, prop: schemas.PropertyCreate):
    db_prop = models.Property(deal_id=deal_id, **prop.model_dump())
    db.add(db_prop)
    db.commit()
    db.refresh(db_prop)
    update_deal_counts(db, deal_id)
    log_activity(db, deal_id, "property_added", f"Property '{db_prop.name}' added")
    return db_prop

def delete_property(db: Session, property_id: int):
    p = db.query(models.Property).filter(models.Property.id == property_id).first()
    if not p: return False
    deal_id = p.deal_id
    db.delete(p)
    db.commit()
    update_deal_counts(db, deal_id)
    return True

def update_deal_counts(db: Session, deal_id: int):
    props = db.query(models.Property).filter(models.Property.deal_id == deal_id).all()
    deal = db.query(models.Deal).filter(models.Deal.id == deal_id).first()
    if deal:
        deal.property_count = len(props)
        deal.total_beds = sum(p.licensed_beds or 0 for p in props)
        if deal.total_beds and deal.asking_price: deal.price_per_bed = deal.asking_price / deal.total_beds
        db.commit()

def get_documents(db: Session, deal_id: int):
    return db.query(models.Document).filter(models.Document.deal_id == deal_id).order_by(models.Document.uploaded_at.desc()).all()

def get_document(db: Session, doc_id: int):
    return db.query(models.Document).filter(models.Document.id == doc_id).first()

def create_document(db: Session, deal_id: int, doc: schemas.DocumentCreate, property_id: int = None):
    doc_data = doc.model_dump()
    db_doc = models.Document(deal_id=deal_id, property_id=property_id, **doc_data)
    db.add(db_doc)
    db.commit()
    db.refresh(db_doc)
    return db_doc


def update_document_parsing_status(db: Session, doc_id: int, status: str, error: str = None):
    """Update document parsing status"""
    doc = db.query(models.Document).filter(models.Document.id == doc_id).first()
    if doc:
        doc.parsing_status = status
        if error:
            doc.parsing_error = error
        db.commit()
        db.refresh(doc)
    return doc


def get_document_by_checksum(db: Session, deal_id: int, checksum: str):
    """Find document by checksum within a deal"""
    return db.query(models.Document).filter(
        models.Document.deal_id == deal_id,
        models.Document.checksum == checksum
    ).first()

def update_doc_analysis(db: Session, doc_id: int, summary: str):
    doc = db.query(models.Document).filter(models.Document.id == doc_id).first()
    if doc:
        doc.analyzed = True
        doc.analysis_summary = summary
        db.commit()
        log_activity(db, doc.deal_id, "document_analyzed", f"Document analyzed")

def delete_document(db: Session, doc_id: int):
    doc = db.query(models.Document).filter(models.Document.id == doc_id).first()
    if not doc: return False
    db.delete(doc)
    db.commit()
    return True

def log_activity(db: Session, deal_id: int, action: str, desc: str):
    db.add(models.Activity(deal_id=deal_id, action=action, description=desc))
    db.commit()

def get_activity(db: Session, deal_id: int, limit=50):
    return db.query(models.Activity).filter(models.Activity.deal_id == deal_id).order_by(models.Activity.created_at.desc()).limit(limit).all()

def get_tasks(db: Session, deal_id: int):
    return db.query(models.Task).filter(models.Task.deal_id == deal_id).order_by(models.Task.due_date.asc()).all()

def create_task(db: Session, deal_id: int, task: schemas.TaskCreate):
    db_task = models.Task(deal_id=deal_id, **task.model_dump())
    db.add(db_task)
    db.commit()
    db.refresh(db_task)
    log_activity(db, deal_id, "task_created", f"Task '{task.title}' created")
    return db_task

def update_task(db: Session, task_id: int, task: schemas.TaskUpdate):
    db_task = db.query(models.Task).filter(models.Task.id == task_id).first()
    if not db_task: return None
    data = task.model_dump(exclude_unset=True)
    if data.get("status") == "completed" and db_task.status != "completed":
        data["completed_at"] = datetime.utcnow()
        log_activity(db, db_task.deal_id, "task_completed", f"Task '{db_task.title}' completed")
    for k, v in data.items(): setattr(db_task, k, v)
    db.commit()
    db.refresh(db_task)
    return db_task

def calc_valuation(deal):
    v = {"deal_id": deal.id, "income_approach": None, "market_approach": None, "summary": {}}
    caps = {"SNF": (0.10, 0.125, 0.15), "ALF": (0.07, 0.085, 0.10), "ILF": (0.055, 0.065, 0.075)}
    ppb = {"SNF": (40000, 75000, 120000), "ALF": (150000, 250000, 400000), "ILF": (200000, 350000, 500000)}
    dt = deal.deal_type or "SNF"
    c = caps.get(dt, caps["SNF"])
    p = ppb.get(dt, ppb["SNF"])
    if deal.ebitdar and deal.ebitdar > 0:
        v["income_approach"] = {"ebitdar": deal.ebitdar, "low_cap": {"cap_rate": c[2], "value": deal.ebitdar/c[2]}, "mid_cap": {"cap_rate": c[1], "value": deal.ebitdar/c[1]}, "high_cap": {"cap_rate": c[0], "value": deal.ebitdar/c[0]}}
    if deal.total_beds and deal.total_beds > 0:
        v["market_approach"] = {"total_beds": deal.total_beds, "low": {"price_per_bed": p[0], "value": deal.total_beds*p[0]}, "mid": {"price_per_bed": p[1], "value": deal.total_beds*p[1]}, "high": {"price_per_bed": p[2], "value": deal.total_beds*p[2]}}
    vals = []
    if v["income_approach"]: vals.append(v["income_approach"]["mid_cap"]["value"])
    if v["market_approach"]: vals.append(v["market_approach"]["mid"]["value"])
    if vals:
        avg = sum(vals)/len(vals)
        v["summary"]["estimated_value"] = avg
        v["summary"]["asking_price"] = deal.asking_price
        if deal.asking_price:
            spread = (avg - deal.asking_price)/deal.asking_price * 100
            v["summary"]["spread_pct"] = round(spread, 2)
            v["summary"]["recommendation"] = "Potentially Undervalued" if spread > 10 else ("Potentially Overvalued" if spread < -10 else "Fair Value Range")
    return v


# ============================================================================
# DOCUMENT ANALYSIS CRUD
# ============================================================================

def create_parsed_artifact(db: Session, document_id: int, artifact_type: str,
                          page_number: int = None, content: str = None,
                          content_json: dict = None, confidence: float = None):
    """Create a parsed artifact from document"""
    artifact = models.ParsedArtifact(
        document_id=document_id,
        artifact_type=artifact_type,
        page_number=page_number,
        content=content,
        content_json=content_json,
        confidence=confidence
    )
    db.add(artifact)
    db.commit()
    db.refresh(artifact)
    return artifact


def get_parsed_artifacts(db: Session, document_id: int):
    """Get all parsed artifacts for a document"""
    return db.query(models.ParsedArtifact).filter(
        models.ParsedArtifact.document_id == document_id
    ).order_by(models.ParsedArtifact.page_number).all()


def create_extracted_field(db: Session, document_id: int, deal_id: int,
                          field_key: str, field_value: str, **kwargs):
    """Create an extracted field with provenance"""
    field = models.ExtractedField(
        document_id=document_id,
        deal_id=deal_id,
        field_key=field_key,
        field_value=field_value,
        **kwargs
    )
    db.add(field)
    db.commit()
    db.refresh(field)
    return field


def get_extracted_fields(db: Session, deal_id: int, document_id: int = None):
    """Get extracted fields for a deal, optionally filtered by document"""
    query = db.query(models.ExtractedField).filter(
        models.ExtractedField.deal_id == deal_id
    )
    if document_id:
        query = query.filter(models.ExtractedField.document_id == document_id)
    return query.order_by(models.ExtractedField.field_key).all()


def update_extracted_field(db: Session, field_id: int, updates: dict, override_by: str = None):
    """Update an extracted field and optionally log override"""
    field = db.query(models.ExtractedField).filter(models.ExtractedField.id == field_id).first()
    if not field:
        return None

    old_value = field.field_value

    for k, v in updates.items():
        if hasattr(field, k):
            setattr(field, k, v)

    # Log override if value changed and override_by provided
    if override_by and 'field_value' in updates and updates['field_value'] != old_value:
        override = models.FieldOverride(
            deal_id=field.deal_id,
            entity_type='extracted_field',
            entity_id=field_id,
            field_name='field_value',
            old_value=old_value,
            new_value=updates['field_value'],
            overridden_by=override_by
        )
        db.add(override)

    db.commit()
    db.refresh(field)
    return field


def create_claim(db: Session, document_id: int, deal_id: int, claim_data: dict):
    """Create a claim from OM/CIM document"""
    claim = models.Claim(
        document_id=document_id,
        deal_id=deal_id,
        **claim_data
    )
    db.add(claim)
    db.commit()
    db.refresh(claim)
    return claim


def get_claims(db: Session, deal_id: int, document_id: int = None, category: str = None):
    """Get claims for a deal"""
    query = db.query(models.Claim).filter(models.Claim.deal_id == deal_id)
    if document_id:
        query = query.filter(models.Claim.document_id == document_id)
    if category:
        query = query.filter(models.Claim.claim_category == category)
    return query.order_by(models.Claim.claim_category, models.Claim.claim_type).all()


def update_claim_verification(db: Session, claim_id: int, verification_data: dict, verified_by: str = None):
    """Update claim verification status"""
    claim = db.query(models.Claim).filter(models.Claim.id == claim_id).first()
    if not claim:
        return None

    for k, v in verification_data.items():
        if hasattr(claim, k):
            setattr(claim, k, v)

    # Calculate variance if verified_value provided
    if verification_data.get('verified_value') and claim.numeric_value:
        try:
            verified_numeric = float(verification_data['verified_value'].replace(',', '').replace('$', ''))
            claim.variance = verified_numeric - claim.numeric_value
            if claim.numeric_value != 0:
                claim.variance_pct = (claim.variance / abs(claim.numeric_value)) * 100
        except:
            pass

    db.commit()
    db.refresh(claim)
    return claim


def get_standard_accounts(db: Session, category: str = None):
    """Get standard chart of accounts"""
    query = db.query(models.StandardAccount).filter(models.StandardAccount.is_active == True)
    if category:
        query = query.filter(models.StandardAccount.category == category)
    return query.order_by(models.StandardAccount.display_order).all()


def create_coa_mapping(db: Session, deal_id: int, mapping_data: dict):
    """Create a COA mapping"""
    mapping = models.COAMapping(deal_id=deal_id, **mapping_data)
    db.add(mapping)
    db.commit()
    db.refresh(mapping)
    return mapping


def get_coa_mappings(db: Session, deal_id: int, status: str = None):
    """Get COA mappings for a deal"""
    query = db.query(models.COAMapping).filter(models.COAMapping.deal_id == deal_id)
    if status:
        query = query.filter(models.COAMapping.mapping_status == status)
    return query.order_by(models.COAMapping.seller_account_name).all()


def approve_coa_mapping(db: Session, mapping_id: int, standard_account_id: int,
                       standard_account_code: str, approved_by: str):
    """Approve a COA mapping"""
    mapping = db.query(models.COAMapping).filter(models.COAMapping.id == mapping_id).first()
    if not mapping:
        return None

    mapping.standard_account_id = standard_account_id
    mapping.standard_account_code = standard_account_code
    mapping.mapping_status = 'approved'
    mapping.approved_by = approved_by
    mapping.approved_at = datetime.utcnow()
    db.commit()
    db.refresh(mapping)
    return mapping


def create_financial_line_item(db: Session, deal_id: int, line_data: dict):
    """Create a financial line item"""
    item = models.FinancialLineItem(deal_id=deal_id, **line_data)
    db.add(item)
    db.commit()
    db.refresh(item)
    return item


def get_financial_line_items(db: Session, deal_id: int, period_type: str = None):
    """Get financial line items for a deal"""
    query = db.query(models.FinancialLineItem).filter(
        models.FinancialLineItem.deal_id == deal_id
    )
    if period_type:
        query = query.filter(models.FinancialLineItem.period_type == period_type)
    return query.order_by(
        models.FinancialLineItem.period_start,
        models.FinancialLineItem.standard_account_code
    ).all()


def create_scenario(db: Session, deal_id: int, scenario_data: dict):
    """Create a pro forma scenario"""
    scenario = models.Scenario(deal_id=deal_id, **scenario_data)
    db.add(scenario)
    db.commit()
    db.refresh(scenario)
    return scenario


def get_scenarios(db: Session, deal_id: int):
    """Get all scenarios for a deal"""
    return db.query(models.Scenario).filter(
        models.Scenario.deal_id == deal_id
    ).order_by(models.Scenario.created_at).all()


def update_scenario(db: Session, scenario_id: int, updates: dict):
    """Update a scenario"""
    scenario = db.query(models.Scenario).filter(models.Scenario.id == scenario_id).first()
    if not scenario:
        return None

    for k, v in updates.items():
        if hasattr(scenario, k):
            setattr(scenario, k, v)

    db.commit()
    db.refresh(scenario)
    return scenario


def create_risk_flag(db: Session, deal_id: int, risk_data: dict):
    """Create a risk flag"""
    risk = models.RiskFlag(deal_id=deal_id, **risk_data)
    db.add(risk)
    db.commit()
    db.refresh(risk)
    return risk


def get_risk_flags(db: Session, deal_id: int, category: str = None, status: str = None):
    """Get risk flags for a deal"""
    query = db.query(models.RiskFlag).filter(models.RiskFlag.deal_id == deal_id)
    if category:
        query = query.filter(models.RiskFlag.risk_category == category)
    if status:
        query = query.filter(models.RiskFlag.status == status)
    return query.order_by(
        models.RiskFlag.severity.desc(),
        models.RiskFlag.created_at.desc()
    ).all()


def update_risk_flag(db: Session, risk_id: int, updates: dict):
    """Update a risk flag"""
    risk = db.query(models.RiskFlag).filter(models.RiskFlag.id == risk_id).first()
    if not risk:
        return None

    for k, v in updates.items():
        if hasattr(risk, k):
            setattr(risk, k, v)

    if updates.get('status') in ['mitigated', 'accepted']:
        risk.resolved_at = datetime.utcnow()

    db.commit()
    db.refresh(risk)
    return risk


def get_or_create_scorecard(db: Session, deal_id: int):
    """Get or create deal scorecard"""
    scorecard = db.query(models.DealScorecard).filter(
        models.DealScorecard.deal_id == deal_id
    ).first()

    if not scorecard:
        scorecard = models.DealScorecard(deal_id=deal_id)
        db.add(scorecard)
        db.commit()
        db.refresh(scorecard)

    return scorecard


def update_scorecard(db: Session, deal_id: int, scores: dict):
    """Update deal scorecard"""
    scorecard = get_or_create_scorecard(db, deal_id)

    for k, v in scores.items():
        if hasattr(scorecard, k):
            setattr(scorecard, k, v)

    db.commit()
    db.refresh(scorecard)
    return scorecard


def create_analysis_job(db: Session, job_type: str, deal_id: int = None, document_id: int = None):
    """Create an analysis job"""
    job = models.AnalysisJob(
        job_type=job_type,
        deal_id=deal_id,
        document_id=document_id,
        status='pending'
    )
    db.add(job)
    db.commit()
    db.refresh(job)
    return job


def update_analysis_job(db: Session, job_id: int, status: str, progress: int = None,
                       error: str = None, result: dict = None):
    """Update analysis job status"""
    job = db.query(models.AnalysisJob).filter(models.AnalysisJob.id == job_id).first()
    if not job:
        return None

    job.status = status
    if progress is not None:
        job.progress = progress
    if error:
        job.error_message = error
    if result:
        job.result = result

    if status == 'running' and not job.started_at:
        job.started_at = datetime.utcnow()
    elif status in ['completed', 'failed']:
        job.completed_at = datetime.utcnow()

    db.commit()
    db.refresh(job)
    return job


def get_analysis_jobs(db: Session, deal_id: int = None, document_id: int = None, status: str = None):
    """Get analysis jobs"""
    query = db.query(models.AnalysisJob)
    if deal_id:
        query = query.filter(models.AnalysisJob.deal_id == deal_id)
    if document_id:
        query = query.filter(models.AnalysisJob.document_id == document_id)
    if status:
        query = query.filter(models.AnalysisJob.status == status)
    return query.order_by(models.AnalysisJob.created_at.desc()).all()


# ============================================================================
# WELCOME NIGHTS PRESENTATION BUILDER CRUD
# ============================================================================

# Brand CRUD
def get_brands(db: Session):
    """Get all brands"""
    return db.query(models.Brand).order_by(models.Brand.name).all()


def get_brand(db: Session, brand_id: int):
    """Get a brand by ID"""
    return db.query(models.Brand).filter(models.Brand.id == brand_id).first()


def get_brand_by_slug(db: Session, slug: str):
    """Get a brand by slug"""
    return db.query(models.Brand).filter(models.Brand.slug == slug).first()


def create_brand(db: Session, brand: schemas.BrandCreate):
    """Create a new brand"""
    db_brand = models.Brand(**brand.model_dump())
    db.add(db_brand)
    db.commit()
    db.refresh(db_brand)
    return db_brand


def update_brand(db: Session, brand_id: int, brand: schemas.BrandUpdate):
    """Update a brand"""
    db_brand = db.query(models.Brand).filter(models.Brand.id == brand_id).first()
    if not db_brand:
        return None
    for k, v in brand.model_dump(exclude_unset=True).items():
        setattr(db_brand, k, v)
    db.commit()
    db.refresh(db_brand)
    return db_brand


# Facility CRUD
def get_wn_facilities(db: Session, brand_id: int = None, search: str = None):
    """Get facilities, optionally filtered by brand"""
    query = db.query(models.WNFacility)
    if brand_id:
        query = query.filter(models.WNFacility.brand_id == brand_id)
    if search:
        query = query.filter(models.WNFacility.name.ilike(f"%{search}%"))
    return query.order_by(models.WNFacility.name).all()


def get_wn_facility(db: Session, facility_id: int):
    """Get a facility by ID"""
    return db.query(models.WNFacility).filter(models.WNFacility.id == facility_id).first()


def create_wn_facility(db: Session, facility: schemas.WNFacilityCreate):
    """Create a new facility"""
    db_facility = models.WNFacility(**facility.model_dump())
    db.add(db_facility)
    db.commit()
    db.refresh(db_facility)
    return db_facility


def update_wn_facility(db: Session, facility_id: int, facility: schemas.WNFacilityUpdate):
    """Update a facility"""
    db_facility = db.query(models.WNFacility).filter(models.WNFacility.id == facility_id).first()
    if not db_facility:
        return None
    for k, v in facility.model_dump(exclude_unset=True).items():
        setattr(db_facility, k, v)
    db.commit()
    db.refresh(db_facility)
    return db_facility


def delete_wn_facility(db: Session, facility_id: int):
    """Delete a facility"""
    db_facility = db.query(models.WNFacility).filter(models.WNFacility.id == facility_id).first()
    if not db_facility:
        return False
    db.delete(db_facility)
    db.commit()
    return True


# Asset CRUD
def get_wn_assets(db: Session, brand_id: int = None, asset_type: str = None):
    """Get assets, optionally filtered by brand and type"""
    query = db.query(models.WNAsset)
    if brand_id:
        query = query.filter(models.WNAsset.brand_id == brand_id)
    if asset_type:
        query = query.filter(models.WNAsset.asset_type == asset_type)
    return query.order_by(models.WNAsset.created_at.desc()).all()


def get_wn_asset(db: Session, asset_id: int):
    """Get an asset by ID"""
    return db.query(models.WNAsset).filter(models.WNAsset.id == asset_id).first()


def create_wn_asset(db: Session, asset: schemas.WNAssetCreate):
    """Create a new asset"""
    db_asset = models.WNAsset(**asset.model_dump())
    db.add(db_asset)
    db.commit()
    db.refresh(db_asset)
    return db_asset


def delete_wn_asset(db: Session, asset_id: int):
    """Delete an asset"""
    db_asset = db.query(models.WNAsset).filter(models.WNAsset.id == asset_id).first()
    if not db_asset:
        return False
    db.delete(db_asset)
    db.commit()
    return True


# Agenda Template CRUD
def get_agenda_templates(db: Session, brand_id: int = None, active_only: bool = True):
    """Get agenda templates, optionally filtered by brand"""
    query = db.query(models.AgendaTemplate)
    if brand_id:
        query = query.filter(models.AgendaTemplate.brand_id == brand_id)
    if active_only:
        query = query.filter(models.AgendaTemplate.is_active == True)
    return query.order_by(models.AgendaTemplate.name).all()


def get_agenda_template(db: Session, template_id: int):
    """Get an agenda template by ID"""
    return db.query(models.AgendaTemplate).filter(models.AgendaTemplate.id == template_id).first()


def create_agenda_template(db: Session, template: schemas.AgendaTemplateCreate):
    """Create a new agenda template"""
    db_template = models.AgendaTemplate(**template.model_dump())
    db.add(db_template)
    db.commit()
    db.refresh(db_template)
    return db_template


def update_agenda_template(db: Session, template_id: int, template: schemas.AgendaTemplateUpdate):
    """Update an agenda template"""
    db_template = db.query(models.AgendaTemplate).filter(models.AgendaTemplate.id == template_id).first()
    if not db_template:
        return None
    for k, v in template.model_dump(exclude_unset=True).items():
        setattr(db_template, k, v)
    db_template.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(db_template)
    return db_template


def delete_agenda_template(db: Session, template_id: int):
    """Delete an agenda template"""
    db_template = db.query(models.AgendaTemplate).filter(models.AgendaTemplate.id == template_id).first()
    if not db_template:
        return False
    db.delete(db_template)
    db.commit()
    return True


# Reusable Content CRUD
def get_reusable_content(db: Session, brand_id: int, content_key: str = None):
    """Get reusable content for a brand"""
    query = db.query(models.ReusableContent).filter(models.ReusableContent.brand_id == brand_id)
    if content_key:
        query = query.filter(models.ReusableContent.content_key == content_key)
    return query.all()


def get_reusable_content_item(db: Session, content_id: int):
    """Get a reusable content item by ID"""
    return db.query(models.ReusableContent).filter(models.ReusableContent.id == content_id).first()


def create_reusable_content(db: Session, content: schemas.ReusableContentCreate):
    """Create a new reusable content item"""
    db_content = models.ReusableContent(**content.model_dump())
    db.add(db_content)
    db.commit()
    db.refresh(db_content)
    return db_content


def update_reusable_content(db: Session, content_id: int, content: schemas.ReusableContentUpdate):
    """Update a reusable content item"""
    db_content = db.query(models.ReusableContent).filter(models.ReusableContent.id == content_id).first()
    if not db_content:
        return None
    for k, v in content.model_dump(exclude_unset=True).items():
        setattr(db_content, k, v)
    db_content.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(db_content)
    return db_content


# Game CRUD
def get_games(db: Session, brand_id: int = None, game_type: str = None, active_only: bool = True):
    """Get games, optionally filtered by brand and type"""
    query = db.query(models.Game)
    if brand_id:
        # Include global games (brand_id is null) and brand-specific games
        query = query.filter(or_(models.Game.brand_id == brand_id, models.Game.brand_id == None))
    if game_type:
        query = query.filter(models.Game.game_type == game_type)
    if active_only:
        query = query.filter(models.Game.is_active == True)
    return query.order_by(models.Game.game_type, models.Game.title).all()


def get_game(db: Session, game_id: int):
    """Get a game by ID"""
    return db.query(models.Game).filter(models.Game.id == game_id).first()


def create_game(db: Session, game: schemas.GameCreate):
    """Create a new game"""
    db_game = models.Game(**game.model_dump())
    db.add(db_game)
    db.commit()
    db.refresh(db_game)
    return db_game


def update_game(db: Session, game_id: int, game: schemas.GameUpdate):
    """Update a game"""
    db_game = db.query(models.Game).filter(models.Game.id == game_id).first()
    if not db_game:
        return None
    for k, v in game.model_dump(exclude_unset=True).items():
        setattr(db_game, k, v)
    db_game.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(db_game)
    return db_game


def delete_game(db: Session, game_id: int):
    """Delete a game"""
    db_game = db.query(models.Game).filter(models.Game.id == game_id).first()
    if not db_game:
        return False
    db.delete(db_game)
    db.commit()
    return True


# Presentation CRUD
def get_presentations(db: Session, brand_id: int = None, facility_id: int = None, search: str = None, status: str = None):
    """Get presentations, with optional filters"""
    query = db.query(models.Presentation)
    if brand_id:
        query = query.filter(models.Presentation.brand_id == brand_id)
    if facility_id:
        query = query.filter(models.Presentation.facility_id == facility_id)
    if search:
        query = query.filter(models.Presentation.title.ilike(f"%{search}%"))
    if status:
        query = query.filter(models.Presentation.status == status)
    return query.order_by(models.Presentation.updated_at.desc()).all()


def get_presentation(db: Session, presentation_id: int):
    """Get a presentation by ID with all slides"""
    return db.query(models.Presentation).filter(models.Presentation.id == presentation_id).first()


def create_presentation(db: Session, presentation: schemas.PresentationCreate):
    """Create a new presentation"""
    db_pres = models.Presentation(**presentation.model_dump())
    db.add(db_pres)
    db.commit()
    db.refresh(db_pres)
    return db_pres


def update_presentation(db: Session, presentation_id: int, presentation: schemas.PresentationUpdate):
    """Update a presentation"""
    db_pres = db.query(models.Presentation).filter(models.Presentation.id == presentation_id).first()
    if not db_pres:
        return None
    for k, v in presentation.model_dump(exclude_unset=True).items():
        setattr(db_pres, k, v)
    db_pres.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(db_pres)
    return db_pres


def delete_presentation(db: Session, presentation_id: int):
    """Delete a presentation and all its slides"""
    db_pres = db.query(models.Presentation).filter(models.Presentation.id == presentation_id).first()
    if not db_pres:
        return False
    db.delete(db_pres)
    db.commit()
    return True


# Slide Instance CRUD
def get_presentation_slides(db: Session, presentation_id: int):
    """Get all slides for a presentation in order"""
    return db.query(models.PresentationSlideInstance).filter(
        models.PresentationSlideInstance.presentation_id == presentation_id
    ).order_by(models.PresentationSlideInstance.order).all()


def create_presentation_slide(db: Session, presentation_id: int, slide: schemas.PresentationSlideInstanceCreate):
    """Create a new slide instance"""
    db_slide = models.PresentationSlideInstance(presentation_id=presentation_id, **slide.model_dump())
    db.add(db_slide)
    db.commit()
    db.refresh(db_slide)
    return db_slide


def clear_presentation_slides(db: Session, presentation_id: int):
    """Clear all slides from a presentation"""
    db.query(models.PresentationSlideInstance).filter(
        models.PresentationSlideInstance.presentation_id == presentation_id
    ).delete()
    db.commit()


def bulk_create_slides(db: Session, presentation_id: int, slides: list):
    """Bulk create slides for a presentation"""
    db_slides = []
    for idx, slide_data in enumerate(slides):
        slide = models.PresentationSlideInstance(
            presentation_id=presentation_id,
            order=idx,
            slide_type=slide_data["slide_type"],
            payload=slide_data.get("payload", {}),
            notes=slide_data.get("notes")
        )
        db.add(slide)
        db_slides.append(slide)
    db.commit()
    for s in db_slides:
        db.refresh(s)
    return db_slides
