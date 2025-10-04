"""Initial database schema

Revision ID: 001
Revises: 
Create Date: 2025-10-04 13:00:00
"""
from alembic import op
import sqlalchemy as sa
from datetime import datetime


# revision identifiers, used by Alembic.
revision = '001'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create initial database tables."""
    
    # Create providers table
    op.create_table(
        'providers',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(100), nullable=False),
        sa.Column('type', sa.String(50), nullable=False),
        sa.Column('config', sa.Text(), nullable=False),
        sa.Column('console', sa.String(255), nullable=True),
        sa.Column('enabled', sa.Boolean(), nullable=True, server_default='1'),
        sa.Column('created_at', sa.DateTime(), nullable=True, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('updated_at', sa.DateTime(), nullable=True, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_providers_name', 'providers', ['name'], unique=True)
    op.create_index('ix_providers_type', 'providers', ['type'])
    op.create_index('idx_provider_type_enabled', 'providers', ['type', 'enabled'])
    
    # Create models table
    op.create_table(
        'models',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(100), nullable=False),
        sa.Column('remark', sa.String(255), nullable=True),
        sa.Column('max_retry', sa.Integer(), nullable=True, server_default='3'),
        sa.Column('timeout', sa.Integer(), nullable=True, server_default='30'),
        sa.Column('enabled', sa.Boolean(), nullable=True, server_default='1'),
        sa.Column('created_at', sa.DateTime(), nullable=True, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('updated_at', sa.DateTime(), nullable=True, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_models_name', 'models', ['name'], unique=True)
    op.create_index('idx_model_name_enabled', 'models', ['name', 'enabled'])
    
    # Create model_providers table
    op.create_table(
        'model_providers',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('model_id', sa.Integer(), nullable=False),
        sa.Column('provider_id', sa.Integer(), nullable=False),
        sa.Column('provider_model', sa.String(100), nullable=False),
        sa.Column('weight', sa.Integer(), nullable=True, server_default='1'),
        sa.Column('tool_call', sa.Boolean(), nullable=True, server_default='1'),
        sa.Column('structured_output', sa.Boolean(), nullable=True, server_default='1'),
        sa.Column('image', sa.Boolean(), nullable=True, server_default='0'),
        sa.Column('enabled', sa.Boolean(), nullable=True, server_default='1'),
        sa.Column('created_at', sa.DateTime(), nullable=True, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('updated_at', sa.DateTime(), nullable=True, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.ForeignKeyConstraint(['model_id'], ['models.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['provider_id'], ['providers.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_model_provider', 'model_providers', ['model_id', 'provider_id'])
    op.create_index('idx_model_enabled', 'model_providers', ['model_id', 'enabled'])
    op.create_index('idx_provider_enabled', 'model_providers', ['provider_id', 'enabled'])
    
    # Create request_logs table
    op.create_table(
        'request_logs',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('provider_id', sa.Integer(), nullable=False),
        sa.Column('model', sa.String(100), nullable=True),
        sa.Column('endpoint', sa.String(255), nullable=True),
        sa.Column('method', sa.String(10), nullable=True),
        sa.Column('status_code', sa.Integer(), nullable=True),
        sa.Column('prompt_tokens', sa.Integer(), nullable=True),
        sa.Column('completion_tokens', sa.Integer(), nullable=True),
        sa.Column('total_tokens', sa.Integer(), nullable=True),
        sa.Column('cost', sa.Float(), nullable=True),
        sa.Column('latency_ms', sa.Integer(), nullable=True),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('user_id', sa.String(100), nullable=True),
        sa.Column('ip_address', sa.String(50), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.ForeignKeyConstraint(['provider_id'], ['providers.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_request_log_provider', 'request_logs', ['provider_id'])
    op.create_index('idx_request_log_created', 'request_logs', ['created_at'])
    op.create_index('idx_request_log_user', 'request_logs', ['user_id'])
    
    # Create provider_health table
    op.create_table(
        'provider_health',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('provider_id', sa.Integer(), nullable=False),
        sa.Column('is_healthy', sa.Boolean(), nullable=True, server_default='1'),
        sa.Column('response_time_ms', sa.Float(), nullable=True),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('last_check', sa.DateTime(), nullable=True, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('consecutive_failures', sa.Integer(), nullable=True, server_default='0'),
        sa.Column('success_rate', sa.Float(), nullable=True, server_default='100.0'),
        sa.ForeignKeyConstraint(['provider_id'], ['providers.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_provider_health_provider_id', 'provider_health', ['provider_id'], unique=True)
    
    # Create provider_stats table
    op.create_table(
        'provider_stats',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('provider_id', sa.Integer(), nullable=False),
        sa.Column('total_requests', sa.Integer(), nullable=True, server_default='0'),
        sa.Column('successful_requests', sa.Integer(), nullable=True, server_default='0'),
        sa.Column('failed_requests', sa.Integer(), nullable=True, server_default='0'),
        sa.Column('total_tokens', sa.Integer(), nullable=True, server_default='0'),
        sa.Column('total_cost', sa.Float(), nullable=True, server_default='0.0'),
        sa.Column('avg_latency_ms', sa.Float(), nullable=True, server_default='0.0'),
        sa.Column('last_updated', sa.DateTime(), nullable=True, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.ForeignKeyConstraint(['provider_id'], ['providers.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_provider_stats_provider_id', 'provider_stats', ['provider_id'], unique=True)


def downgrade() -> None:
    """Drop all tables."""
    op.drop_table('provider_stats')
    op.drop_table('provider_health')
    op.drop_table('request_logs')
    op.drop_table('model_providers')
    op.drop_table('models')
    op.drop_table('providers')