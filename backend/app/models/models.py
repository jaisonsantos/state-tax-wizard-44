from sqlalchemy import (
    Column,
    String,
    Boolean,
    Integer,
    DateTime,
    Text,
    ForeignKey,
    JSON,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from sqlalchemy.types import CHAR, TypeDecorator
import uuid
from ..db.database import Base


class GUID(TypeDecorator):
    """Platform-independent GUID/UUID type."""

    impl = CHAR
    cache_ok = True

    def load_dialect_impl(self, dialect):
        if dialect.name == "postgresql":
            return dialect.type_descriptor(PGUUID(as_uuid=True))
        return dialect.type_descriptor(CHAR(36))

    def process_bind_param(self, value, dialect):
        if value is None:
            return value
        if isinstance(value, uuid.UUID):
            return str(value) if dialect.name != "postgresql" else value
        return str(uuid.UUID(str(value)))

    def process_result_value(self, value, dialect):
        if value is None:
            return value
        return value if isinstance(value, uuid.UUID) else uuid.UUID(str(value))

class Store(Base):
    __tablename__ = "stores"

    id = Column(GUID(), primary_key=True, default=uuid.uuid4)
    name = Column(String(255), nullable=False)
    platform = Column(String(20), nullable=False)  # "shopify" or "woo"
    domain = Column(String(255), nullable=False)
    country = Column(String(2), nullable=False, default="US")
    state = Column(String(2), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    settings = relationship("StoreSetting", back_populates="store", uselist=False)
    subscriptions = relationship("Subscription", back_populates="store")
    order_fees = relationship("OrderFee", back_populates="store")
    users = relationship("User", secondary="user_stores", back_populates="stores")

class StoreSetting(Base):
    __tablename__ = "store_settings"

    store_id = Column(GUID(), ForeignKey("stores.id"), primary_key=True)
    enable_mn = Column(Boolean, default=True)
    enable_co = Column(Boolean, default=True)
    absorb_fee = Column(Boolean, default=False)
    label_override = Column(Text, default="Delivery Fee")
    plan = Column(String(20), default="starter")  # "starter", "pro", "plus"
    hmac_secret = Column(Text, nullable=True)

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

    id = Column(GUID(), primary_key=True, default=uuid.uuid4)
    store_id = Column(GUID(), ForeignKey("stores.id"), nullable=False)
    order_id = Column(String(100), nullable=False)
    jurisdiction = Column(String(2), nullable=False)
    amount_cents = Column(Integer, nullable=False)
    applied_at = Column(DateTime(timezone=True), server_default=func.now())
    delivery_method = Column(String(20), nullable=False)
    absorbed = Column(Boolean, default=False)
    rule_version = Column(String(50), nullable=False)
    reason_codes = Column(JSON, nullable=False)
    display_name = Column(Text, nullable=True)
    status = Column(String(20), nullable=False, default="applied")
    reversal_reason = Column(String(50), nullable=True)
    reversed_at = Column(DateTime(timezone=True), nullable=True)
    source_of_remittance = Column(String(20), nullable=True)

    # Relationships
    store = relationship("Store", back_populates="order_fees")

    __table_args__ = (
        UniqueConstraint("store_id", "order_id", "jurisdiction", name="uq_order_fee_store_order_jurisdiction"),
    )

class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(GUID(), primary_key=True, default=uuid.uuid4)
    ts = Column(DateTime(timezone=True), server_default=func.now())
    actor = Column(String(255), nullable=False)
    action = Column(String(100), nullable=False)
    payload = Column(JSON, nullable=False)

class Subscription(Base):
    __tablename__ = "subscriptions"
    
    id = Column(GUID(), primary_key=True, default=uuid.uuid4)
    store_id = Column(GUID(), ForeignKey("stores.id"), nullable=False)
    provider = Column(String(20), nullable=False)  # "shopify" or "stripe"
    plan = Column(String(20), nullable=False)
    status = Column(String(20), nullable=False)
    trial_end = Column(DateTime(timezone=True), nullable=True)
    current_period_end = Column(DateTime(timezone=True), nullable=True)

    # Relationships
    store = relationship("Store", back_populates="subscriptions")


class User(Base):
    __tablename__ = "users"

    id = Column(GUID(), primary_key=True, default=uuid.uuid4)
    email = Column(String(255), nullable=False, unique=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    stores = relationship("Store", secondary="user_stores", back_populates="users")


class UserStore(Base):
    __tablename__ = "user_stores"

    user_id = Column(GUID(), ForeignKey("users.id"), primary_key=True)
    store_id = Column(GUID(), ForeignKey("stores.id"), primary_key=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        UniqueConstraint("user_id", "store_id", name="uq_user_store"),
    )