"""Ensure processed_nonces unique index exists"""
from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "202510010001"
down_revision: Union[str, None] = "202503150001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        sa.text(
            """
            DELETE FROM processed_nonces
            WHERE id IN (
                SELECT id
                FROM (
                    SELECT id,
                           ROW_NUMBER() OVER (
                               PARTITION BY store_id, nonce
                               ORDER BY processed_at, id
                           ) AS rn
                    FROM processed_nonces
                ) AS duplicates
                WHERE duplicates.rn > 1
            )
            """
        )
    )

    op.execute(
        sa.text(
            """
            CREATE UNIQUE INDEX IF NOT EXISTS uq_processed_nonces_store_nonce
            ON processed_nonces (store_id, nonce)
            """
        )
    )

    op.execute(
        sa.text(
            """
            CREATE INDEX IF NOT EXISTS ix_processed_nonces_expires
            ON processed_nonces (expires_at)
            """
        )
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_processed_nonces_expires")
    op.execute("DROP INDEX IF EXISTS uq_processed_nonces_store_nonce")
