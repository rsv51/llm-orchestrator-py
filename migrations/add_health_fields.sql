-- Migration: Add new health tracking fields to provider_health table
-- Created: 2025-10-04
-- Description: Add fields required by SystemHealthResponse schema

-- Add new columns with default values
ALTER TABLE provider_health
ADD COLUMN IF NOT EXISTS response_time_ms REAL DEFAULT 0.0,
ADD COLUMN IF NOT EXISTS error_message TEXT,
ADD COLUMN IF NOT EXISTS last_check TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
ADD COLUMN IF NOT EXISTS consecutive_failures INTEGER DEFAULT 0,
ADD COLUMN IF NOT EXISTS success_rate REAL DEFAULT 100.0;

-- Update existing records to use new field mappings
UPDATE provider_health
SET 
    last_check = COALESCE(last_validated_at, CURRENT_TIMESTAMP),
    error_message = last_error,
    consecutive_failures = error_count
WHERE last_check IS NULL;

-- Create index for better query performance
CREATE INDEX IF NOT EXISTS idx_health_last_check ON provider_health(last_check);

-- Verify migration
SELECT 
    provider_id,
    is_healthy,
    response_time_ms,
    last_check,
    consecutive_failures,
    success_rate
FROM provider_health
LIMIT 5;