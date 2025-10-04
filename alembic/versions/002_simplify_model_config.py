"""Simplify model config schema (remove pricing and context fields)

Revision ID: 002_simplify_model_config
Revises: 001_initial_schema
Create Date: 2025-10-04 15:58:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '002_simplify_model_config'
down_revision: Union[str, None] = '001'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """
    Simplify models table to match llmio-master architecture:
    - Remove display_name
    - Remove description  
    - Remove context_length
    - Remove max_output_tokens
    - Remove input_price_per_million
    - Remove output_price_per_million
    - Remove supports_streaming
    - Remove supports_functions
    - Remove supports_vision
    - Remove metadata
    
    Keep only: id, name, remark, max_retry, timeout, enabled, created_at, updated_at
    """
    
    # Check which columns exist before trying to drop them
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    columns = [col['name'] for col in inspector.get_columns('models')]
    
    # Drop columns if they exist
    with op.batch_alter_table('models', schema=None) as batch_op:
        if 'display_name' in columns:
            batch_op.drop_column('display_name')
        if 'description' in columns:
            batch_op.drop_column('description')
        if 'context_length' in columns:
            batch_op.drop_column('context_length')
        if 'max_output_tokens' in columns:
            batch_op.drop_column('max_output_tokens')
        if 'input_price_per_million' in columns:
            batch_op.drop_column('input_price_per_million')
        if 'output_price_per_million' in columns:
            batch_op.drop_column('output_price_per_million')
        if 'supports_streaming' in columns:
            batch_op.drop_column('supports_streaming')
        if 'supports_functions' in columns:
            batch_op.drop_column('supports_functions')
        if 'supports_vision' in columns:
            batch_op.drop_column('supports_vision')
        if 'metadata' in columns:
            batch_op.drop_column('metadata')


def downgrade() -> None:
    """Re-add removed columns with default values."""
    
    with op.batch_alter_table('models', schema=None) as batch_op:
        batch_op.add_column(sa.Column('display_name', sa.String(length=100), nullable=True))
        batch_op.add_column(sa.Column('description', sa.Text(), nullable=True))
        batch_op.add_column(sa.Column('context_length', sa.Integer(), nullable=False, server_default='8192'))
        batch_op.add_column(sa.Column('max_output_tokens', sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column('input_price_per_million', sa.Float(), nullable=False, server_default='0.0'))
        batch_op.add_column(sa.Column('output_price_per_million', sa.Float(), nullable=False, server_default='0.0'))
        batch_op.add_column(sa.Column('supports_streaming', sa.Boolean(), nullable=False, server_default='1'))
        batch_op.add_column(sa.Column('supports_functions', sa.Boolean(), nullable=False, server_default='0'))
        batch_op.add_column(sa.Column('supports_vision', sa.Boolean(), nullable=False, server_default='0'))
        batch_op.add_column(sa.Column('metadata', sa.Text(), nullable=True))