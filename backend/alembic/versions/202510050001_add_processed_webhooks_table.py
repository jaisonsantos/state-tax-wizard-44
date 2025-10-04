"""add processed webhooks table

Revision ID: 202510050001
Revises: 202510020003_add_store_contact_email
Create Date: 2025-10-05 00:00:00
"""

from __future__ import annotations

import uuid

from alembic import op
import sqlalchemy as sa
from sqlalchemy import TypeDecorator, CHAR


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


# revision identifiers, used by Alembic.
revision = "202510050001"
down_revision = "202510020003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "processed_webhooks",
        sa.Column("id", GUID(), primary_key=True, nullable=False),
        sa.Column("provider", sa.String(length=50), nullable=False),
        sa.Column("event_id", sa.String(length=255), nullable=False, unique=True),
        sa.Column("event_type", sa.String(length=200), nullable=False),
        sa.Column("store_id", GUID(), sa.ForeignKey("stores.id"), nullable=True),
        sa.Column("status", sa.String(length=50), nullable=False, server_default="pending"),
        sa.Column("attempts", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("last_error", sa.Text(), nullable=True),
        sa.Column("dead_letter", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("payload", sa.JSON(), nullable=False),
        sa.Column("received_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("processed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("next_retry_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
            onupdate=sa.func.now(),
        ),
    )
    op.create_index(
        "ix_processed_webhooks_provider",
        "processed_webhooks",
        ["provider"],
    )
    op.create_index(
        "ix_processed_webhooks_status",
        "processed_webhooks",
        ["status"],
    )


def downgrade() -> None:
    op.drop_index("ix_processed_webhooks_status", table_name="processed_webhooks")
    op.drop_index("ix_processed_webhooks_provider", table_name="processed_webhooks")
    op.drop_table("processed_webhooks")
