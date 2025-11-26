-- MySQL 8.0+ Schema Initialization for async-task Queue System
-- This script is automatically executed when the MySQL container starts for the first time
-- Creates the default task_queue and dead_letter_queue tables
--
-- Requirements:
--   - MySQL 8.0+ (for SKIP LOCKED support and DATETIME(6) precision)
--   - InnoDB storage engine (for row-level locking and transactions)
--   - utf8mb4 charset (for full Unicode support)

-- =============================================================================
-- Queue Table: Stores pending and processing tasks
-- =============================================================================
CREATE TABLE IF NOT EXISTS task_queue (
    id INT AUTO_INCREMENT PRIMARY KEY,
    queue_name VARCHAR(255) NOT NULL,
    payload BLOB NOT NULL,
    available_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
    locked_until DATETIME(6) NULL,
    status VARCHAR(50) NOT NULL DEFAULT 'pending',
    attempts INT NOT NULL DEFAULT 0,
    max_attempts INT NOT NULL DEFAULT 3,
    created_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
    updated_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6) ON UPDATE CURRENT_TIMESTAMP(6),
    INDEX idx_task_queue_lookup (queue_name, status, available_at, locked_until)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- =============================================================================
-- Dead Letter Queue Table: Stores tasks that exceeded max retry attempts
-- =============================================================================
CREATE TABLE IF NOT EXISTS dead_letter_queue (
    id INT AUTO_INCREMENT PRIMARY KEY,
    queue_name VARCHAR(255) NOT NULL,
    payload BLOB NOT NULL,
    attempts INT NOT NULL,
    error_message TEXT,
    failed_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- =============================================================================
-- Grant Permissions
-- =============================================================================
-- Ensure the test user has full access to the tables
GRANT ALL PRIVILEGES ON test_db.task_queue TO 'test'@'%';
GRANT ALL PRIVILEGES ON test_db.dead_letter_queue TO 'test'@'%';
FLUSH PRIVILEGES;

-- =============================================================================
-- Verification
-- =============================================================================
-- Output confirmation message
SELECT '✓ Schema initialized successfully!' AS message;
SELECT '  - Created table: task_queue' AS message;
SELECT '  - Created index: idx_task_queue_lookup' AS message;
SELECT '  - Created table: dead_letter_queue' AS message;
SELECT '  - Granted permissions to user: test' AS message;

