from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime

class DealBase(BaseModel):
    name: str
    deal_type: Optional[str] = "SNF"
    priority: Optional[str] = "medium"
    asking_price: Optional[float] = None
    ebitdar: Optional[float] = None
    cap_rate: Optional[float] = None
    total_beds: Optional[int] = None
    broker_name: Optional[str] = None
    broker_company: Optional[str] = None
    broker_email: Optional[str] = None
    broker_phone: Optional[str] = None
    seller_name: Optional[str] = None
    source: Optional[str] = None
    notes: Optional[str] = None
    investment_thesis: Optional[str] = None

class DealCreate(DealBase): pass

class DealUpdate(BaseModel):
    name: Optional[str] = None
    deal_type: Optional[str] = None
    status: Optional[str] = None
    priority: Optional[str] = None
    asking_price: Optional[float] = None
    ebitdar: Optional[float] = None
    cap_rate: Optional[float] = None
    total_beds: Optional[int] = None
    broker_name: Optional[str] = None
    broker_company: Optional[str] = None
    broker_email: Optional[str] = None
    broker_phone: Optional[str] = None
    seller_name: Optional[str] = None
    source: Optional[str] = None
    notes: Optional[str] = None
    investment_thesis: Optional[str] = None

class DealResponse(DealBase):
    id: int
    status: str
    estimated_value: Optional[float] = None
    price_per_bed: Optional[float] = None
    property_count: int = 1
    custom_categories: Optional[List[dict]] = []
    created_at: datetime
    updated_at: Optional[datetime] = None
    document_count: Optional[int] = 0
    task_count: Optional[int] = 0
    class Config: from_attributes = True

class PropertyBase(BaseModel):
    name: str
    property_type: Optional[str] = "SNF"
    address: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    licensed_beds: Optional[int] = None
    star_rating: Optional[int] = None
    current_occupancy: Optional[float] = None
    ebitdar: Optional[float] = None

class PropertyCreate(PropertyBase): pass
class PropertyUpdate(PropertyBase): pass

class PropertyResponse(PropertyBase):
    id: int
    deal_id: int
    price_per_bed: Optional[float] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    created_at: datetime
    class Config: from_attributes = True

class DocumentCreate(BaseModel):
    filename: str
    original_filename: str
    file_type: str
    file_size: Optional[int] = None
    category: Optional[str] = "other"
    checksum: Optional[str] = None
    doc_type: Optional[str] = None
    uploaded_by: Optional[str] = None

class DocumentResponse(BaseModel):
    id: int
    deal_id: int
    property_id: Optional[int] = None
    filename: str
    original_filename: str
    file_type: str
    category: str
    analyzed: bool
    analysis_summary: Optional[str] = None
    uploaded_at: datetime
    # New fields
    checksum: Optional[str] = None
    doc_type: Optional[str] = None
    parsing_status: Optional[str] = "pending"
    parsing_error: Optional[str] = None
    uploaded_by: Optional[str] = None
    class Config: from_attributes = True

class ActivityResponse(BaseModel):
    id: int
    deal_id: int
    action: str
    description: Optional[str] = None
    created_at: datetime
    class Config: from_attributes = True

class TaskBase(BaseModel):
    title: str
    description: Optional[str] = None
    priority: Optional[str] = "medium"
    due_date: Optional[datetime] = None

class TaskCreate(TaskBase): pass

class TaskUpdate(BaseModel):
    title: Optional[str] = None
    status: Optional[str] = None
    priority: Optional[str] = None

class TaskResponse(TaskBase):
    id: int
    deal_id: int
    status: str
    completed_at: Optional[datetime] = None
    created_at: datetime
    class Config: from_attributes = True

class StatusUpdate(BaseModel):
    status: str

class DealDetailResponse(DealResponse):
    properties: List[PropertyResponse] = []
    documents: List[DocumentResponse] = []
    activities: List[ActivityResponse] = []
    tasks: List[TaskResponse] = []
    class Config: from_attributes = True


# ============================================================================
# DOCUMENT ANALYSIS SCHEMAS
# ============================================================================

class ParsedArtifactResponse(BaseModel):
    id: int
    document_id: int
    artifact_type: str
    page_number: Optional[int] = None
    content: Optional[str] = None
    content_json: Optional[dict] = None
    confidence: Optional[float] = None
    created_at: datetime
    class Config: from_attributes = True


class ExtractedFieldCreate(BaseModel):
    field_key: str
    field_value: str
    field_type: Optional[str] = None
    numeric_value: Optional[float] = None
    units: Optional[str] = None
    period_start: Optional[datetime] = None
    period_end: Optional[datetime] = None
    confidence: Optional[float] = 0.0
    source_page: Optional[int] = None
    source_snippet: Optional[str] = None
    extraction_method: Optional[str] = "manual"

class ExtractedFieldResponse(BaseModel):
    id: int
    document_id: int
    deal_id: int
    property_id: Optional[int] = None
    field_key: str
    field_value: str
    field_type: Optional[str] = None
    numeric_value: Optional[float] = None
    units: Optional[str] = None
    period_start: Optional[datetime] = None
    period_end: Optional[datetime] = None
    confidence: float
    source_page: Optional[int] = None
    source_snippet: Optional[str] = None
    source_table_ref: Optional[str] = None
    extraction_method: Optional[str] = None
    is_verified: bool
    created_by: str
    created_at: datetime
    updated_at: Optional[datetime] = None
    class Config: from_attributes = True

class ExtractedFieldUpdate(BaseModel):
    field_value: Optional[str] = None
    numeric_value: Optional[float] = None
    is_verified: Optional[bool] = None


class ClaimCreate(BaseModel):
    claim_category: str
    claim_type: str
    claim_text: str
    claimed_value: Optional[str] = None
    numeric_value: Optional[float] = None
    units: Optional[str] = None
    timeframe: Optional[str] = None
    confidence: Optional[float] = 0.0
    source_page: Optional[int] = None
    source_snippet: Optional[str] = None

class ClaimResponse(BaseModel):
    id: int
    document_id: int
    deal_id: int
    property_id: Optional[int] = None
    claim_category: str
    claim_type: str
    claim_text: str
    claimed_value: Optional[str] = None
    numeric_value: Optional[float] = None
    units: Optional[str] = None
    timeframe: Optional[str] = None
    confidence: float
    source_page: Optional[int] = None
    source_snippet: Optional[str] = None
    verified_value: Optional[str] = None
    variance: Optional[float] = None
    variance_pct: Optional[float] = None
    verification_status: str
    verification_notes: Optional[str] = None
    is_red_flag: bool
    created_at: datetime
    updated_at: Optional[datetime] = None
    class Config: from_attributes = True

class ClaimVerification(BaseModel):
    verified_value: Optional[str] = None
    verification_status: str  # verified, disputed, flagged
    verification_notes: Optional[str] = None
    is_red_flag: Optional[bool] = False


class StandardAccountResponse(BaseModel):
    id: int
    code: str
    name: str
    category: str
    subcategory: Optional[str] = None
    display_order: Optional[int] = None
    class Config: from_attributes = True


class COAMappingCreate(BaseModel):
    seller_account_name: str
    seller_account_number: Optional[str] = None
    standard_account_id: Optional[int] = None
    standard_account_code: Optional[str] = None

class COAMappingResponse(BaseModel):
    id: int
    deal_id: int
    document_id: Optional[int] = None
    seller_account_name: str
    seller_account_number: Optional[str] = None
    standard_account_id: Optional[int] = None
    standard_account_code: Optional[str] = None
    confidence: float
    mapping_status: str
    suggested_by: Optional[str] = None
    approved_by: Optional[str] = None
    approved_at: Optional[datetime] = None
    created_at: datetime
    class Config: from_attributes = True

class COAMappingApproval(BaseModel):
    standard_account_id: Optional[int] = None
    standard_account_code: Optional[str] = None
    mapping_status: str  # approved, rejected
    approved_by: str


class FinancialLineItemCreate(BaseModel):
    standard_account_code: str
    period_type: str
    period_start: Optional[datetime] = None
    period_end: Optional[datetime] = None
    period_label: Optional[str] = None
    amount: float

class FinancialLineItemResponse(BaseModel):
    id: int
    deal_id: int
    property_id: Optional[int] = None
    document_id: Optional[int] = None
    standard_account_id: Optional[int] = None
    standard_account_code: Optional[str] = None
    period_type: str
    period_start: Optional[datetime] = None
    period_end: Optional[datetime] = None
    period_label: Optional[str] = None
    amount: float
    is_annualized: bool
    is_adjusted: bool
    adjustment_notes: Optional[str] = None
    source_page: Optional[int] = None
    created_at: datetime
    class Config: from_attributes = True


class ScenarioCreate(BaseModel):
    name: str
    description: Optional[str] = None
    is_base_case: Optional[bool] = False
    assumptions: Optional[dict] = None

class ScenarioResponse(BaseModel):
    id: int
    deal_id: int
    name: str
    description: Optional[str] = None
    is_base_case: bool
    assumptions: Optional[dict] = None
    outputs: Optional[dict] = None
    ebitdar: Optional[float] = None
    noi: Optional[float] = None
    cap_rate: Optional[float] = None
    implied_value: Optional[float] = None
    price_per_bed: Optional[float] = None
    created_by: Optional[str] = None
    created_at: datetime
    updated_at: Optional[datetime] = None
    class Config: from_attributes = True

class ScenarioUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    is_base_case: Optional[bool] = None
    assumptions: Optional[dict] = None


class RiskFlagCreate(BaseModel):
    risk_category: str
    risk_type: str
    severity: str
    title: str
    description: Optional[str] = None
    evidence_refs: Optional[List[dict]] = None
    recommendation: Optional[str] = None

class RiskFlagResponse(BaseModel):
    id: int
    deal_id: int
    property_id: Optional[int] = None
    risk_category: str
    risk_type: str
    severity: str
    title: str
    description: Optional[str] = None
    evidence_refs: Optional[List[dict]] = None
    recommendation: Optional[str] = None
    status: str
    resolution_notes: Optional[str] = None
    resolved_by: Optional[str] = None
    resolved_at: Optional[datetime] = None
    created_at: datetime
    class Config: from_attributes = True

class RiskFlagUpdate(BaseModel):
    status: Optional[str] = None  # acknowledged, mitigated, accepted
    resolution_notes: Optional[str] = None
    resolved_by: Optional[str] = None


class DealScorecardResponse(BaseModel):
    id: int
    deal_id: int
    financial_score: Optional[float] = None
    operational_score: Optional[float] = None
    compliance_score: Optional[float] = None
    market_score: Optional[float] = None
    lease_score: Optional[float] = None
    overall_score: Optional[float] = None
    recommendation: Optional[str] = None
    recommendation_summary: Optional[str] = None
    key_risks: Optional[List[dict]] = None
    key_strengths: Optional[List[dict]] = None
    created_at: datetime
    updated_at: Optional[datetime] = None
    class Config: from_attributes = True


class FieldOverrideCreate(BaseModel):
    entity_type: str
    entity_id: int
    field_name: str
    old_value: Optional[str] = None
    new_value: str
    reason: Optional[str] = None
    overridden_by: str

class FieldOverrideResponse(BaseModel):
    id: int
    deal_id: int
    entity_type: str
    entity_id: int
    field_name: str
    old_value: Optional[str] = None
    new_value: str
    reason: Optional[str] = None
    overridden_by: str
    created_at: datetime
    class Config: from_attributes = True


class AnalysisJobResponse(BaseModel):
    id: int
    deal_id: Optional[int] = None
    document_id: Optional[int] = None
    job_type: str
    status: str
    progress: int
    error_message: Optional[str] = None
    result: Optional[dict] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    created_at: datetime
    class Config: from_attributes = True


# ============================================================================
# OM SCRUB REPORT SCHEMAS
# ============================================================================

class OMClaimSummary(BaseModel):
    """Single claim in OM scrub report"""
    claim_id: int
    category: str
    type: str
    claim_text: str
    claimed_value: Optional[str] = None
    timeframe: Optional[str] = None
    confidence: float
    source_page: Optional[int] = None
    source_snippet: Optional[str] = None
    verified_value: Optional[str] = None
    variance_pct: Optional[float] = None
    status: str
    is_red_flag: bool

class OMVarianceItem(BaseModel):
    """Variance between OM claim and evidence"""
    claim_type: str
    om_value: str
    evidence_value: str
    variance: str
    variance_pct: float
    evidence_source: str
    severity: str  # low, medium, high

class OMScrubReport(BaseModel):
    """Complete OM scrub report"""
    deal_id: int
    document_id: int
    document_name: str
    generated_at: datetime
    claims_summary: List[OMClaimSummary]
    variances: List[OMVarianceItem]
    red_flags: List[str]
    diligence_questions: List[str]
    overall_confidence: float
