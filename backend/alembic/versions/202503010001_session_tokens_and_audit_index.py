"""Create session_tokens table and audit index"""

import uuid

from alembic import op
import sqlalchemy as sa
from sqlalchemy.types import CHAR, TypeDecorator


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
            return value if dialect.name == "postgresql" else str(value)
        return str(uuid.UUID(str(value)))

    def process_result_value(self, value, dialect):
        if value is None:
            return value
        return value if isinstance(value, uuid.UUID) else uuid.UUID(str(value))

# revision identifiers, used by Alembic.
revision = "202503010001"
down_revision = "202502050001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "session_tokens",
        sa.Column("id", GUID(), nullable=False),
        sa.Column(
            "user_id",
            GUID(),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("jti", sa.String(length=36), nullable=False),
        sa.Column(
            "issued_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("revoked_reason", sa.String(length=100), nullable=True),
        sa.Column("user_agent", sa.String(length=255), nullable=True),
        sa.Column("ip_address", sa.String(length=45), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_session_tokens_user_id", "session_tokens", ["user_id"])
    op.create_index(
        "uq_session_tokens_jti",
        "session_tokens",
        ["jti"],
        unique=True,
    )

    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        op.execute(
            "CREATE INDEX IF NOT EXISTS idx_audit_logs_store_action_ts "
            "ON audit_logs ((payload->>'store_id'), action, ts DESC)"
        )
    else:
        op.create_index(
            "idx_audit_logs_action_ts",
            "audit_logs",
            ["action", "ts"],
        )


def downgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        op.execute("DROP INDEX IF EXISTS idx_audit_logs_store_action_ts")
    else:
        op.drop_index("idx_audit_logs_action_ts", table_name="audit_logs")

    op.drop_index("ix_session_tokens_user_id", table_name="session_tokens")
    op.drop_index("uq_session_tokens_jti", table_name="session_tokens")
    op.drop_table("session_tokens")
