"""billing_stripe_integration

Revision ID: 202510020001
Revises: 202510010002
Create Date: 2025-10-02 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '202510020001'
down_revision = '202510010002'
branch_labels = None
depends_on = None


def upgrade():
    # Add Stripe customer/subscription fields to stores table
    op.add_column('stores', sa.Column('stripe_customer_id', sa.String(255), nullable=True, unique=True))
    op.add_column('stores', sa.Column('stripe_subscription_id', sa.String(255), nullable=True))
    
    # Update subscriptions table with Stripe-specific fields
    op.add_column('subscriptions', sa.Column('stripe_subscription_id', sa.String(255), nullable=True, unique=True))
    op.add_column('subscriptions', sa.Column('stripe_customer_id', sa.String(255), nullable=True))
    op.add_column('subscriptions', sa.Column('plan_tier', sa.String(50), nullable=True))
    op.add_column('subscriptions', sa.Column('cancel_at_period_end', sa.Boolean(), server_default='false'))
    op.add_column('subscriptions', sa.Column('updated_at', sa.TIMESTAMP(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP')))
    
    # Backfill plan_tier from existing plan column
    op.execute("""
        UPDATE subscriptions 
        SET plan_tier = CASE 
            WHEN plan = 'starter' THEN 'starter'
            WHEN plan = 'pro' THEN 'pro'
            WHEN plan = 'plus' THEN 'plus'
            ELSE 'starter'
        END
        WHERE plan_tier IS NULL
    """)
    
    # Make plan_tier NOT NULL after backfill
    op.alter_column('subscriptions', 'plan_tier', nullable=False)


def downgrade():
    op.drop_column('subscriptions', 'updated_at')
    op.drop_column('subscriptions', 'cancel_at_period_end')
    op.drop_column('subscriptions', 'plan_tier')
    op.drop_column('subscriptions', 'stripe_customer_id')
    op.drop_column('subscriptions', 'stripe_subscription_id')
    op.drop_column('stores', 'stripe_subscription_id')
    op.drop_column('stores', 'stripe_customer_id')
