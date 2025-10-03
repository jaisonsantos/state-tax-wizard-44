"""Initial application schema."""
import uuid

from alembic import op
import sqlalchemy as sa
from sqlalchemy.types import CHAR, TypeDecorator

# revision identifiers, used by Alembic.
revision = "202501010000"
down_revision = None
branch_labels = None
depends_on = None

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


def upgrade() -> None:
    op.create_table(
        "stores",
        sa.Column("id", GUID(), primary_key=True, nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("platform", sa.String(length=20), nullable=False),
        sa.Column("domain", sa.String(length=255), nullable=False),
        sa.Column("country", sa.String(length=2), nullable=False, server_default=sa.text("'US'")),
        sa.Column("state", sa.String(length=2), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
    )

    op.create_table(
        "store_settings",
        sa.Column("store_id", GUID(), sa.ForeignKey("stores.id"), primary_key=True),
        sa.Column("enable_mn", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("enable_co", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("absorb_fee", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("label_override", sa.Text(), nullable=False, server_default=sa.text("'Delivery Fee'")),
        sa.Column("plan", sa.String(length=20), nullable=False, server_default=sa.text("'starter'")),
    )

    op.create_table(
        "rule_versions",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("jurisdiction", sa.String(length=2), nullable=False),
        sa.Column("version", sa.String(length=50), nullable=False),
        sa.Column("effective_from", sa.DateTime(timezone=True), nullable=False),
        sa.Column("effective_to", sa.DateTime(timezone=True), nullable=True),
        sa.Column("params", sa.JSON(), nullable=False),
    )

    op.create_table(
        "users",
        sa.Column("id", GUID(), primary_key=True, nullable=False),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.UniqueConstraint("email", name="uq_users_email"),
    )

    op.create_table(
        "subscriptions",
        sa.Column("id", GUID(), primary_key=True, nullable=False),
        sa.Column("store_id", GUID(), sa.ForeignKey("stores.id"), nullable=False),
        sa.Column("provider", sa.String(length=20), nullable=False),
        sa.Column("plan", sa.String(length=20), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("trial_end", sa.DateTime(timezone=True), nullable=True),
        sa.Column("current_period_end", sa.DateTime(timezone=True), nullable=True),
    )

    op.create_table(
        "audit_logs",
        sa.Column("id", GUID(), primary_key=True, nullable=False),
        sa.Column(
            "ts",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.Column("actor", sa.String(length=255), nullable=False),
        sa.Column("action", sa.String(length=100), nullable=False),
        sa.Column("payload", sa.JSON(), nullable=False),
    )

    op.create_table(
        "order_fees",
        sa.Column("id", GUID(), primary_key=True, nullable=False),
        sa.Column("store_id", GUID(), sa.ForeignKey("stores.id"), nullable=False),
        sa.Column("order_id", sa.String(length=100), nullable=False),
        sa.Column("jurisdiction", sa.String(length=2), nullable=False),
        sa.Column("amount_cents", sa.Integer(), nullable=False),
        sa.Column(
            "applied_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.Column("delivery_method", sa.String(length=20), nullable=False),
        sa.Column("absorbed", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("rule_version", sa.String(length=50), nullable=False),
        sa.Column("reason_codes", sa.JSON(), nullable=False),
        sa.UniqueConstraint("store_id", "order_id", "jurisdiction", name="uq_order_fee_store_order_jurisdiction"),
    )

    op.create_table(
        "user_stores",
        sa.Column("user_id", GUID(), sa.ForeignKey("users.id"), primary_key=True, nullable=False),
        sa.Column("store_id", GUID(), sa.ForeignKey("stores.id"), primary_key=True, nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.UniqueConstraint("user_id", "store_id", name="uq_user_store"),
    )


def downgrade() -> None:
    op.drop_table("user_stores")
    op.drop_table("order_fees")
    op.drop_table("audit_logs")
    op.drop_table("subscriptions")
    op.drop_table("users")
    op.drop_table("rule_versions")
    op.drop_table("store_settings")
    op.drop_table("stores")
