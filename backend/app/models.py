from sqlalchemy import Column, Integer, String, Float, Text, DateTime, ForeignKey, Boolean
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
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    stage_changed_at = Column(DateTime(timezone=True), server_default=func.now())
    properties = relationship("Property", back_populates="deal", cascade="all, delete-orphan")
    documents = relationship("Document", back_populates="deal", cascade="all, delete-orphan")
    activities = relationship("Activity", back_populates="deal", cascade="all, delete-orphan")
    tasks = relationship("Task", back_populates="deal", cascade="all, delete-orphan")

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
    deal = relationship("Deal", back_populates="documents")
    property = relationship("Property", back_populates="documents")

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
