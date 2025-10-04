"""Add Taxo webhook outbox tables and store settings columns"""

from __future__ import annotations

import uuid

from alembic import op
import sqlalchemy as sa
from sqlalchemy import CHAR, TypeDecorator


class GUID(TypeDecorator):
    """Platform-independent GUID/UUID type."""

    impl = CHAR
    cache_ok = True

    def load_dialect_impl(self, dialect):
        if dialect.name == "postgresql":
            from sqlalchemy.dialects.postgresql import UUID as PGUUID

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


revision = "202510060001"
down_revision = "202510050001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "store_settings",
        sa.Column("webhook_endpoint", sa.Text(), nullable=True),
    )
    op.add_column(
        "store_settings",
        sa.Column(
            "webhook_active",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
    )
    op.add_column(
        "store_settings",
        sa.Column(
            "webhook_events",
            sa.JSON(),
            nullable=False,
            server_default=sa.text("'[]'"),
        ),
    )

    op.create_table(
        "webhook_events",
        sa.Column("id", GUID(), primary_key=True, nullable=False),
        sa.Column("store_id", GUID(), sa.ForeignKey("stores.id"), nullable=False),
        sa.Column("event_id", sa.String(length=255), nullable=False, unique=True),
        sa.Column("event_type", sa.String(length=100), nullable=False),
        sa.Column("payload", sa.JSON(), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="pending"),
        sa.Column("attempts", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("last_error", sa.Text(), nullable=True),
        sa.Column("next_retry_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("delivered_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("dead_letter", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
            onupdate=sa.func.now(),
        ),
    )
    op.create_index("ix_webhook_events_status", "webhook_events", ["status"])
    op.create_index("ix_webhook_events_store", "webhook_events", ["store_id"])

    op.create_table(
        "webhook_delivery_attempts",
        sa.Column("id", GUID(), primary_key=True, nullable=False),
        sa.Column("event_id", GUID(), sa.ForeignKey("webhook_events.id"), nullable=False),
        sa.Column("attempt", sa.Integer(), nullable=False),
        sa.Column("requested_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("response_status", sa.Integer(), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("duration_ms", sa.Integer(), nullable=True),
    )
    op.create_index(
        "ix_webhook_delivery_attempts_event",
        "webhook_delivery_attempts",
        ["event_id"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_webhook_delivery_attempts_event", table_name="webhook_delivery_attempts"
    )
    op.drop_table("webhook_delivery_attempts")
    op.drop_index("ix_webhook_events_store", table_name="webhook_events")
    op.drop_index("ix_webhook_events_status", table_name="webhook_events")
    op.drop_table("webhook_events")
    op.drop_column("store_settings", "webhook_events")
    op.drop_column("store_settings", "webhook_active")
    op.drop_column("store_settings", "webhook_endpoint")
