"""Add processed_nonces table and secret rotation timestamp"""
from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "202503150001"
down_revision: Union[str, None] = "202503010001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "store_settings",
        sa.Column("hmac_secret_rotated_at", sa.DateTime(timezone=True), nullable=True),
    )

    bind = op.get_bind()

    store_settings = sa.table(
        "store_settings",
        sa.column("hmac_secret", sa.Text()),
        sa.column("hmac_secret_rotated_at", sa.DateTime(timezone=True)),
    )
    op.execute(
        store_settings.update()
        .where(store_settings.c.hmac_secret.isnot(None))
        .where(store_settings.c.hmac_secret != "")
        .where(store_settings.c.hmac_secret_rotated_at.is_(None))
        .values(hmac_secret_rotated_at=sa.func.current_timestamp())
    )

    uuid_type = postgresql.UUID(as_uuid=True) if bind.dialect.name == "postgresql" else sa.String(length=36)

    op.create_table(
        "processed_nonces",
        sa.Column("id", uuid_type, nullable=False),
        sa.Column("store_id", uuid_type, sa.ForeignKey("stores.id"), nullable=False),
        sa.Column("nonce", sa.String(length=128), nullable=False),
        sa.Column(
            "processed_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "uq_processed_nonces_store_nonce",
        "processed_nonces",
        ["store_id", "nonce"],
        unique=True,
    )
    op.create_index("ix_processed_nonces_expires", "processed_nonces", ["expires_at"])


def downgrade() -> None:
    op.drop_index("ix_processed_nonces_expires", table_name="processed_nonces")
    op.drop_index("uq_processed_nonces_store_nonce", table_name="processed_nonces")
    op.drop_table("processed_nonces")
    op.drop_column("store_settings", "hmac_secret_rotated_at")
