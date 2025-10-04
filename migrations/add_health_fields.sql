-- Migration: Add new health tracking fields to provider_health table
-- Created: 2025-10-04
-- Description: Add fields required by SystemHealthResponse schema
-- SQLite compatible version: Add columns one by one

-- Step 1: Add response_time_ms column
ALTER TABLE provider_health ADD COLUMN response_time_ms REAL DEFAULT 0.0;

-- Step 2: Add error_message column
ALTER TABLE provider_health ADD COLUMN error_message TEXT;

-- Step 3: Add last_check column
ALTER TABLE provider_health ADD COLUMN last_check TIMESTAMP DEFAULT CURRENT_TIMESTAMP;

-- Step 4: Add consecutive_failures column
ALTER TABLE provider_health ADD COLUMN consecutive_failures INTEGER DEFAULT 0;

-- Step 5: Add success_rate column
ALTER TABLE provider_health ADD COLUMN success_rate REAL DEFAULT 100.0;

-- Step 6: Update existing records to use new field mappings
UPDATE provider_health
SET
    last_check = COALESCE(last_validated_at, CURRENT_TIMESTAMP),
    error_message = last_error,
    consecutive_failures = error_count
WHERE last_check IS NULL OR last_check = '';

-- Step 7: Create index for better query performance
CREATE INDEX IF NOT EXISTS idx_health_last_check ON provider_health(last_check);

-- Step 8: Verify migration
SELECT
    provider_id,
    is_healthy,
    response_time_ms,
    last_check,
    consecutive_failures,
    success_rate
FROM provider_health
LIMIT 5;