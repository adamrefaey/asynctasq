-- MySQL 8.0+ Migration script to create tables for ORM integration tests
-- This script creates test tables for SQLAlchemy, Django, and Tortoise ORM models
-- Run automatically during Docker container initialization
--
-- Requirements:
--   - MySQL 8.0+ (for DATETIME(6) microsecond precision)
--   - InnoDB storage engine (default in MySQL 8.0)
--   - utf8mb4 charset (for full Unicode support)

-- SQLAlchemy test table
CREATE TABLE IF NOT EXISTS sqlalchemy_test_users (
    id INT AUTO_INCREMENT PRIMARY KEY,
    username VARCHAR(100) NOT NULL UNIQUE,
    email VARCHAR(255) NOT NULL,
    created_at DATETIME(6) NULL,
    updated_at DATETIME(6) NULL,
    INDEX idx_sqlalchemy_test_users_username (username),
    INDEX idx_sqlalchemy_test_users_email (email)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- SQLAlchemy test table with composite primary key
CREATE TABLE IF NOT EXISTS sqlalchemy_test_user_sessions (
    user_id INT NOT NULL,
    session_id VARCHAR(100) NOT NULL,
    created_at DATETIME(6) NULL,
    expires_at DATETIME(6) NULL,
    PRIMARY KEY (user_id, session_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Django test table (simulating Django's table naming convention)
CREATE TABLE IF NOT EXISTS django_test_products (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(200) NOT NULL,
    price DECIMAL(10, 2) NOT NULL,
    description TEXT,
    created_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
    updated_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6) ON UPDATE CURRENT_TIMESTAMP(6),
    INDEX idx_django_test_products_name (name)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Tortoise ORM test table
CREATE TABLE IF NOT EXISTS tortoise_test_orders (
    id INT AUTO_INCREMENT PRIMARY KEY,
    order_number VARCHAR(50) NOT NULL UNIQUE,
    customer_name VARCHAR(200) NOT NULL,
    total_amount DECIMAL(10, 2) NOT NULL,
    status VARCHAR(50) NOT NULL DEFAULT 'pending',
    created_at DATETIME(6) NULL,
    updated_at DATETIME(6) NULL,
    INDEX idx_tortoise_test_orders_order_number (order_number),
    INDEX idx_tortoise_test_orders_status (status)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Grant permissions to test user
GRANT ALL PRIVILEGES ON test_db.sqlalchemy_test_users TO 'test'@'%';
GRANT ALL PRIVILEGES ON test_db.sqlalchemy_test_user_sessions TO 'test'@'%';
GRANT ALL PRIVILEGES ON test_db.django_test_products TO 'test'@'%';
GRANT ALL PRIVILEGES ON test_db.tortoise_test_orders TO 'test'@'%';
FLUSH PRIVILEGES;

