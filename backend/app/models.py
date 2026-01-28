from sqlalchemy import Column, Integer, String, Float, Text, DateTime, ForeignKey, Boolean, JSON
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from .database import Base

class Deal(Base):
    __tablename__ = "deals"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    status = Column(String(50), default="vetting")
    deal_type = Column(String(50), default="SNF")
    priority = Column(String(20), default="medium")
    asking_price = Column(Float)
    estimated_value = Column(Float)
    ebitdar = Column(Float)
    cap_rate = Column(Float)
    price_per_bed = Column(Float)
    total_beds = Column(Integer)
    total_units = Column(Integer)
    property_count = Column(Integer, default=1)
    broker_name = Column(String(255))
    broker_company = Column(String(255))
    broker_email = Column(String(255))
    broker_phone = Column(String(50))
    seller_name = Column(String(255))
    source = Column(String(255))
    notes = Column(Text)
    investment_thesis = Column(Text)
    custom_categories = Column(JSON, default=list)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    stage_changed_at = Column(DateTime(timezone=True), server_default=func.now())
    properties = relationship("Property", back_populates="deal", cascade="all, delete-orphan")
    documents = relationship("Document", back_populates="deal", cascade="all, delete-orphan")
    activities = relationship("Activity", back_populates="deal", cascade="all, delete-orphan")
    tasks = relationship("Task", back_populates="deal", cascade="all, delete-orphan")
    # Analysis relationships
    scenarios = relationship("Scenario", backref="deal", cascade="all, delete-orphan")
    risk_flags = relationship("RiskFlag", backref="deal", cascade="all, delete-orphan")
    coa_mappings = relationship("COAMapping", backref="deal", cascade="all, delete-orphan")
    financial_line_items = relationship("FinancialLineItem", backref="deal", cascade="all, delete-orphan")
    scorecard = relationship("DealScorecard", backref="deal", uselist=False, cascade="all, delete-orphan")

class Property(Base):
    __tablename__ = "properties"
    id = Column(Integer, primary_key=True, index=True)
    deal_id = Column(Integer, ForeignKey("deals.id"), nullable=False)
    name = Column(String(255), nullable=False)
    property_type = Column(String(50), default="SNF")
    address = Column(String(255))
    city = Column(String(100))
    state = Column(String(50))
    licensed_beds = Column(Integer)
    star_rating = Column(Integer)
    current_occupancy = Column(Float)
    ebitdar = Column(Float)
    allocated_value = Column(Float)
    price_per_bed = Column(Float)
    latitude = Column(Float)
    longitude = Column(Float)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    deal = relationship("Deal", back_populates="properties")
    documents = relationship("Document", back_populates="property")

class Document(Base):
    __tablename__ = "documents"
    id = Column(Integer, primary_key=True, index=True)
    deal_id = Column(Integer, ForeignKey("deals.id"), nullable=False)
    property_id = Column(Integer, ForeignKey("properties.id"))
    filename = Column(String(255), nullable=False)
    original_filename = Column(String(255), nullable=False)
    file_type = Column(String(50), nullable=False)
    file_size = Column(Integer)
    category = Column(String(100), default="other")
    analyzed = Column(Boolean, default=False)
    analysis_summary = Column(Text)
    uploaded_at = Column(DateTime(timezone=True), server_default=func.now())
    # New fields for enhanced analysis
    checksum = Column(String(64))  # SHA-256 hash for duplicate detection
    doc_type = Column(String(50))  # classified type: om, financials, rent_roll, census, lease, survey, etc.
    parsing_status = Column(String(20), default="pending")  # pending, processing, completed, failed
    parsing_error = Column(Text)  # error message if parsing failed
    uploaded_by = Column(String(255))  # user identifier
    # Relationships
    deal = relationship("Deal", back_populates="documents")
    property = relationship("Property", back_populates="documents")
    artifacts = relationship("ParsedArtifact", back_populates="document", cascade="all, delete-orphan")
    extracted_fields = relationship("ExtractedField", back_populates="document", cascade="all, delete-orphan")
    claims = relationship("Claim", back_populates="document", cascade="all, delete-orphan")

class Activity(Base):
    __tablename__ = "activities"
    id = Column(Integer, primary_key=True, index=True)
    deal_id = Column(Integer, ForeignKey("deals.id"), nullable=False)
    action = Column(String(100), nullable=False)
    description = Column(Text)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    deal = relationship("Deal", back_populates="activities")

class Task(Base):
    __tablename__ = "tasks"
    id = Column(Integer, primary_key=True, index=True)
    deal_id = Column(Integer, ForeignKey("deals.id"), nullable=False)
    title = Column(String(255), nullable=False)
    description = Column(Text)
    status = Column(String(50), default="pending")
    priority = Column(String(20), default="medium")
    due_date = Column(DateTime)
    completed_at = Column(DateTime)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    deal = relationship("Deal", back_populates="tasks")

class CurrentOperation(Base):
    __tablename__ = "current_operations"
    id = Column(Integer, primary_key=True, index=True)
    company = Column(String(255), nullable=False)
    team = Column(String(255))
    property_name = Column(String(255))
    property_type = Column(String(50))
    address = Column(String(255))
    city = Column(String(100))
    state = Column(String(50))
    beds = Column(Integer)
    notes = Column(Text)
    latitude = Column(Float)
    longitude = Column(Float)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


# ============================================================================
# DOCUMENT ANALYSIS MODELS
# ============================================================================

class ParsedArtifact(Base):
    """Stores extracted content from documents (text, tables, OCR results)"""
    __tablename__ = "parsed_artifacts"
    id = Column(Integer, primary_key=True, index=True)
    document_id = Column(Integer, ForeignKey("documents.id"), nullable=False)
    artifact_type = Column(String(50), nullable=False)  # text, table, ocr, image
    page_number = Column(Integer)  # source page (1-indexed)
    content = Column(Text)  # extracted text or JSON for tables
    content_json = Column(JSON)  # structured data (for tables)
    table_coords = Column(JSON)  # bounding box coordinates for tables
    confidence = Column(Float)  # OCR/extraction confidence
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    document = relationship("Document", back_populates="artifacts")


class ExtractedField(Base):
    """Stores individual extracted values with full provenance"""
    __tablename__ = "extracted_fields"
    id = Column(Integer, primary_key=True, index=True)
    document_id = Column(Integer, ForeignKey("documents.id"), nullable=True)  # nullable for deal-level analysis
    deal_id = Column(Integer, ForeignKey("deals.id"), nullable=False)
    property_id = Column(Integer, ForeignKey("properties.id"))
    field_key = Column(String(100), nullable=False)  # e.g., "revenue", "ebitdar", "occupancy"
    field_value = Column(Text)  # the extracted value (stored as text)
    field_type = Column(String(20))  # number, currency, percentage, date, text
    numeric_value = Column(Float)  # parsed numeric value if applicable
    units = Column(String(50))  # USD, beds, %, etc.
    period_start = Column(DateTime)  # for time-series data
    period_end = Column(DateTime)
    confidence = Column(Float, default=0.0)  # 0.0 to 1.0
    source_page = Column(Integer)  # page number in document
    source_snippet = Column(Text)  # surrounding text for context
    source_table_ref = Column(String(100))  # reference to table if from table
    extraction_method = Column(String(50))  # regex, llm, table_parse, manual
    is_verified = Column(Boolean, default=False)  # user verified
    created_by = Column(String(50), default="system")  # system or user_id
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    document = relationship("Document", back_populates="extracted_fields")


class Claim(Base):
    """Stores claims extracted from OM/CIM documents for scrubbing"""
    __tablename__ = "claims"
    id = Column(Integer, primary_key=True, index=True)
    document_id = Column(Integer, ForeignKey("documents.id"), nullable=False)
    deal_id = Column(Integer, ForeignKey("deals.id"), nullable=False)
    property_id = Column(Integer, ForeignKey("properties.id"))
    claim_category = Column(String(50), nullable=False)  # financial, operational, market, regulatory, staffing
    claim_type = Column(String(100), nullable=False)  # revenue, ebitda, occupancy, payer_mix, star_rating, etc.
    claim_text = Column(Text, nullable=False)  # the actual claim statement
    claimed_value = Column(Text)  # the value being claimed
    numeric_value = Column(Float)  # parsed numeric if applicable
    units = Column(String(50))
    timeframe = Column(String(100))  # "T-12", "2024", "as of Dec 2024", etc.
    confidence = Column(Float, default=0.0)
    source_page = Column(Integer)
    source_snippet = Column(Text)  # surrounding context
    # Verification fields
    verified_value = Column(Text)  # value from evidence documents
    variance = Column(Float)  # difference between claimed and verified
    variance_pct = Column(Float)  # percentage variance
    verification_status = Column(String(20), default="unverified")  # unverified, verified, disputed, flagged
    verification_source_id = Column(Integer)  # document_id of evidence
    verification_notes = Column(Text)
    is_red_flag = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    document = relationship("Document", back_populates="claims")


class StandardAccount(Base):
    """Standard Chart of Accounts for normalizing seller financials"""
    __tablename__ = "standard_accounts"
    id = Column(Integer, primary_key=True, index=True)
    code = Column(String(20), nullable=False, unique=True)  # e.g., "REV-001"
    name = Column(String(255), nullable=False)  # e.g., "Medicaid Revenue"
    category = Column(String(50), nullable=False)  # revenue, expense, asset, liability
    subcategory = Column(String(100))  # e.g., "patient_revenue", "labor", "supplies"
    display_order = Column(Integer)  # for report ordering
    is_active = Column(Boolean, default=True)


class COAMapping(Base):
    """Maps seller account names to standard accounts"""
    __tablename__ = "coa_mappings"
    id = Column(Integer, primary_key=True, index=True)
    deal_id = Column(Integer, ForeignKey("deals.id"), nullable=False)
    document_id = Column(Integer, ForeignKey("documents.id"))  # source document
    seller_account_name = Column(String(255), nullable=False)
    seller_account_number = Column(String(50))
    standard_account_id = Column(Integer, ForeignKey("standard_accounts.id"))
    standard_account_code = Column(String(20))  # denormalized for convenience
    confidence = Column(Float, default=0.0)  # suggestion confidence
    mapping_status = Column(String(20), default="suggested")  # suggested, approved, rejected, manual
    suggested_by = Column(String(50))  # llm, rules, user
    approved_by = Column(String(255))
    approved_at = Column(DateTime)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class FinancialLineItem(Base):
    """Normalized financial data from parsed documents"""
    __tablename__ = "financial_line_items"
    id = Column(Integer, primary_key=True, index=True)
    deal_id = Column(Integer, ForeignKey("deals.id"), nullable=False)
    property_id = Column(Integer, ForeignKey("properties.id"))
    document_id = Column(Integer, ForeignKey("documents.id"))
    standard_account_id = Column(Integer, ForeignKey("standard_accounts.id"))
    standard_account_code = Column(String(20))  # denormalized
    period_type = Column(String(20))  # monthly, quarterly, annual, t12
    period_start = Column(DateTime)
    period_end = Column(DateTime)
    period_label = Column(String(50))  # "Jan 2024", "Q1 2024", "T-12", etc.
    amount = Column(Float, nullable=False)
    is_annualized = Column(Boolean, default=False)
    source_table_ref = Column(String(100))  # reference to source table
    source_page = Column(Integer)
    is_adjusted = Column(Boolean, default=False)  # user adjusted
    adjustment_notes = Column(Text)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class Scenario(Base):
    """Pro forma scenarios with assumptions and outputs"""
    __tablename__ = "scenarios"
    id = Column(Integer, primary_key=True, index=True)
    deal_id = Column(Integer, ForeignKey("deals.id"), nullable=False)
    name = Column(String(100), nullable=False)  # "Status Quo", "Stabilized", "Upside", "Downside"
    description = Column(Text)
    is_base_case = Column(Boolean, default=False)
    # Assumptions stored as JSON
    assumptions = Column(JSON)  # {"occupancy_target": 0.90, "labor_increase_pct": 0.03, ...}
    # Calculated outputs
    outputs = Column(JSON)  # {"revenue": 5000000, "ebitdar": 800000, "noi": 600000, ...}
    ebitdar = Column(Float)  # denormalized key metrics
    noi = Column(Float)
    cap_rate = Column(Float)
    implied_value = Column(Float)
    price_per_bed = Column(Float)
    created_by = Column(String(255))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())


class RiskFlag(Base):
    """Risk indicators identified during analysis"""
    __tablename__ = "risk_flags"
    id = Column(Integer, primary_key=True, index=True)
    deal_id = Column(Integer, ForeignKey("deals.id"), nullable=False)
    property_id = Column(Integer, ForeignKey("properties.id"))
    risk_category = Column(String(50), nullable=False)  # financial, compliance, operational, market, regulatory, lease
    risk_type = Column(String(100), nullable=False)  # specific risk identifier
    severity = Column(String(20), nullable=False)  # low, medium, high, critical
    title = Column(String(255), nullable=False)
    description = Column(Text)
    evidence_refs = Column(JSON)  # [{"doc_id": 1, "page": 5, "snippet": "..."}, ...]
    recommendation = Column(Text)  # suggested action
    status = Column(String(20), default="open")  # open, acknowledged, mitigated, accepted
    resolution_notes = Column(Text)
    resolved_by = Column(String(255))
    resolved_at = Column(DateTime)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class DealScorecard(Base):
    """Overall deal scoring and recommendation"""
    __tablename__ = "deal_scorecards"
    id = Column(Integer, primary_key=True, index=True)
    deal_id = Column(Integer, ForeignKey("deals.id"), nullable=False, unique=True)
    # Category scores (0-100)
    financial_score = Column(Float)
    operational_score = Column(Float)
    compliance_score = Column(Float)
    market_score = Column(Float)
    lease_score = Column(Float)
    overall_score = Column(Float)
    # Recommendation
    recommendation = Column(String(20))  # proceed, pause, kill
    recommendation_summary = Column(Text)
    key_risks = Column(JSON)  # top 3-5 risks
    key_strengths = Column(JSON)  # top 3-5 strengths
    # Scoring config used
    scoring_config_version = Column(String(20))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())


class FieldOverride(Base):
    """Audit trail for user overrides of extracted/calculated values"""
    __tablename__ = "field_overrides"
    id = Column(Integer, primary_key=True, index=True)
    deal_id = Column(Integer, ForeignKey("deals.id"), nullable=False)
    entity_type = Column(String(50), nullable=False)  # extracted_field, claim, financial_line_item, scenario
    entity_id = Column(Integer, nullable=False)
    field_name = Column(String(100), nullable=False)
    old_value = Column(Text)
    new_value = Column(Text)
    reason = Column(Text)
    overridden_by = Column(String(255), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class AnalysisJob(Base):
    """Track background analysis jobs"""
    __tablename__ = "analysis_jobs"
    id = Column(Integer, primary_key=True, index=True)
    deal_id = Column(Integer, ForeignKey("deals.id"))
    document_id = Column(Integer, ForeignKey("documents.id"))
    job_type = Column(String(50), nullable=False)  # parse, classify, extract, scrub, financial_ingest
    status = Column(String(20), default="pending")  # pending, running, completed, failed
    progress = Column(Integer, default=0)  # 0-100
    error_message = Column(Text)
    result = Column(JSON)  # job output
    started_at = Column(DateTime)
    completed_at = Column(DateTime)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


