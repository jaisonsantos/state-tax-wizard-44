"""Add contact_email column to stores."""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "202510020003"
down_revision = "202510020002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "stores",
        sa.Column("contact_email", sa.String(length=255), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("stores", "contact_email")
