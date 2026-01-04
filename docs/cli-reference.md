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

**For comprehensive worker deployment guides, production patterns, and best practices, see [Running Workers](running-workers.md).**

**Recommended Approach:**

Use a `.env` file for configuration (production best practice):

```bash
# .env file
ASYNCTASQ_DRIVER=redis
ASYNCTASQ_REDIS_URL=redis://localhost:6379

# Then run worker with clean command signature
uv run asynctasq worker --queues default
```

For complete `.env` file setup and examples, see [Environment Variables Guide](environment-variables.md).

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
| `--task-defaults-visibility-timeout N`    | Visibility timeout for crash recovery (seconds). See [Configuration - Visibility Timeout Warning](../configuration.md#visibility-timeout-warning) | `3600` (1 hour) |
| `--process-pool-size N`                   | Number of worker processes for CPU-bound tasks   | (auto-detect CPU count)              |
| `--process-pool-max-tasks-per-child N`    | Recycle worker processes after N tasks           | -                                    |
| `--repository-keep-completed-tasks`       | Keep completed tasks for history/audit           | `False`                              |

**Examples:**

```bash
# ============================================
# RECOMMENDED: Use .env file for configuration
# ============================================

# Create .env file with your configuration:
# ASYNCTASQ_DRIVER=redis
# ASYNCTASQ_REDIS_URL=redis://localhost:6379

# Basic usage - configuration loaded from .env
uv run asynctasq worker --queues default

# Multiple queues with priority
uv run asynctasq worker --queues high,default,low --concurrency 20

# With worker-specific options
uv run asynctasq worker \
    --queues default,emails \
    --concurrency 10 \
    --process-pool-size 4

# ============================================
# REFERENCE: Inline CLI configuration (testing only)
# ============================================
# Note: Production deployments should use .env files

# Redis with auth
asynctasq worker \
    --driver redis \
    --redis-url redis://localhost:6379 \
    --redis-password secret \
    --queues default

# PostgreSQL worker
asynctasq worker \
    --driver postgres \
    --postgres-dsn postgresql://user:pass@localhost/db \
    --queues default

# MySQL worker
asynctasq worker \
    --driver mysql \
    --mysql-dsn mysql://user:pass@localhost:3306/db \
    --queues default

# RabbitMQ worker
asynctasq worker \
    --driver rabbitmq \
    --rabbitmq-url amqp://user:pass@localhost:5672/ \
    --queues default

# SQS worker
asynctasq worker \
    --driver sqs \
    --sqs-region us-west-2 \
    --sqs-queue-url-prefix https://sqs.us-west-2.amazonaws.com/123456789/ \
    --queues default
```

**Additional Usage Examples:**

```bash
# ============================================
# Production patterns (use .env for configuration)
# ============================================

# Single queue worker (email processing)
# Configure ASYNCTASQ_DRIVER and connection details in .env
uv run asynctasq worker --queues emails --concurrency 5

# High-throughput worker (multiple queues with priority)
uv run asynctasq worker \
    --queues critical,high,default,low \
    --concurrency 100 \
    --process-pool-size 16

# Worker for CPU-intensive tasks only
uv run asynctasq worker \
    --queues cpu_intensive \
    --concurrency 4 \
    --process-pool-size 4

# Development with hot-reload (using entr)
# Install: pip install watchdog
echo "src/**/*.py" | entr -r asynctasq worker --queues dev --concurrency 1

# ============================================
# Container deployments (use env vars)
# ============================================

# Docker container worker
asynctasq worker \
    --queues "${QUEUE_NAMES}" \
    --concurrency "${CONCURRENCY:-10}"

# Multi-tenant worker
asynctasq worker \
    --queues tenant_1,tenant_2,tenant_3 \
    --concurrency 30
```
```

**Common Patterns:**

| Use Case                        | Key Options                                                          | Example                                                           |
| ------------------------------- | -------------------------------------------------------------------- | ----------------------------------------------------------------- |
| **High Priority Processing**    | `--queues high,default` with high concurrency                        | Process urgent tasks first, fall back to default                  |
| **CPU-Heavy Workloads**         | `--process-pool-size` matching CPU cores                             | Image processing, data analysis, ML inference                     |
| **I/O-Heavy Workloads**         | High `--concurrency`, moderate `--process-pool-size`                 | API calls, database queries, file operations                      |
| **Mixed Workloads**             | Balanced concurrency and process pool                                | Combination of I/O and CPU tasks                                  |
| **Multi-Region Deployment**     | Separate workers per region with different queue names               | `us-east-worker` processes `us_east_*` queues                     |
| **Gradual Rollout**             | Start with low concurrency, increase gradually                       | Test new task versions with limited concurrency                   |
| **Cost Optimization**           | Lower concurrency during off-peak hours                              | Scale down workers at night                                       |

**Troubleshooting Commands:**

```bash
# Test worker connectivity (load config from .env)
uv run asynctasq worker --queues test &
sleep 2
kill %1  # If no errors, connection works

# Debug mode with verbose logging
LOG_LEVEL=DEBUG uv run asynctasq worker --queues default --concurrency 1

# Minimal worker (for debugging)
uv run asynctasq worker --queues default --concurrency 1
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

# Production migration with connection pooling
asynctasq migrate \
    --driver postgres \
    --postgres-dsn postgresql://user:pass@localhost/db \
    --postgres-min-pool-size 20 \
    --postgres-max-pool-size 50 \
    --postgres-queue-table production_queue \
    --postgres-dead-letter-table production_dlq \
    --postgres-max-attempts 5

# Development migration with Docker
asynctasq migrate \
    --driver postgres \
    --postgres-dsn postgresql://postgres:postgres@localhost:5432/asynctasq_dev

# MySQL migration for existing database
asynctasq migrate \
    --driver mysql \
    --mysql-dsn mysql://app_user:secret@localhost:3306/app_db \
    --mysql-queue-table async_tasks \
    --mysql-dead-letter-table async_tasks_failed

# CI/CD migration (using environment variables)
asynctasq migrate \
    --driver postgres \
    --postgres-dsn "${DATABASE_URL}"

# Migration with SSL connection
asynctasq migrate \
    --driver postgres \
    --postgres-dsn "postgresql://user:pass@localhost/db?sslmode=require"

# Multi-environment setup
# Development
asynctasq migrate --postgres-dsn postgresql://localhost/asynctasq_dev
# Staging
asynctasq migrate --postgres-dsn postgresql://localhost/asynctasq_staging
# Production
asynctasq migrate --postgres-dsn "${PRODUCTION_DB_URL}"

# Verify migration was successful (check tables exist)
asynctasq migrate --postgres-dsn postgresql://user:pass@localhost/db
psql postgresql://user:pass@localhost/db -c "\dt task_queue"
psql postgresql://user:pass@localhost/db -c "\dt dead_letter_queue"
```

**Best Practices:**

- ✅ **Run in CI/CD pipeline** - Ensure schema is up-to-date on deployment
- ✅ **Separate credentials** - Use service account with CREATE TABLE permissions
- ✅ **Test first** - Run migration on staging before production
- ✅ **Idempotent by design** - Safe to run multiple times
- ✅ **Version control** - Track migration runs in deployment logs

**Common Migration Issues:**

| Issue                    | Symptom                                  | Solution                                        |
| ------------------------ | ---------------------------------------- | ----------------------------------------------- |
| Permission denied        | `permission denied for schema public`    | Grant CREATE privilege to database user         |
| Connection refused       | `could not connect to server`            | Verify DSN, check firewall, test with psql/mysql |
| Table already exists     | No error (migration is idempotent)       | Expected behavior, safe to ignore               |
| SSL required             | `SSL connection required`                | Add `?sslmode=require` to DSN                   |
| Invalid DSN format       | `invalid DSN`                            | Check DSN format: `driver://user:pass@host/db`  |

**What it does:**

- Creates queue table with optimized indexes
- Creates dead-letter table for failed tasks
- Idempotent (safe to run multiple times)
- Only works with PostgreSQL and MySQL drivers
- Sets up proper indexes for queue polling performance

**Schema Details:**

The migration creates two tables:
- **Queue Table** - Stores pending and in-progress tasks
- **Dead Letter Queue** - Stores permanently failed tasks for analysis

Both tables include:
- Optimized indexes for queue polling
- Timestamp columns for tracking
- JSON payload column for task data
- Retry attempt tracking

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

# Initial project setup
mkdir my-project && cd my-project
asynctasq publish
cp .env.example .env
# Edit .env with your configuration

# Team onboarding (publish and commit template)
asynctasq publish --output-dir .
git add .env.example
git commit -m "Add AsyncTasQ configuration template"
# Team members can now: cp .env.example .env

# Update existing template (overwrite)
asynctasq publish --force

# Docker project setup
asynctasq publish --output-dir ./config
# Then mount in Dockerfile: COPY config/.env.example /app/.env.example

# Multi-environment setup
asynctasq publish --output-dir .
cp .env.example .env.dev
cp .env.example .env.staging
cp .env.example .env.prod
# Customize each environment file

# Monorepo setup
asynctasq publish --output-dir ./services/background-worker
asynctasq publish --output-dir ./services/api-server

# Continuous Integration (CI) setup
asynctasq publish --output-dir .
# Use .env.example as base for CI environment variables

# Publish to specific deployment directory
asynctasq publish --output-dir /opt/myapp/config

# Create backup before overwriting
cp .env.example .env.example.backup
asynctasq publish --force
```

**Integration Examples:**

**With Docker:**
```dockerfile
# Dockerfile
FROM python:3.11
WORKDIR /app

# Publish .env.example during build
RUN pip install asynctasq
RUN asynctasq publish --output-dir /app

# Copy and use .env.example as template
COPY .env.prod .env
CMD ["asynctasq", "worker"]
```

**With Docker Compose:**
```yaml
# docker-compose.yml
version: '3.8'
services:
  worker:
    build: .
    volumes:
      - ./.env.example:/app/.env.example:ro
    environment:
      - ASYNCTASQ_DRIVER=redis
      - ASYNCTASQ_REDIS_URL=redis://redis:6379
```

**With CI/CD Pipeline:**
```bash
# .github/workflows/deploy.yml
- name: Setup AsyncTasQ config
  run: |
    asynctasq publish
    cp .env.example .env.ci
    # Inject secrets from GitHub Actions
    echo "ASYNCTASQ_REDIS_PASSWORD=${{ secrets.REDIS_PASSWORD }}" >> .env.ci
```

**Best Practices:**

- ✅ **Commit `.env.example` to git** - Share configuration template with team
- ✅ **Never commit `.env`** - Add to `.gitignore` to protect secrets
- ✅ **Document changes** - Update `.env.example` when adding new config
- ✅ **Use in onboarding** - New team members copy `.env.example` to `.env`
- ✅ **Validate configuration** - Check required variables are set before running worker

**Workflow:**

1. **Initial Setup**: Run `asynctasq publish` to create template
2. **Customize**: Copy to `.env` and set your values
3. **Secure**: Add `.env` to `.gitignore`
4. **Share**: Commit `.env.example` for team
5. **Maintain**: Update template when config changes

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
