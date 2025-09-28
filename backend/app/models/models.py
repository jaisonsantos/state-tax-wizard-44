from sqlalchemy import Column, String, Boolean, Integer, DateTime, Text, ForeignKey, JSON
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
import uuid
from ..db.database import Base

class Store(Base):
    __tablename__ = "stores"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    platform = Column(String(20), nullable=False)  # "shopify" or "woo"
    domain = Column(String(255), nullable=False)
    country = Column(String(2), nullable=False, default="US")
    state = Column(String(2), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    settings = relationship("StoreSetting", back_populates="store", uselist=False)
    subscriptions = relationship("Subscription", back_populates="store")
    order_fees = relationship("OrderFee", back_populates="store")

class StoreSetting(Base):
    __tablename__ = "store_settings"
    
    store_id = Column(UUID(as_uuid=True), ForeignKey("stores.id"), primary_key=True)
    enable_mn = Column(Boolean, default=True)
    enable_co = Column(Boolean, default=True)
    absorb_fee = Column(Boolean, default=False)
    label_override = Column(Text, default="Delivery Fee")
    plan = Column(String(20), default="starter")  # "starter", "pro", "plus"
    
    # Relationships
    store = relationship("Store", back_populates="settings")

class RuleVersion(Base):
    __tablename__ = "rule_versions"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    jurisdiction = Column(String(2), nullable=False)  # "MN" or "CO"
    version = Column(String(50), nullable=False)
    effective_from = Column(DateTime(timezone=True), nullable=False)
    effective_to = Column(DateTime(timezone=True), nullable=True)
    params = Column(JSON, nullable=False)

class OrderFee(Base):
    __tablename__ = "order_fees"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    store_id = Column(UUID(as_uuid=True), ForeignKey("stores.id"), nullable=False)
    order_id = Column(String(100), nullable=False)
    jurisdiction = Column(String(2), nullable=False)
    amount_cents = Column(Integer, nullable=False)
    applied_at = Column(DateTime(timezone=True), server_default=func.now())
    delivery_method = Column(String(20), nullable=False)
    absorbed = Column(Boolean, default=False)
    rule_version = Column(String(50), nullable=False)
    reason_codes = Column(JSON, nullable=False)
    
    # Relationships
    store = relationship("Store", back_populates="order_fees")

class AuditLog(Base):
    __tablename__ = "audit_logs"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    ts = Column(DateTime(timezone=True), server_default=func.now())
    actor = Column(String(255), nullable=False)
    action = Column(String(100), nullable=False)
    payload = Column(JSON, nullable=False)

class Subscription(Base):
    __tablename__ = "subscriptions"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    store_id = Column(UUID(as_uuid=True), ForeignKey("stores.id"), nullable=False)
    provider = Column(String(20), nullable=False)  # "shopify" or "stripe"
    plan = Column(String(20), nullable=False)
    status = Column(String(20), nullable=False)
    trial_end = Column(DateTime(timezone=True), nullable=True)
    current_period_end = Column(DateTime(timezone=True), nullable=True)
    
    # Relationships
    store = relationship("Store", back_populates="subscriptions")