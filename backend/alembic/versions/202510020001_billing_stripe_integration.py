"""billing_stripe_integration

Revision ID: 202510020001
Revises: 202510010002
Create Date: 2025-10-02 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "202510020001"
down_revision = "202510010002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add Stripe customer/subscription fields to stores table
    op.add_column(
        "stores",
        sa.Column("stripe_customer_id", sa.String(length=255), nullable=True),
    )
    op.add_column(
        "stores",
        sa.Column("stripe_subscription_id", sa.String(length=255), nullable=True),
    )
    op.create_index(
        "uq_stores_stripe_customer_id",
        "stores",
        ["stripe_customer_id"],
        unique=True,
    )

    # Update subscriptions table with Stripe-specific fields
    op.add_column(
        "subscriptions",
        sa.Column("stripe_subscription_id", sa.String(length=255), nullable=True),
    )
    op.add_column(
        "subscriptions",
        sa.Column("stripe_customer_id", sa.String(length=255), nullable=True),
    )
    op.add_column(
        "subscriptions",
        sa.Column("plan_tier", sa.String(length=50), nullable=True),
    )
    op.add_column(
        "subscriptions",
        sa.Column(
            "cancel_at_period_end",
            sa.Boolean(),
            server_default=sa.text("false"),
        ),
    )
    op.add_column(
        "subscriptions",
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
    )
    op.create_index(
        "uq_subscriptions_stripe_subscription_id",
        "subscriptions",
        ["stripe_subscription_id"],
        unique=True,
    )

    # Backfill plan_tier from existing plan column
    op.execute(
        """
        UPDATE subscriptions
        SET plan_tier = CASE
            WHEN plan = 'starter' THEN 'starter'
            WHEN plan = 'pro' THEN 'pro'
            WHEN plan = 'plus' THEN 'plus'
            ELSE 'starter'
        END
        WHERE plan_tier IS NULL
        """
    )

    # Make plan_tier NOT NULL after backfill
    bind = op.get_bind()
    if bind.dialect.name == "sqlite":
        with op.batch_alter_table("subscriptions") as batch_op:
            batch_op.alter_column(
                "plan_tier",
                existing_type=sa.String(length=50),
                nullable=False,
            )
    else:
        op.alter_column(
            "subscriptions",
            "plan_tier",
            existing_type=sa.String(length=50),
            nullable=False,
        )


def downgrade() -> None:
    op.drop_index(
        "uq_subscriptions_stripe_subscription_id",
        table_name="subscriptions",
    )
    op.drop_index("uq_stores_stripe_customer_id", table_name="stores")

    op.drop_column("subscriptions", "updated_at")
    op.drop_column("subscriptions", "cancel_at_period_end")
    op.drop_column("subscriptions", "plan_tier")
    op.drop_column("subscriptions", "stripe_customer_id")
    op.drop_column("subscriptions", "stripe_subscription_id")
    op.drop_column("stores", "stripe_subscription_id")
    op.drop_column("stores", "stripe_customer_id")
