# CLI Reference

## Worker Command

Start a worker to process tasks from queues.

```bash
# Using Python module
python -m asynctasq worker [OPTIONS]

# Or using installed command (after package installation)
asynctasq worker [OPTIONS]

# Or with uv
uv run asynctasq worker [OPTIONS]
```

**Options:**

| Option                          | Description                                  | Default                  |
| ------------------------------- | -------------------------------------------- | ------------------------ |
| `--driver DRIVER`               | Queue driver (redis/postgres/mysql/rabbitmq/sqs) | `redis`                  |
| `--queues QUEUES`               | Comma-separated queue names (priority order) | `default`                |
| `--concurrency N`               | Max concurrent tasks                         | `10`                     |
| `--redis-url URL`               | Redis connection URL                         | `redis://localhost:6379` |
| `--redis-password PASSWORD`     | Redis password                               | `None`                   |
| `--redis-db N`                  | Redis database number (0-15)                 | `0`                      |
| `--redis-max-connections N`     | Redis connection pool size                   | `100`                     |
| `--postgres-dsn DSN`            | PostgreSQL connection DSN                    | -                        |
| `--postgres-queue-table TABLE`  | PostgreSQL queue table name                  | `task_queue`             |
| `--postgres-dead-letter-table TABLE` | PostgreSQL dead letter table name       | `dead_letter_queue`      |
| `--mysql-dsn DSN`               | MySQL connection DSN                         | -                        |
| `--mysql-queue-table TABLE`     | MySQL queue table name                       | `task_queue`             |
| `--mysql-dead-letter-table TABLE` | MySQL dead letter table name               | `dead_letter_queue`      |
| `--sqs-region REGION`           | AWS SQS region                               | `us-east-1`              |
| `--sqs-queue-url-prefix PREFIX` | SQS queue URL prefix                         | -                        |
| `--aws-access-key-id KEY`       | AWS access key (optional)                    | -                        |
| `--aws-secret-access-key KEY`   | AWS secret key (optional)                    | -                        |

**Examples:**

```bash
# Basic usage
python -m asynctasq worker
# or
asynctasq worker

# Multiple queues with priority
asynctasq worker --queues high,default,low --concurrency 20

# Redis with auth
asynctasq worker \
    --driver redis \
    --redis-url redis://localhost:6379 \
    --redis-password secret

# PostgreSQL worker
asynctasq worker \
    --driver postgres \
    --postgres-dsn postgresql://user:pass@localhost/db

# MySQL worker
asynctasq worker \
    --driver mysql \
    --mysql-dsn mysql://user:pass@localhost:3306/db

# SQS worker
asynctasq worker \
    --driver sqs \
    --sqs-region us-west-2

# RabbitMQ worker
asynctasq worker \
    --driver rabbitmq \
    --queues default,emails \
    --concurrency 5

# With uv
uv run asynctasq worker --queues default --concurrency 10
```

---

## Migrate Command

Initialize database schema for PostgreSQL or MySQL drivers.

```bash
# Using Python module
python -m asynctasq migrate [OPTIONS]

# Or using installed command
asynctasq migrate [OPTIONS]

# Or with uv
uv run asynctasq migrate [OPTIONS]
```

**Options:**

| Option                               | Description                | Default             |
| ------------------------------------ | -------------------------- | ------------------- |
| `--driver DRIVER`                    | Driver (postgres or mysql) | `postgres`          |
| `--postgres-dsn DSN`                 | PostgreSQL connection DSN  | -                   |
| `--postgres-queue-table TABLE`       | Queue table name           | `task_queue`        |
| `--postgres-dead-letter-table TABLE` | Dead letter table name     | `dead_letter_queue` |
| `--mysql-dsn DSN`                    | MySQL connection DSN       | -                   |
| `--mysql-queue-table TABLE`          | Queue table name           | `task_queue`        |
| `--mysql-dead-letter-table TABLE`    | Dead letter table name     | `dead_letter_queue` |

**Examples:**

```bash
# PostgreSQL migration (default)
asynctasq migrate \
    --postgres-dsn postgresql://user:pass@localhost/db

# PostgreSQL with custom tables
asynctasq migrate \
    --postgres-dsn postgresql://user:pass@localhost/db \
    --postgres-queue-table my_queue \
    --postgres-dead-letter-table my_dlq

# MySQL migration
asynctasq migrate \
    --driver mysql \
    --mysql-dsn mysql://user:pass@localhost:3306/db

# With uv
uv run asynctasq migrate --driver postgres --postgres-dsn postgresql://user:pass@localhost/db
```

**What it does:**

- Creates queue table with optimized indexes
- Creates dead-letter table for failed tasks
- Idempotent (safe to run multiple times)
- Only works with PostgreSQL and MySQL drivers
