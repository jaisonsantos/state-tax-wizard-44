"""Add current_period_start to subscriptions

Revision ID: 202510020002
Revises: 202510020001
Create Date: 2025-10-05 00:00:00.000000

"""
from __future__ import annotations

from datetime import timedelta, timezone

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "202510020002"
down_revision = "202510020001"
branch_labels = None
depends_on = None


subscriptions_table = sa.table(
    "subscriptions",
    sa.column("id", sa.String()),
    sa.column("current_period_end", sa.DateTime(timezone=True)),
    sa.column("current_period_start", sa.DateTime(timezone=True)),
)


def _normalise_period_end(raw_value):
    if raw_value is None:
        return None
    if getattr(raw_value, "tzinfo", None) is None:
        return raw_value.replace(tzinfo=timezone.utc)
    return raw_value


def upgrade() -> None:
    with op.batch_alter_table("subscriptions") as batch_op:
        batch_op.add_column(
            sa.Column("current_period_start", sa.DateTime(timezone=True), nullable=True)
        )

    bind = op.get_bind()
    result = bind.execute(sa.select(subscriptions_table.c.id, subscriptions_table.c.current_period_end))
    for row in result:
        period_end = _normalise_period_end(row.current_period_end)
        period_start = None
        if period_end is not None:
            period_start = period_end - timedelta(days=30)
        bind.execute(
            subscriptions_table.update()
            .where(subscriptions_table.c.id == row.id)
            .values(current_period_start=period_start)
        )


def downgrade() -> None:
    with op.batch_alter_table("subscriptions") as batch_op:
        batch_op.drop_column("current_period_start")
