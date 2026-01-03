# Test Infrastructure

Docker-based test infrastructure for asynctasq integration tests.

## Services

- **PostgreSQL** (port 5432) - Database driver and ORM integration tests
- **MySQL** (port 3306) - Database driver and ORM integration tests
- **Redis** (port 6379) - Redis driver integration tests
- **RabbitMQ** (port 5672, management 15672) - RabbitMQ driver integration tests
- **LocalStack** (port 4566) - AWS SQS driver integration tests

## Quick Start

```bash
# Start all services and run migrations
just docker-up

# Stop all services
just docker-down

# Restart services
just docker-restart
```

## Schema Initialization

### Queue Tables (task_queue, dead_letter_queue)
Created automatically by the `asynctasq migrate` command:
- Runs automatically via `just docker-up`
- Also runs automatically before tests via `tests/conftest.py`
- Idempotent and safe to re-run

### ORM Test Tables
Created automatically during Docker container initialization:
- **PostgreSQL**: `postgres-init/orm-tables.sql`
- **MySQL**: `mysql-init/orm-tables.sql`

Test tables include:
- `sqlalchemy_test_users` - SQLAlchemy ORM tests
- `sqlalchemy_test_user_sessions` - SQLAlchemy composite PK tests
- `django_test_products` - Django ORM tests
- `tortoise_test_orders` - Tortoise ORM tests

## Directory Structure

```
infrastructure/
├── docker-compose.yml          # Service definitions
├── postgres-init/
│   └── orm-tables.sql         # PostgreSQL ORM test tables
├── mysql-init/
│   └── orm-tables.sql         # MySQL ORM test tables
├── localstack-init/
│   └── ready.d/               # LocalStack initialization scripts
└── rabbitmq.conf              # RabbitMQ configuration
```

## Notes

- Queue tables use the official migration tool (single source of truth)
- ORM tables are test-specific fixtures (not part of asynctasq)
- All initialization is automated - no manual setup required
- Containers persist data between restarts for faster iteration
- Use `docker-compose down -v` to completely reset (remove volumes)
