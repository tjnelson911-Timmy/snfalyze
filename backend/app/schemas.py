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

class DocumentResponse(BaseModel):
    id: int
    deal_id: int
    filename: str
    original_filename: str
    file_type: str
    category: str
    analyzed: bool
    analysis_summary: Optional[str] = None
    uploaded_at: datetime
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
