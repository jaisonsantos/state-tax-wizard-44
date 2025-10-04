from sqlalchemy import (
    Column,
    String,
    Boolean,
    Integer,
    DateTime,
    Text,
    ForeignKey,
    JSON,
    Index,
    text,
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
    contact_email = Column(String(255), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    stripe_customer_id = Column(String(255), unique=True, nullable=True)
    stripe_subscription_id = Column(String(255), nullable=True)

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
    hmac_secret_rotated_at = Column(DateTime(timezone=True), nullable=True)
    webhook_endpoint = Column(Text, nullable=True)
    webhook_active = Column(Boolean, nullable=False, server_default=text("false"), default=False)
    webhook_events = Column(JSON, nullable=False, server_default=text("'[]'"), default=list)

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
        Index(
            "uq_order_fee_store_order_jurisdiction_applied",
            "store_id",
            "order_id",
            "jurisdiction",
            unique=True,
            postgresql_where=text("status = 'applied'"),
        ),
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
    current_period_start = Column(DateTime(timezone=True), nullable=True)
    current_period_end = Column(DateTime(timezone=True), nullable=True)
    stripe_subscription_id = Column(String(255), unique=True, nullable=True)
    stripe_customer_id = Column(String(255), nullable=True)
    plan_tier = Column(String(50), nullable=False, default="starter")
    cancel_at_period_end = Column(Boolean, nullable=False, default=False)
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    # Relationships
    store = relationship("Store", back_populates="subscriptions")


class User(Base):
    __tablename__ = "users"

    id = Column(GUID(), primary_key=True, default=uuid.uuid4)
    email = Column(String(255), nullable=False, unique=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    stores = relationship("Store", secondary="user_stores", back_populates="users")
    sessions = relationship("SessionToken", back_populates="user")


class UserStore(Base):
    __tablename__ = "user_stores"

    user_id = Column(GUID(), ForeignKey("users.id"), primary_key=True)
    store_id = Column(GUID(), ForeignKey("stores.id"), primary_key=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class SessionToken(Base):
    __tablename__ = "session_tokens"

    id = Column(GUID(), primary_key=True, default=uuid.uuid4)
    user_id = Column(GUID(), ForeignKey("users.id"), nullable=False)
    jti = Column(String(36), nullable=False, unique=True)
    issued_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    expires_at = Column(DateTime(timezone=True), nullable=False)
    revoked_at = Column(DateTime(timezone=True), nullable=True)
    revoked_reason = Column(String(100), nullable=True)
    user_agent = Column(String(255), nullable=True)
    ip_address = Column(String(45), nullable=True)

    user = relationship("User", back_populates="sessions")

    __table_args__ = (Index("uq_session_tokens_jti", "jti", unique=True),)


class ProcessedNonce(Base):
    __tablename__ = "processed_nonces"

    id = Column(GUID(), primary_key=True, default=uuid.uuid4)
    store_id = Column(GUID(), ForeignKey("stores.id"), nullable=False)
    nonce = Column(String(128), nullable=False)
    processed_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    expires_at = Column(DateTime(timezone=True), nullable=False)

    __table_args__ = (
        Index("uq_processed_nonces_store_nonce", "store_id", "nonce", unique=True),
        Index("ix_processed_nonces_expires", "expires_at"),
    )


class ProcessedWebhook(Base):
    __tablename__ = "processed_webhooks"

    id = Column(GUID(), primary_key=True, default=uuid.uuid4)
    provider = Column(String(50), nullable=False)
    event_id = Column(String(255), nullable=False, unique=True)
    event_type = Column(String(200), nullable=False)
    store_id = Column(GUID(), ForeignKey("stores.id"), nullable=True)
    status = Column(String(50), nullable=False, default="pending")
    attempts = Column(Integer, nullable=False, default=0)
    last_error = Column(Text, nullable=True)
    dead_letter = Column(Boolean, nullable=False, default=False)
    payload = Column(JSON, nullable=False)
    received_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    processed_at = Column(DateTime(timezone=True), nullable=True)
    next_retry_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())

    store = relationship("Store")

    __table_args__ = (
        Index("ix_processed_webhooks_provider", "provider"),
        Index("ix_processed_webhooks_status", "status"),
    )


class WebhookEvent(Base):
    __tablename__ = "webhook_events"

    id = Column(GUID(), primary_key=True, default=uuid.uuid4)
    store_id = Column(GUID(), ForeignKey("stores.id"), nullable=False)
    event_id = Column(String(255), nullable=False, unique=True)
    event_type = Column(String(100), nullable=False)
    payload = Column(JSON, nullable=False)
    status = Column(String(20), nullable=False, default="pending")
    attempts = Column(Integer, nullable=False, default=0)
    last_error = Column(Text, nullable=True)
    next_retry_at = Column(DateTime(timezone=True), nullable=True)
    delivered_at = Column(DateTime(timezone=True), nullable=True)
    dead_letter = Column(Boolean, nullable=False, default=False)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    store = relationship("Store")
    attempts_log = relationship(
        "WebhookDeliveryAttempt",
        back_populates="event",
        cascade="all, delete-orphan",
    )

    __table_args__ = (
        Index("ix_webhook_events_status", "status"),
        Index("ix_webhook_events_store", "store_id"),
    )


class WebhookDeliveryAttempt(Base):
    __tablename__ = "webhook_delivery_attempts"

    id = Column(GUID(), primary_key=True, default=uuid.uuid4)
    event_id = Column(GUID(), ForeignKey("webhook_events.id"), nullable=False)
    attempt = Column(Integer, nullable=False)
    requested_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    response_status = Column(Integer, nullable=True)
    error_message = Column(Text, nullable=True)
    duration_ms = Column(Integer, nullable=True)

    event = relationship("WebhookEvent", back_populates="attempts_log")

    __table_args__ = (
        Index("ix_webhook_delivery_attempts_event", "event_id"),
    )
