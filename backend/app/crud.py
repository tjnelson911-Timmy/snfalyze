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
    stats = {"vetting": 0, "pipeline": 0, "due_diligence": 0, "current_operations": 0, "on_hold": 0, "total": 0, "total_value": 0, "total_beds": 0}
    for r in db.query(models.Deal.status, func.count(models.Deal.id), func.sum(models.Deal.asking_price), func.sum(models.Deal.total_beds)).group_by(models.Deal.status).all():
        if r[0] in stats:
            stats[r[0]] = r[1]
            stats["total"] += r[1]
            if r[2]: stats["total_value"] += r[2]
            if r[3]: stats["total_beds"] += r[3]
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

def create_document(db: Session, deal_id: int, doc: schemas.DocumentCreate):
    db_doc = models.Document(deal_id=deal_id, **doc.model_dump())
    db.add(db_doc)
    db.commit()
    db.refresh(db_doc)
    log_activity(db, deal_id, "document_uploaded", f"Document '{doc.original_filename}' uploaded")
    return db_doc

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
