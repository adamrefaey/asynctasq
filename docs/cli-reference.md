# CLI Reference

## Table of Contents

- [CLI Reference](#cli-reference)
  - [Table of Contents](#table-of-contents)
  - [Worker Command](#worker-command)
  - [Migrate Command](#migrate-command)
  - [Publish Command](#publish-command)

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

| Option                                    | Description                                      | Default                              |
| ----------------------------------------- | ------------------------------------------------ | ------------------------------------ |
| `--driver DRIVER`                         | Queue driver (redis/postgres/mysql/rabbitmq/sqs) | `redis`                              |
| `--queues QUEUES`                         | Comma-separated queue names (priority order)     | `default`                            |
| `--concurrency N`                         | Max concurrent tasks                             | `10`                                 |
| `--redis-url URL`                         | Redis connection URL                             | `redis://localhost:6379`             |
| `--redis-password PASSWORD`               | Redis password                                   | `None`                               |
| `--redis-db N`                            | Redis database number (0-15)                     | `0`                                  |
| `--redis-max-connections N`               | Redis connection pool size                       | `100`                                |
| `--postgres-dsn DSN`                      | PostgreSQL connection DSN                        | -                                    |
| `--postgres-queue-table TABLE`            | PostgreSQL queue table name                      | `task_queue`                         |
| `--postgres-dead-letter-table TABLE`      | PostgreSQL dead letter table name                | `dead_letter_queue`                  |
| `--postgres-max-attempts N`               | PostgreSQL max attempts before dead-lettering    | `3`                                  |
| `--postgres-min-pool-size N`              | PostgreSQL minimum connection pool size          | `10`                                 |
| `--postgres-max-pool-size N`              | PostgreSQL maximum connection pool size          | `10`                                 |
| `--mysql-dsn DSN`                         | MySQL connection DSN                             | -                                    |
| `--mysql-queue-table TABLE`               | MySQL queue table name                           | `task_queue`                         |
| `--mysql-dead-letter-table TABLE`         | MySQL dead letter table name                     | `dead_letter_queue`                  |
| `--mysql-max-attempts N`                  | MySQL max attempts before dead-lettering         | `3`                                  |
| `--mysql-min-pool-size N`                 | MySQL minimum connection pool size               | `10`                                 |
| `--mysql-max-pool-size N`                 | MySQL maximum connection pool size               | `10`                                 |
| `--sqs-region REGION`                     | AWS SQS region                                   | `us-east-1`                          |
| `--sqs-queue-url-prefix PREFIX`           | SQS queue URL prefix                             | -                                    |
| `--sqs-endpoint-url URL`                  | SQS endpoint URL (for LocalStack)                | -                                    |
| `--aws-access-key-id KEY`                 | AWS access key (optional)                        | -                                    |
| `--aws-secret-access-key KEY`             | AWS secret key (optional)                        | -                                    |
| `--rabbitmq-url URL`                      | RabbitMQ connection URL                          | `amqp://guest:guest@localhost:5672/` |
| `--rabbitmq-exchange-name NAME`           | RabbitMQ exchange name                           | `asynctasq`                          |
| `--rabbitmq-prefetch-count N`             | RabbitMQ consumer prefetch count                 | `1`                                  |
| `--events-redis-url URL`                  | Redis URL for event pub/sub                      | (uses main redis.url)                |
| `--events-channel CHANNEL`                | Redis Pub/Sub channel name for events            | `asynctasq:events`                   |
| `--events-enable-event-emitter-redis`     | Enable Redis Pub/Sub event emitter               | `False`                              |
| `--task-defaults-queue QUEUE`             | Default queue name for tasks                     | `default`                            |
| `--task-defaults-max-attempts N`          | Default maximum retry attempts                   | `3`                                  |
| `--task-defaults-retry-strategy STRATEGY` | Retry delay strategy (fixed/exponential)         | `exponential`                        |
| `--task-defaults-retry-delay N`           | Base retry delay in seconds                      | `60`                                 |
| `--task-defaults-timeout N`               | Default task timeout in seconds                  | -                                    |
| `--task-defaults-visibility-timeout N`    | **⚠️ CRITICAL:** Visibility timeout for crash recovery (seconds) - Must exceed task execution time | `3600` (1 hour) |
| `--process-pool-size N`                   | Number of worker processes for CPU-bound tasks   | (auto-detect CPU count)              |
| `--process-pool-max-tasks-per-child N`    | Recycle worker processes after N tasks           | -                                    |
| `--repository-keep-completed-tasks`       | Keep completed tasks for history/audit           | `False`                              |

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
    --rabbitmq-url amqp://user:pass@localhost:5672/ \
    --rabbitmq-exchange-name my_exchange \
    --rabbitmq-prefetch-count 5 \
    --queues default,emails \
    --concurrency 5

# With events enabled (Redis Pub/Sub)
asynctasq worker \
    --driver redis \
    --events-enable-event-emitter-redis \
    --events-redis-url redis://localhost:6379 \
    --events-channel my_events_channel

# With custom task defaults
asynctasq worker \
    --task-defaults-queue high_priority \
    --task-defaults-max-attempts 5 \
    --task-defaults-retry-strategy exponential \
    --task-defaults-retry-delay 120 \
    --task-defaults-timeout 300 \
    --task-defaults-visibility-timeout 600

# With process pool for CPU-bound tasks
asynctasq worker \
    --process-pool-size 8 \
    --process-pool-max-tasks-per-child 1000 \
    --concurrency 20

# Keep completed tasks for audit trail
asynctasq worker \
    --driver postgres \
    --postgres-dsn postgresql://user:pass@localhost/db \
    --repository-keep-completed-tasks

# LocalStack SQS (testing)
asynctasq worker \
    --driver sqs \
    --sqs-endpoint-url http://localhost:4566 \
    --sqs-queue-url-prefix http://localhost:4566/000000000000/ \
    --aws-access-key-id test \
    --aws-secret-access-key test

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

| Option                               | Description                        | Default             |
| ------------------------------------ | ---------------------------------- | ------------------- |
| `--driver DRIVER`                    | Driver (postgres or mysql)         | `postgres`          |
| `--postgres-dsn DSN`                 | PostgreSQL connection DSN          | -                   |
| `--postgres-queue-table TABLE`       | Queue table name                   | `task_queue`        |
| `--postgres-dead-letter-table TABLE` | Dead letter table name             | `dead_letter_queue` |
| `--postgres-max-attempts N`          | Max attempts before dead-lettering | `3`                 |
| `--postgres-min-pool-size N`         | Minimum connection pool size       | `10`                |
| `--postgres-max-pool-size N`         | Maximum connection pool size       | `10`                |
| `--mysql-dsn DSN`                    | MySQL connection DSN               | -                   |
| `--mysql-queue-table TABLE`          | Queue table name                   | `task_queue`        |
| `--mysql-dead-letter-table TABLE`    | Dead letter table name             | `dead_letter_queue` |
| `--mysql-max-attempts N`             | Max attempts before dead-lettering | `3`                 |
| `--mysql-min-pool-size N`            | Minimum connection pool size       | `10`                |
| `--mysql-max-pool-size N`            | Maximum connection pool size       | `10`                |

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

---

## Publish Command

Publish the `.env.example` configuration file to your project root. This command copies the comprehensive environment variables template from AsyncTasQ to your project, making it easy to configure the library.

```bash
# Using Python module
python -m asynctasq publish [OPTIONS]

# Or using installed command
asynctasq publish [OPTIONS]

# Or with uv
uv run asynctasq publish [OPTIONS]
```

**Options:**

| Option               | Description                                   | Default             |
| -------------------- | --------------------------------------------- | ------------------- |
| `--output-dir DIR`   | Output directory for .env.example file        | Current directory   |
| `--force`            | Overwrite existing .env.example file          | `False`             |

**Examples:**

```bash
# Publish to current directory
asynctasq publish

# Publish to a specific directory
asynctasq publish --output-dir /path/to/project

# Overwrite existing .env.example file
asynctasq publish --force

# Publish to project and create .env from it
asynctasq publish --output-dir ~/my-project
cp ~/my-project/.env.example ~/my-project/.env
# Edit .env with your actual configuration values

# With uv
uv run asynctasq publish --output-dir .
```

**What it does:**

- Copies the `.env.example` file from AsyncTasQ package to your project
- Provides a complete template with all available environment variables
- Includes documentation and examples for each configuration option
- Safe by default - won't overwrite existing files unless `--force` is used

**Next Steps After Publishing:**

1. Copy `.env.example` to `.env` in your project root
2. Update the values in `.env` with your actual configuration
3. Add `.env` to your `.gitignore` to keep secrets safe
4. Use `.env.example` as a template for team members

**Why Use This Command:**

- **Quick Setup**: Get started with configuration in seconds
- **Complete Reference**: All environment variables documented in one place
- **Best Practices**: Examples show recommended configurations
- **Team Collaboration**: Share `.env.example` with your team via git
- **Multiple Environments**: Easy to create `.env.dev`, `.env.prod`, etc.
