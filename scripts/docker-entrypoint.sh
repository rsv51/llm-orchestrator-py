#!/bin/bash
set -e

echo "🚀 Starting LLM Orchestrator..."

# Wait a bit for database to be ready (for Docker Compose)
if [ "${REDIS_ENABLED:-true}" = "true" ]; then
    echo "⏳ Waiting for Redis..."
    sleep 5
fi

# Run database migrations (will auto-create tables)
echo "📦 Running database migrations..."
if alembic upgrade head 2>&1; then
    echo "✅ Database migrations completed"
else
    echo "⚠️ Migration failed, attempting to continue..."
fi

# Initialize database with default data if needed
echo "🔧 Initializing database..."
python scripts/init_db.py 2>&1 || echo "⚠️ Init failed, continuing..."

# Start the application
echo "✅ Starting application server..."
exec uvicorn app.main:app --host 0.0.0.0 --port 8000