-- PostgreSQL Schema Initialization for q-task Queue System
-- This script is automatically executed when the PostgreSQL container starts for the first time
-- Creates the default task_queue and dead_letter_queue tables

-- =============================================================================
-- Queue Table: Stores pending and processing tasks
-- =============================================================================
CREATE TABLE IF NOT EXISTS task_queue (
    id SERIAL PRIMARY KEY,
    queue_name TEXT NOT NULL,
    payload BYTEA NOT NULL,
    available_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    locked_until TIMESTAMPTZ,
    status TEXT NOT NULL DEFAULT 'pending',
    attempts INTEGER NOT NULL DEFAULT 0,
    max_attempts INTEGER NOT NULL DEFAULT 3,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Create index for efficient queue lookup
-- Composite index on queue_name, status, and available_at for optimal dequeue performance
-- Note: We don't use a partial index with NOW() since NOW() is not IMMUTABLE
CREATE INDEX IF NOT EXISTS idx_task_queue_lookup
ON task_queue (queue_name, status, available_at, locked_until);

-- =============================================================================
-- Dead Letter Queue Table: Stores tasks that exceeded max retry attempts
-- =============================================================================
CREATE TABLE IF NOT EXISTS dead_letter_queue (
    id SERIAL PRIMARY KEY,
    queue_name TEXT NOT NULL,
    payload BYTEA NOT NULL,
    attempts INTEGER NOT NULL,
    error_message TEXT,
    failed_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- =============================================================================
-- Grant Permissions
-- =============================================================================
-- Ensure the test user has full access to the tables and sequences
GRANT ALL PRIVILEGES ON TABLE task_queue TO test;
GRANT ALL PRIVILEGES ON TABLE dead_letter_queue TO test;
GRANT ALL PRIVILEGES ON SEQUENCE task_queue_id_seq TO test;
GRANT ALL PRIVILEGES ON SEQUENCE dead_letter_queue_id_seq TO test;

-- =============================================================================
-- Verification
-- =============================================================================
-- Output confirmation message
DO $$
BEGIN
    RAISE NOTICE '✓ Schema initialized successfully!';
    RAISE NOTICE '  - Created table: task_queue';
    RAISE NOTICE '  - Created index: idx_task_queue_lookup';
    RAISE NOTICE '  - Created table: dead_letter_queue';
    RAISE NOTICE '  - Granted permissions to user: test';
END $$;
