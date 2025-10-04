#!/bin/bash
set -e

echo "🚀 Starting LLM Orchestrator..."

# Wait for database to be ready
echo "⏳ Waiting for database..."
python -c "
import time
import sys
from sqlalchemy import create_engine
from app.core.config import get_settings

settings = get_settings()
max_retries = 30
retry_interval = 2

for i in range(max_retries):
    try:
        engine = create_engine(settings.database_url)
        conn = engine.connect()
        conn.close()
        print('✅ Database is ready!')
        sys.exit(0)
    except Exception as e:
        if i < max_retries - 1:
            print(f'⏳ Database not ready yet, retrying in {retry_interval}s... ({i+1}/{max_retries})')
            time.sleep(retry_interval)
        else:
            print(f'❌ Database connection failed after {max_retries} attempts')
            sys.exit(1)
"

# Run database migrations
echo "📦 Running database migrations..."
alembic upgrade head

# Initialize database with default data if needed
echo "🔧 Initializing database..."
python scripts/init_db.py || true

# Start the application
echo "✅ Starting application server..."
exec uvicorn app.main:app --host 0.0.0.0 --port 8000