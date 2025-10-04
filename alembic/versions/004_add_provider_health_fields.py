"""Add missing provider_health fields

Revision ID: 004
Revises: 003
Create Date: 2025-10-04 15:00:00
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import text

# revision identifiers, used by Alembic.
revision = '004'
down_revision = '003'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Add missing fields to provider_health table."""
    
    # Add new columns with batch_alter_table for SQLite compatibility
    with op.batch_alter_table('provider_health', schema=None) as batch_op:
        # Add response_time_ms
        batch_op.add_column(
            sa.Column('response_time_ms', sa.Float(), nullable=True, server_default='0.0')
        )
        
        # Add error_message
        batch_op.add_column(
            sa.Column('error_message', sa.Text(), nullable=True)
        )
        
        # Add last_check
        batch_op.add_column(
            sa.Column('last_check', sa.DateTime(), nullable=True, 
                     server_default=sa.text('CURRENT_TIMESTAMP'))
        )
        
        # Add consecutive_failures
        batch_op.add_column(
            sa.Column('consecutive_failures', sa.Integer(), nullable=True, server_default='0')
        )
        
        # Add success_rate
        batch_op.add_column(
            sa.Column('success_rate', sa.Float(), nullable=True, server_default='100.0')
        )
        
        # Create index for last_check
        batch_op.create_index(
            'idx_health_last_check', ['last_check'], unique=False
        )
    
    # Update existing records to populate new fields from old fields
    connection = op.get_bind()
    connection.execute(
        text("""
            UPDATE provider_health
            SET 
                last_check = COALESCE(last_validated_at, CURRENT_TIMESTAMP),
                error_message = last_error,
                consecutive_failures = error_count,
                response_time_ms = 0.0,
                success_rate = CASE 
                    WHEN is_healthy = 1 THEN 100.0 
                    ELSE 0.0 
                END
            WHERE last_check IS NULL
        """)
    )


def downgrade() -> None:
    """Remove added fields from provider_health table."""
    
    with op.batch_alter_table('provider_health', schema=None) as batch_op:
        # Drop index
        batch_op.drop_index('idx_health_last_check')
        
        # Drop columns
        batch_op.drop_column('success_rate')
        batch_op.drop_column('consecutive_failures')
        batch_op.drop_column('last_check')
        batch_op.drop_column('error_message')
        batch_op.drop_column('response_time_ms')