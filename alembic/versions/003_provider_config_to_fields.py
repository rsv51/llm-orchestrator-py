"""Convert provider config JSON to separate fields

Revision ID: 003
Revises: 002
Create Date: 2025-10-04 17:58:00

"""
from alembic import op
import sqlalchemy as sa
import json


# revision identifiers, used by Alembic.
revision = '003'
down_revision = '002'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Convert provider config JSON to separate api_key and base_url fields."""
    
    # Add new columns (nullable first for migration)
    op.add_column('providers', sa.Column('api_key', sa.String(length=255), nullable=True))
    op.add_column('providers', sa.Column('base_url', sa.String(length=255), nullable=True))
    
    # Migrate existing data from config JSON to new columns
    connection = op.get_bind()
    
    # Read existing providers with config
    result = connection.execute(
        sa.text("SELECT id, config FROM providers WHERE config IS NOT NULL")
    )
    providers = result.fetchall()
    
    # Migrate each provider
    for provider_id, config_json in providers:
        try:
            config = json.loads(config_json) if config_json else {}
            api_key = config.get('api_key', '')
            base_url = config.get('base_url')
            
            connection.execute(
                sa.text("UPDATE providers SET api_key = :api_key, base_url = :base_url WHERE id = :id"),
                {"api_key": api_key, "base_url": base_url, "id": provider_id}
            )
            connection.commit()
        except (json.JSONDecodeError, Exception) as e:
            print(f"Warning: Failed to migrate provider {provider_id}: {e}")
            # Set empty api_key for failed migrations
            connection.execute(
                sa.text("UPDATE providers SET api_key = '' WHERE id = :id"),
                {"id": provider_id}
            )
            connection.commit()
    
    # Make api_key NOT NULL
    with op.batch_alter_table('providers') as batch_op:
        batch_op.alter_column('api_key', nullable=False, existing_type=sa.String(length=255))
    
    # Drop old config column
    op.drop_column('providers', 'config')


def downgrade() -> None:
    """Revert separate fields back to config JSON."""
    
    # Add config column back
    op.add_column('providers', sa.Column('config', sa.Text(), nullable=True))
    
    # Migrate data back to JSON
    connection = op.get_bind()
    
    result = connection.execute(
        sa.text("SELECT id, api_key, base_url FROM providers")
    )
    providers = result.fetchall()
    
    for provider_id, api_key, base_url in providers:
        config = {
            'api_key': api_key,
            'base_url': base_url
        }
        config_json = json.dumps(config)
        
        connection.execute(
            sa.text("UPDATE providers SET config = :config WHERE id = :id"),
            {"config": config_json, "id": provider_id}
        )
        connection.commit()
    
    # Make config NOT NULL
    with op.batch_alter_table('providers') as batch_op:
        batch_op.alter_column('config', nullable=False, existing_type=sa.Text())
    
    # Drop new columns
    op.drop_column('providers', 'base_url')
    op.drop_column('providers', 'api_key')