# Configuration

AsyncTasQ supports three configuration methods with clear precedence rules.

## Configuration Precedence (highest to lowest)

1. **Keyword arguments** to `set_global_config()` or `Config.from_env()`
2. **Environment variables**
3. **Default values**

---

## Method 1: Environment Variables (Recommended for Production)

**General Configuration:**

```bash
export ASYNCTASQ_DRIVER=redis              # Driver: redis, postgres, mysql, rabbitmq, sqs
export ASYNCTASQ_DEFAULT_QUEUE=default     # Default queue name
export ASYNCTASQ_MAX_RETRIES=3             # Default max retry attempts
export ASYNCTASQ_RETRY_DELAY=60            # Default retry delay (seconds)
export ASYNCTASQ_TIMEOUT=300               # Default task timeout (seconds, None = no timeout)
```

**Redis Configuration:**

```bash
export ASYNCTASQ_REDIS_URL=redis://localhost:6379
export ASYNCTASQ_REDIS_PASSWORD=secret
export ASYNCTASQ_REDIS_DB=0
export ASYNCTASQ_REDIS_MAX_CONNECTIONS=10
```

**PostgreSQL Configuration:**

```bash
export ASYNCTASQ_POSTGRES_DSN=postgresql://user:pass@localhost:5432/dbname
export ASYNCTASQ_POSTGRES_QUEUE_TABLE=task_queue
export ASYNCTASQ_POSTGRES_DEAD_LETTER_TABLE=dead_letter_queue
export ASYNCTASQ_POSTGRES_MAX_ATTEMPTS=3
export ASYNCTASQ_POSTGRES_RETRY_DELAY_SECONDS=60
export ASYNCTASQ_POSTGRES_VISIBILITY_TIMEOUT_SECONDS=300
export ASYNCTASQ_POSTGRES_MIN_POOL_SIZE=10
export ASYNCTASQ_POSTGRES_MAX_POOL_SIZE=10
```

**MySQL Configuration:**

```bash
export ASYNCTASQ_MYSQL_DSN=mysql://user:pass@localhost:3306/dbname
export ASYNCTASQ_MYSQL_QUEUE_TABLE=task_queue
export ASYNCTASQ_MYSQL_DEAD_LETTER_TABLE=dead_letter_queue
export ASYNCTASQ_MYSQL_MAX_ATTEMPTS=3
export ASYNCTASQ_MYSQL_RETRY_DELAY_SECONDS=60
export ASYNCTASQ_MYSQL_VISIBILITY_TIMEOUT_SECONDS=300
export ASYNCTASQ_MYSQL_MIN_POOL_SIZE=10
export ASYNCTASQ_MYSQL_MAX_POOL_SIZE=10
```

**RabbitMQ Configuration:**

```bash
export ASYNCTASQ_DRIVER=rabbitmq
export ASYNCTASQ_RABBITMQ_URL=amqp://guest:guest@localhost:5672/
export ASYNCTASQ_RABBITMQ_EXCHANGE_NAME=asynctasq
export ASYNCTASQ_RABBITMQ_PREFETCH_COUNT=1
```

**AWS SQS Configuration:**

```bash
export ASYNCTASQ_SQS_REGION=us-east-1
export ASYNCTASQ_SQS_QUEUE_PREFIX=https://sqs.us-east-1.amazonaws.com/123456789/
export AWS_ACCESS_KEY_ID=your_access_key
export AWS_SECRET_ACCESS_KEY=your_secret_key
```

**Events Configuration (Redis Pub/Sub):**

```bash
export ASYNCTASQ_EVENTS_REDIS_URL=redis://localhost:6379  # Separate Redis for events (optional)
export ASYNCTASQ_EVENTS_CHANNEL=asynctasq:events          # Pub/Sub channel name
```

**Task Retention Configuration:**

```bash
export ASYNCTASQ_KEEP_COMPLETED_TASKS=false  # Keep completed tasks for history (default: false)
```

**Note:** `keep_completed_tasks` is not applicable for SQS driver (SQS always deletes acknowledged messages).

---

## Method 2: Programmatic Configuration

**Using `set_global_config()`:**

```python
from asynctasq.config import set_global_config

# Basic Redis configuration
set_global_config(
    driver='redis',
    redis_url='redis://localhost:6379',
    default_queue='default',
    default_max_retries=3
)

# PostgreSQL with custom settings
set_global_config(
    driver='postgres',
    postgres_dsn='postgresql://user:pass@localhost:5432/mydb',
    postgres_queue_table='my_queue',
    postgres_max_attempts=5,
    postgres_min_pool_size=5,
    postgres_max_pool_size=20
)

# MySQL with custom settings
set_global_config(
    driver='mysql',
    mysql_dsn='mysql://user:pass@localhost:3306/mydb',
    mysql_queue_table='my_queue',
    mysql_max_attempts=5,
    mysql_min_pool_size=5,
    mysql_max_pool_size=20
)

# RabbitMQ configuration
set_global_config(
    driver='rabbitmq',
    rabbitmq_url='amqp://user:pass@localhost:5672/',
    rabbitmq_exchange_name='asynctasq',
    rabbitmq_prefetch_count=1
)

# SQS configuration
set_global_config(
    driver='sqs',
    sqs_region='us-west-2',
    sqs_queue_url_prefix='https://sqs.us-west-2.amazonaws.com/123456789/',
    aws_access_key_id='your_key',
    aws_secret_access_key='your_secret'
)

# Task retention (keep completed tasks for history/audit)
set_global_config(
    keep_completed_tasks=True  # Default: False (tasks are deleted after completion)
)
```

**Using `Config.from_env()` with Overrides:**

```python
from asynctasq.config import Config

# Create config from environment variables with overrides
config = Config.from_env(
    driver='redis',
    redis_url='redis://localhost:6379',
    default_max_retries=5
)
```

---

## Method 3: CLI Arguments

CLI arguments override both environment variables and programmatic configuration:

```bash
python -m asynctasq worker \
    --driver redis \
    --redis-url redis://localhost:6379 \
    --redis-password secret \
    --queues high,default,low \
    --concurrency 20
```

---

## Complete Configuration Reference

**General Options:**

| Option                | Env Var                    | Default   | Description                    |
| --------------------- | -------------------------- | --------- | ------------------------------ |
| `driver`              | `ASYNCTASQ_DRIVER`        | `redis`   | Queue driver                   |
| `default_queue`       | `ASYNCTASQ_DEFAULT_QUEUE` | `default` | Default queue name             |
| `default_max_retries` | `ASYNCTASQ_MAX_RETRIES`   | `3`       | Default max retry attempts     |
| `default_retry_delay` | `ASYNCTASQ_RETRY_DELAY`   | `60`      | Default retry delay (seconds)  |
| `default_timeout`     | `ASYNCTASQ_TIMEOUT`       | `None`    | Default task timeout (seconds) |

**Redis Options:**

| Option                  | Env Var                            | Default                  | Description                  |
| ----------------------- | ---------------------------------- | ------------------------ | ---------------------------- |
| `redis_url`             | `ASYNCTASQ_REDIS_URL`             | `redis://localhost:6379` | Redis connection URL         |
| `redis_password`        | `ASYNCTASQ_REDIS_PASSWORD`        | `None`                   | Redis password               |
| `redis_db`              | `ASYNCTASQ_REDIS_DB`              | `0`                      | Redis database number (0-15) |
| `redis_max_connections` | `ASYNCTASQ_REDIS_MAX_CONNECTIONS` | `10`                     | Redis connection pool size   |

**PostgreSQL Options:**

| Option                                | Env Var                                          | Default                                         | Description                  |
| ------------------------------------- | ------------------------------------------------ | ----------------------------------------------- | ---------------------------- |
| `postgres_dsn`                        | `ASYNCTASQ_POSTGRES_DSN`                        | `postgresql://test:test@localhost:5432/test_db` | PostgreSQL connection string |
| `postgres_queue_table`                | `ASYNCTASQ_POSTGRES_QUEUE_TABLE`                | `task_queue`                                    | Queue table name             |
| `postgres_dead_letter_table`          | `ASYNCTASQ_POSTGRES_DEAD_LETTER_TABLE`          | `dead_letter_queue`                             | Dead letter table name       |
| `postgres_max_attempts`               | `ASYNCTASQ_POSTGRES_MAX_ATTEMPTS`               | `3`                                             | Max attempts before DLQ      |
| `postgres_retry_delay_seconds`        | `ASYNCTASQ_POSTGRES_RETRY_DELAY_SECONDS`        | `60`                                            | Retry delay (seconds)        |
| `postgres_visibility_timeout_seconds` | `ASYNCTASQ_POSTGRES_VISIBILITY_TIMEOUT_SECONDS` | `300`                                           | Visibility timeout (seconds) |
| `postgres_min_pool_size`              | `ASYNCTASQ_POSTGRES_MIN_POOL_SIZE`              | `10`                                            | Min connection pool size     |
| `postgres_max_pool_size`              | `ASYNCTASQ_POSTGRES_MAX_POOL_SIZE`              | `10`                                            | Max connection pool size     |

**MySQL Options:**

| Option                             | Env Var                                       | Default                                    | Description                  |
| ---------------------------------- | --------------------------------------------- | ------------------------------------------ | ---------------------------- |
| `mysql_dsn`                        | `ASYNCTASQ_MYSQL_DSN`                        | `mysql://test:test@localhost:3306/test_db` | MySQL connection string      |
| `mysql_queue_table`                | `ASYNCTASQ_MYSQL_QUEUE_TABLE`                | `task_queue`                               | Queue table name             |
| `mysql_dead_letter_table`          | `ASYNCTASQ_MYSQL_DEAD_LETTER_TABLE`          | `dead_letter_queue`                        | Dead letter table name       |
| `mysql_max_attempts`               | `ASYNCTASQ_MYSQL_MAX_ATTEMPTS`               | `3`                                        | Max attempts before DLQ      |
| `mysql_retry_delay_seconds`        | `ASYNCTASQ_MYSQL_RETRY_DELAY_SECONDS`        | `60`                                       | Retry delay (seconds)        |
| `mysql_visibility_timeout_seconds` | `ASYNCTASQ_MYSQL_VISIBILITY_TIMEOUT_SECONDS` | `300`                                      | Visibility timeout (seconds) |
| `mysql_min_pool_size`              | `ASYNCTASQ_MYSQL_MIN_POOL_SIZE`              | `10`                                       | Min connection pool size     |
| `mysql_max_pool_size`              | `ASYNCTASQ_MYSQL_MAX_POOL_SIZE`              | `10`                                       | Max connection pool size     |

**RabbitMQ Options:**

| Option                    | Env Var                              | Default                              | Description                      |
| ------------------------- | ------------------------------------ | ------------------------------------ | -------------------------------- |
| `rabbitmq_url`            | `ASYNCTASQ_RABBITMQ_URL`            | `amqp://guest:guest@localhost:5672/` | RabbitMQ connection URL          |
| `rabbitmq_exchange_name`  | `ASYNCTASQ_RABBITMQ_EXCHANGE_NAME`  | `asynctasq`                         | RabbitMQ exchange name           |
| `rabbitmq_prefetch_count` | `ASYNCTASQ_RABBITMQ_PREFETCH_COUNT` | `1`                                  | RabbitMQ consumer prefetch count |

**AWS SQS Options:**

| Option                  | Env Var                       | Default     | Description                                          |
| ----------------------- | ----------------------------- | ----------- | ---------------------------------------------------- |
| `sqs_region`            | `ASYNCTASQ_SQS_REGION`       | `us-east-1` | AWS region                                           |
| `sqs_queue_url_prefix`  | `ASYNCTASQ_SQS_QUEUE_PREFIX` | `None`      | SQS queue URL prefix                                 |
| `aws_access_key_id`     | `AWS_ACCESS_KEY_ID`           | `None`      | AWS access key (optional, uses AWS credential chain) |
| `aws_secret_access_key` | `AWS_SECRET_ACCESS_KEY`       | `None`      | AWS secret key (optional, uses AWS credential chain) |

**Events Options (Redis Pub/Sub):**

| Option              | Env Var                         | Default            | Description                                       |
| ------------------- | ------------------------------- | ------------------ | ------------------------------------------------- |
| `events_redis_url`  | `ASYNCTASQ_EVENTS_REDIS_URL`   | `None`             | Dedicated Redis URL for events (falls back to redis_url) |
| `events_channel`    | `ASYNCTASQ_EVENTS_CHANNEL`     | `asynctasq:events` | Pub/Sub channel name for task events              |

**Task Retention Options:**

| Option                  | Env Var                              | Default | Description                                                                 |
| ----------------------- | ------------------------------------ | ------- | --------------------------------------------------------------------------- |
| `keep_completed_tasks`  | `ASYNCTASQ_KEEP_COMPLETED_TASKS`    | `False` | Keep completed tasks for history/audit (not applicable for SQS driver)      |

**Note:** When `keep_completed_tasks=True`:
- **Redis**: Completed tasks stored in `queue:{name}:completed` list
- **PostgreSQL**: Completed tasks marked with `status='completed'` in queue table
- **MySQL**: Completed tasks marked with `status='completed'` in queue table
- **RabbitMQ**: Completed tasks published to `{queue_name}_completed` queue
- **SQS**: Not supported (SQS always deletes acknowledged messages)

