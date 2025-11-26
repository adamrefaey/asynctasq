# Configuration

Async Task supports three configuration methods with clear precedence rules.

## Configuration Precedence (highest to lowest)

1. **Keyword arguments** to `set_global_config()` or `Config.from_env()`
2. **Environment variables**
3. **Default values**

---

## Method 1: Environment Variables (Recommended for Production)

**General Configuration:**

```bash
export ASYNC_TASK_DRIVER=redis              # Driver: memory, redis, postgres, mysql, sqs
export ASYNC_TASK_DEFAULT_QUEUE=default     # Default queue name
export ASYNC_TASK_MAX_RETRIES=3             # Default max retry attempts
export ASYNC_TASK_RETRY_DELAY=60            # Default retry delay (seconds)
export ASYNC_TASK_TIMEOUT=300               # Default task timeout (seconds, None = no timeout)
```

**Redis Configuration:**

```bash
export ASYNC_TASK_REDIS_URL=redis://localhost:6379
export ASYNC_TASK_REDIS_PASSWORD=secret
export ASYNC_TASK_REDIS_DB=0
export ASYNC_TASK_REDIS_MAX_CONNECTIONS=10
```

**PostgreSQL Configuration:**

```bash
export ASYNC_TASK_POSTGRES_DSN=postgresql://user:pass@localhost:5432/dbname
export ASYNC_TASK_POSTGRES_QUEUE_TABLE=task_queue
export ASYNC_TASK_POSTGRES_DEAD_LETTER_TABLE=dead_letter_queue
export ASYNC_TASK_POSTGRES_MAX_ATTEMPTS=3
export ASYNC_TASK_POSTGRES_RETRY_DELAY_SECONDS=60
export ASYNC_TASK_POSTGRES_VISIBILITY_TIMEOUT_SECONDS=300
export ASYNC_TASK_POSTGRES_MIN_POOL_SIZE=10
export ASYNC_TASK_POSTGRES_MAX_POOL_SIZE=10
```

**MySQL Configuration:**

```bash
export ASYNC_TASK_MYSQL_DSN=mysql://user:pass@localhost:3306/dbname
export ASYNC_TASK_MYSQL_QUEUE_TABLE=task_queue
export ASYNC_TASK_MYSQL_DEAD_LETTER_TABLE=dead_letter_queue
export ASYNC_TASK_MYSQL_MAX_ATTEMPTS=3
export ASYNC_TASK_MYSQL_RETRY_DELAY_SECONDS=60
export ASYNC_TASK_MYSQL_VISIBILITY_TIMEOUT_SECONDS=300
export ASYNC_TASK_MYSQL_MIN_POOL_SIZE=10
export ASYNC_TASK_MYSQL_MAX_POOL_SIZE=10
```

**AWS SQS Configuration:**

```bash
export ASYNC_TASK_SQS_REGION=us-east-1
export ASYNC_TASK_SQS_QUEUE_PREFIX=https://sqs.us-east-1.amazonaws.com/123456789/
export AWS_ACCESS_KEY_ID=your_access_key
export AWS_SECRET_ACCESS_KEY=your_secret_key
```

---

## Method 2: Programmatic Configuration

**Using `set_global_config()`:**

```python
from async_task.config import set_global_config

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

# SQS configuration
set_global_config(
    driver='sqs',
    sqs_region='us-west-2',
    sqs_queue_url_prefix='https://sqs.us-west-2.amazonaws.com/123456789/',
    aws_access_key_id='your_key',
    aws_secret_access_key='your_secret'
)
```

**Using `Config.from_env()` with Overrides:**

```python
from async_task.config import Config

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
python -m async_task worker \
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
| `driver`              | `ASYNC_TASK_DRIVER`        | `redis`   | Queue driver                   |
| `default_queue`       | `ASYNC_TASK_DEFAULT_QUEUE` | `default` | Default queue name             |
| `default_max_retries` | `ASYNC_TASK_MAX_RETRIES`   | `3`       | Default max retry attempts     |
| `default_retry_delay` | `ASYNC_TASK_RETRY_DELAY`   | `60`      | Default retry delay (seconds)  |
| `default_timeout`     | `ASYNC_TASK_TIMEOUT`       | `None`    | Default task timeout (seconds) |

**Redis Options:**

| Option                  | Env Var                            | Default                  | Description                  |
| ----------------------- | ---------------------------------- | ------------------------ | ---------------------------- |
| `redis_url`             | `ASYNC_TASK_REDIS_URL`             | `redis://localhost:6379` | Redis connection URL         |
| `redis_password`        | `ASYNC_TASK_REDIS_PASSWORD`        | `None`                   | Redis password               |
| `redis_db`              | `ASYNC_TASK_REDIS_DB`              | `0`                      | Redis database number (0-15) |
| `redis_max_connections` | `ASYNC_TASK_REDIS_MAX_CONNECTIONS` | `10`                     | Redis connection pool size   |

**PostgreSQL Options:**

| Option                                | Env Var                                          | Default                                         | Description                  |
| ------------------------------------- | ------------------------------------------------ | ----------------------------------------------- | ---------------------------- |
| `postgres_dsn`                        | `ASYNC_TASK_POSTGRES_DSN`                        | `postgresql://test:test@localhost:5432/test_db` | PostgreSQL connection string |
| `postgres_queue_table`                | `ASYNC_TASK_POSTGRES_QUEUE_TABLE`                | `task_queue`                                    | Queue table name             |
| `postgres_dead_letter_table`          | `ASYNC_TASK_POSTGRES_DEAD_LETTER_TABLE`          | `dead_letter_queue`                             | Dead letter table name       |
| `postgres_max_attempts`               | `ASYNC_TASK_POSTGRES_MAX_ATTEMPTS`               | `3`                                             | Max attempts before DLQ      |
| `postgres_retry_delay_seconds`        | `ASYNC_TASK_POSTGRES_RETRY_DELAY_SECONDS`        | `60`                                            | Retry delay (seconds)        |
| `postgres_visibility_timeout_seconds` | `ASYNC_TASK_POSTGRES_VISIBILITY_TIMEOUT_SECONDS` | `300`                                           | Visibility timeout (seconds) |
| `postgres_min_pool_size`              | `ASYNC_TASK_POSTGRES_MIN_POOL_SIZE`              | `10`                                            | Min connection pool size     |
| `postgres_max_pool_size`              | `ASYNC_TASK_POSTGRES_MAX_POOL_SIZE`              | `10`                                            | Max connection pool size     |

**MySQL Options:**

| Option                             | Env Var                                       | Default                                    | Description                  |
| ---------------------------------- | --------------------------------------------- | ------------------------------------------ | ---------------------------- |
| `mysql_dsn`                        | `ASYNC_TASK_MYSQL_DSN`                        | `mysql://test:test@localhost:3306/test_db` | MySQL connection string      |
| `mysql_queue_table`                | `ASYNC_TASK_MYSQL_QUEUE_TABLE`                | `task_queue`                               | Queue table name             |
| `mysql_dead_letter_table`          | `ASYNC_TASK_MYSQL_DEAD_LETTER_TABLE`          | `dead_letter_queue`                        | Dead letter table name       |
| `mysql_max_attempts`               | `ASYNC_TASK_MYSQL_MAX_ATTEMPTS`               | `3`                                        | Max attempts before DLQ      |
| `mysql_retry_delay_seconds`        | `ASYNC_TASK_MYSQL_RETRY_DELAY_SECONDS`        | `60`                                       | Retry delay (seconds)        |
| `mysql_visibility_timeout_seconds` | `ASYNC_TASK_MYSQL_VISIBILITY_TIMEOUT_SECONDS` | `300`                                      | Visibility timeout (seconds) |
| `mysql_min_pool_size`              | `ASYNC_TASK_MYSQL_MIN_POOL_SIZE`              | `10`                                       | Min connection pool size     |
| `mysql_max_pool_size`              | `ASYNC_TASK_MYSQL_MAX_POOL_SIZE`              | `10`                                       | Max connection pool size     |

**AWS SQS Options:**

| Option                  | Env Var                       | Default     | Description                                          |
| ----------------------- | ----------------------------- | ----------- | ---------------------------------------------------- |
| `sqs_region`            | `ASYNC_TASK_SQS_REGION`       | `us-east-1` | AWS region                                           |
| `sqs_queue_url_prefix`  | `ASYNC_TASK_SQS_QUEUE_PREFIX` | `None`      | SQS queue URL prefix                                 |
| `aws_access_key_id`     | `AWS_ACCESS_KEY_ID`           | `None`      | AWS access key (optional, uses AWS credential chain) |
| `aws_secret_access_key` | `AWS_SECRET_ACCESS_KEY`       | `None`      | AWS secret key (optional, uses AWS credential chain) |
