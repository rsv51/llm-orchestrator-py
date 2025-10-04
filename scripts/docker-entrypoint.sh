#!/bin/bash
set -e

echo "🚀 Starting LLM Orchestrator..."

# Wait a bit for database to be ready (for Docker Compose)
if [ "${REDIS_ENABLED:-true}" = "true" ]; then
    echo "⏳ Waiting for Redis..."
    sleep 5
fi

# Run database migrations (auto-creates all tables)
echo "📦 Running database migrations..."
alembic upgrade head

# Start the application
echo "✅ Starting application server..."
exec uvicorn app.main:app --host 0.0.0.0 --port 8000