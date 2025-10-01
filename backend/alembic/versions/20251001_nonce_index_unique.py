"""Ensure unique nonce index for replay protection"""

from alembic import op


revision = "20251001_nonce_index_unique"
down_revision = "202503150001"
branch_labels = None
depends_on = None


def upgrade():
    op.execute(
        """
    CREATE UNIQUE INDEX IF NOT EXISTS uq_processed_nonces_store_nonce
    ON processed_nonces (store_id, nonce);
    """
    )
    op.execute(
        """
    CREATE INDEX IF NOT EXISTS ix_processed_nonces_expires
    ON processed_nonces (expires_at);
    """
    )


def downgrade():
    op.execute("DROP INDEX IF EXISTS ix_processed_nonces_expires;")
    op.execute("DROP INDEX IF EXISTS uq_processed_nonces_store_nonce;")
