-- ORM Integration Test Tables for PostgreSQL
--
-- Purpose:
--   Creates test tables for ORM serialization hook integration tests.
--   Supports SQLAlchemy, Django ORM, and Tortoise ORM test fixtures.
--
-- Execution:
--   Automatically run when PostgreSQL container starts via Docker init.
--   Tables are idempotent (safe to re-run).
--
-- Note:
--   Queue tables (task_queue, dead_letter_queue) are created by the
--   'asynctasq migrate' command, not this script. See tests/conftest.py.

-- SQLAlchemy test table
CREATE TABLE IF NOT EXISTS sqlalchemy_test_users (
    id SERIAL PRIMARY KEY,
    username VARCHAR(100) NOT NULL UNIQUE,
    email VARCHAR(255) NOT NULL,
    created_at TIMESTAMPTZ,
    updated_at TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS idx_sqlalchemy_test_users_username ON sqlalchemy_test_users(username);
CREATE INDEX IF NOT EXISTS idx_sqlalchemy_test_users_email ON sqlalchemy_test_users(email);

-- SQLAlchemy test table with composite primary key
CREATE TABLE IF NOT EXISTS sqlalchemy_test_user_sessions (
    user_id INTEGER NOT NULL,
    session_id VARCHAR(100) NOT NULL,
    created_at TIMESTAMPTZ,
    expires_at TIMESTAMPTZ,
    PRIMARY KEY (user_id, session_id)
);

-- Django test table (simulating Django's table naming convention)
CREATE TABLE IF NOT EXISTS django_test_products (
    id SERIAL PRIMARY KEY,
    name VARCHAR(200) NOT NULL,
    price DECIMAL(10, 2) NOT NULL,
    description TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_django_test_products_name ON django_test_products(name);

-- Tortoise ORM test table
CREATE TABLE IF NOT EXISTS tortoise_test_orders (
    id SERIAL PRIMARY KEY,
    order_number VARCHAR(50) NOT NULL UNIQUE,
    customer_name VARCHAR(200) NOT NULL,
    total_amount DECIMAL(10, 2) NOT NULL,
    status VARCHAR(50) NOT NULL DEFAULT 'pending',
    created_at TIMESTAMPTZ,
    updated_at TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS idx_tortoise_test_orders_order_number ON tortoise_test_orders(order_number);
CREATE INDEX IF NOT EXISTS idx_tortoise_test_orders_status ON tortoise_test_orders(status);

-- Grant permissions to test user
GRANT ALL PRIVILEGES ON TABLE sqlalchemy_test_users TO test;
GRANT ALL PRIVILEGES ON TABLE sqlalchemy_test_user_sessions TO test;
GRANT ALL PRIVILEGES ON TABLE django_test_products TO test;
GRANT ALL PRIVILEGES ON TABLE tortoise_test_orders TO test;
GRANT ALL PRIVILEGES ON SEQUENCE sqlalchemy_test_users_id_seq TO test;
GRANT ALL PRIVILEGES ON SEQUENCE django_test_products_id_seq TO test;
GRANT ALL PRIVILEGES ON SEQUENCE tortoise_test_orders_id_seq TO test;
