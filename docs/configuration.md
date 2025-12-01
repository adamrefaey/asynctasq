# Configuration

Q Task supports three configuration methods with clear precedence rules.

## Configuration Precedence (highest to lowest)

1. **Keyword arguments** to `set_global_config()` or `Config.from_env()`
2. **Environment variables**
3. **Default values**

---

## Method 1: Environment Variables (Recommended for Production)

**General Configuration:**

```bash
export q_task_DRIVER=redis              # Driver: redis, postgres, mysql, rabbitmq, sqs
export q_task_DEFAULT_QUEUE=default     # Default queue name
export q_task_MAX_RETRIES=3             # Default max retry attempts
export q_task_RETRY_DELAY=60            # Default retry delay (seconds)
export q_task_TIMEOUT=300               # Default task timeout (seconds, None = no timeout)
```

**Redis Configuration:**

```bash
export q_task_REDIS_URL=redis://localhost:6379
export q_task_REDIS_PASSWORD=secret
export q_task_REDIS_DB=0
export q_task_REDIS_MAX_CONNECTIONS=10
```

**PostgreSQL Configuration:**

```bash
export q_task_POSTGRES_DSN=postgresql://user:pass@localhost:5432/dbname
export q_task_POSTGRES_QUEUE_TABLE=task_queue
export q_task_POSTGRES_DEAD_LETTER_TABLE=dead_letter_queue
export q_task_POSTGRES_MAX_ATTEMPTS=3
export q_task_POSTGRES_RETRY_DELAY_SECONDS=60
export q_task_POSTGRES_VISIBILITY_TIMEOUT_SECONDS=300
export q_task_POSTGRES_MIN_POOL_SIZE=10
export q_task_POSTGRES_MAX_POOL_SIZE=10
```

**MySQL Configuration:**

```bash
export q_task_MYSQL_DSN=mysql://user:pass@localhost:3306/dbname
export q_task_MYSQL_QUEUE_TABLE=task_queue
export q_task_MYSQL_DEAD_LETTER_TABLE=dead_letter_queue
export q_task_MYSQL_MAX_ATTEMPTS=3
export q_task_MYSQL_RETRY_DELAY_SECONDS=60
export q_task_MYSQL_VISIBILITY_TIMEOUT_SECONDS=300
export q_task_MYSQL_MIN_POOL_SIZE=10
export q_task_MYSQL_MAX_POOL_SIZE=10
```

**RabbitMQ Configuration:**

```bash
export q_task_DRIVER=rabbitmq
export q_task_RABBITMQ_URL=amqp://guest:guest@localhost:5672/
export q_task_RABBITMQ_EXCHANGE_NAME=q_task
export q_task_RABBITMQ_PREFETCH_COUNT=1
```

**AWS SQS Configuration:**

```bash
export q_task_SQS_REGION=us-east-1
export q_task_SQS_QUEUE_PREFIX=https://sqs.us-east-1.amazonaws.com/123456789/
export AWS_ACCESS_KEY_ID=your_access_key
export AWS_SECRET_ACCESS_KEY=your_secret_key
```

---

## Method 2: Programmatic Configuration

**Using `set_global_config()`:**

```python
from q_task.config import set_global_config

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
    rabbitmq_exchange_name='q_task',
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
```

**Using `Config.from_env()` with Overrides:**

```python
from q_task.config import Config

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
python -m q_task worker \
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
| `driver`              | `q_task_DRIVER`        | `redis`   | Queue driver                   |
| `default_queue`       | `q_task_DEFAULT_QUEUE` | `default` | Default queue name             |
| `default_max_retries` | `q_task_MAX_RETRIES`   | `3`       | Default max retry attempts     |
| `default_retry_delay` | `q_task_RETRY_DELAY`   | `60`      | Default retry delay (seconds)  |
| `default_timeout`     | `q_task_TIMEOUT`       | `None`    | Default task timeout (seconds) |

**Redis Options:**

| Option                  | Env Var                            | Default                  | Description                  |
| ----------------------- | ---------------------------------- | ------------------------ | ---------------------------- |
| `redis_url`             | `q_task_REDIS_URL`             | `redis://localhost:6379` | Redis connection URL         |
| `redis_password`        | `q_task_REDIS_PASSWORD`        | `None`                   | Redis password               |
| `redis_db`              | `q_task_REDIS_DB`              | `0`                      | Redis database number (0-15) |
| `redis_max_connections` | `q_task_REDIS_MAX_CONNECTIONS` | `10`                     | Redis connection pool size   |

**PostgreSQL Options:**

| Option                                | Env Var                                          | Default                                         | Description                  |
| ------------------------------------- | ------------------------------------------------ | ----------------------------------------------- | ---------------------------- |
| `postgres_dsn`                        | `q_task_POSTGRES_DSN`                        | `postgresql://test:test@localhost:5432/test_db` | PostgreSQL connection string |
| `postgres_queue_table`                | `q_task_POSTGRES_QUEUE_TABLE`                | `task_queue`                                    | Queue table name             |
| `postgres_dead_letter_table`          | `q_task_POSTGRES_DEAD_LETTER_TABLE`          | `dead_letter_queue`                             | Dead letter table name       |
| `postgres_max_attempts`               | `q_task_POSTGRES_MAX_ATTEMPTS`               | `3`                                             | Max attempts before DLQ      |
| `postgres_retry_delay_seconds`        | `q_task_POSTGRES_RETRY_DELAY_SECONDS`        | `60`                                            | Retry delay (seconds)        |
| `postgres_visibility_timeout_seconds` | `q_task_POSTGRES_VISIBILITY_TIMEOUT_SECONDS` | `300`                                           | Visibility timeout (seconds) |
| `postgres_min_pool_size`              | `q_task_POSTGRES_MIN_POOL_SIZE`              | `10`                                            | Min connection pool size     |
| `postgres_max_pool_size`              | `q_task_POSTGRES_MAX_POOL_SIZE`              | `10`                                            | Max connection pool size     |

**MySQL Options:**

| Option                             | Env Var                                       | Default                                    | Description                  |
| ---------------------------------- | --------------------------------------------- | ------------------------------------------ | ---------------------------- |
| `mysql_dsn`                        | `q_task_MYSQL_DSN`                        | `mysql://test:test@localhost:3306/test_db` | MySQL connection string      |
| `mysql_queue_table`                | `q_task_MYSQL_QUEUE_TABLE`                | `task_queue`                               | Queue table name             |
| `mysql_dead_letter_table`          | `q_task_MYSQL_DEAD_LETTER_TABLE`          | `dead_letter_queue`                        | Dead letter table name       |
| `mysql_max_attempts`               | `q_task_MYSQL_MAX_ATTEMPTS`               | `3`                                        | Max attempts before DLQ      |
| `mysql_retry_delay_seconds`        | `q_task_MYSQL_RETRY_DELAY_SECONDS`        | `60`                                       | Retry delay (seconds)        |
| `mysql_visibility_timeout_seconds` | `q_task_MYSQL_VISIBILITY_TIMEOUT_SECONDS` | `300`                                      | Visibility timeout (seconds) |
| `mysql_min_pool_size`              | `q_task_MYSQL_MIN_POOL_SIZE`              | `10`                                       | Min connection pool size     |
| `mysql_max_pool_size`              | `q_task_MYSQL_MAX_POOL_SIZE`              | `10`                                       | Max connection pool size     |

**RabbitMQ Options:**

| Option                    | Env Var                              | Default                              | Description                      |
| ------------------------- | ------------------------------------ | ------------------------------------ | -------------------------------- |
| `rabbitmq_url`            | `q_task_RABBITMQ_URL`            | `amqp://guest:guest@localhost:5672/` | RabbitMQ connection URL          |
| `rabbitmq_exchange_name`  | `q_task_RABBITMQ_EXCHANGE_NAME`  | `q_task`                         | RabbitMQ exchange name           |
| `rabbitmq_prefetch_count` | `q_task_RABBITMQ_PREFETCH_COUNT` | `1`                                  | RabbitMQ consumer prefetch count |

**AWS SQS Options:**

| Option                  | Env Var                       | Default     | Description                                          |
| ----------------------- | ----------------------------- | ----------- | ---------------------------------------------------- |
| `sqs_region`            | `q_task_SQS_REGION`       | `us-east-1` | AWS region                                           |
| `sqs_queue_url_prefix`  | `q_task_SQS_QUEUE_PREFIX` | `None`      | SQS queue URL prefix                                 |
| `aws_access_key_id`     | `AWS_ACCESS_KEY_ID`           | `None`      | AWS access key (optional, uses AWS credential chain) |
| `aws_secret_access_key` | `AWS_SECRET_ACCESS_KEY`       | `None`      | AWS secret key (optional, uses AWS credential chain) |
