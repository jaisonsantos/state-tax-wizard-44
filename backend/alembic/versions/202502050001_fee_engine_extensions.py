"""Fee engine extensions for MVP finalization"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "202502050001"
down_revision: Union[str, None] = "202501010000"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "order_fees",
        sa.Column("display_name", sa.Text(), nullable=True),
    )
    op.add_column(
        "order_fees",
        sa.Column("status", sa.String(length=20), nullable=False, server_default="applied"),
    )
    op.add_column(
        "order_fees",
        sa.Column("reversal_reason", sa.String(length=50), nullable=True),
    )
    op.add_column(
        "order_fees",
        sa.Column("reversed_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "order_fees",
        sa.Column("source_of_remittance", sa.String(length=20), nullable=True),
    )

    op.add_column(
        "store_settings",
        sa.Column("hmac_secret", sa.Text(), nullable=True),
    )

    # Ensure existing rows adopt the new defaults
    op.execute("UPDATE order_fees SET status='applied' WHERE status IS NULL")


def downgrade() -> None:
    op.drop_column("store_settings", "hmac_secret")
    op.drop_column("order_fees", "source_of_remittance")
    op.drop_column("order_fees", "reversed_at")
    op.drop_column("order_fees", "reversal_reason")
    op.drop_column("order_fees", "status")
    op.drop_column("order_fees", "display_name")
