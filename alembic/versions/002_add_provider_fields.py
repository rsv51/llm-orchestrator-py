"""Add priority, weight, max_retries, timeout, rate_limit to Provider

Revision ID: 002
Revises: 001
Create Date: 2025-10-04 13:35:00
"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '002'
down_revision = '001'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Add missing fields to providers table."""
    # Add priority column
    op.add_column('providers', sa.Column('priority', sa.Integer(), nullable=False, server_default='100'))
    
    # Add weight column
    op.add_column('providers', sa.Column('weight', sa.Integer(), nullable=False, server_default='100'))
    
    # Add max_retries column
    op.add_column('providers', sa.Column('max_retries', sa.Integer(), nullable=False, server_default='3'))
    
    # Add timeout column
    op.add_column('providers', sa.Column('timeout', sa.Integer(), nullable=False, server_default='60'))
    
    # Add rate_limit column (nullable)
    op.add_column('providers', sa.Column('rate_limit', sa.Integer(), nullable=True))
    
    # Remove server defaults after creation (they're only for existing rows)
    op.alter_column('providers', 'priority', server_default=None)
    op.alter_column('providers', 'weight', server_default=None)
    op.alter_column('providers', 'max_retries', server_default=None)
    op.alter_column('providers', 'timeout', server_default=None)


def downgrade() -> None:
    """Remove added fields from providers table."""
    op.drop_column('providers', 'rate_limit')
    op.drop_column('providers', 'timeout')
    op.drop_column('providers', 'max_retries')
    op.drop_column('providers', 'weight')
    op.drop_column('providers', 'priority')