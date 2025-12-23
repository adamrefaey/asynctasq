# Configuration

AsyncTasQ uses `Config.set()` and `Config.get()` as the primary configuration interface. Users should not instantiate `Config` directly.

## Configuration Functions

## Table of Contents

- [Configuration](#configuration)
  - [Configuration Functions](#configuration-functions)
  - [Table of Contents](#table-of-contents)
    - [`Config.set(**kwargs)`](#configsetkwargs)
    - [`Config.get()`](#configget)
  - [Configuration Options](#configuration-options)
    - [Driver Selection](#driver-selection)
    - [Task Defaults](#task-defaults)
    - [Process Pool Configuration](#process-pool-configuration)
    - [Redis Driver Configuration](#redis-driver-configuration)
    - [PostgreSQL Driver Configuration](#postgresql-driver-configuration)
    - [MySQL Driver Configuration](#mysql-driver-configuration)
    - [RabbitMQ Driver Configuration](#rabbitmq-driver-configuration)
    - [AWS SQS Driver Configuration](#aws-sqs-driver-configuration)
    - [Events \& Monitoring Configuration](#events--monitoring-configuration)
    - [Task Repository Configuration](#task-repository-configuration)
  - [Complete Example](#complete-example)
  - [Best Practices](#best-practices)
  - [Environment-driven configuration example](#environment-driven-configuration-example)

### `Config.set(**kwargs)`

Set the global configuration for AsyncTasQ. Call this once at application startup before creating tasks or workers.

```python
from asynctasq.config import Config

Config.set(
    driver='redis',
    redis_url='redis://localhost:6379'
)
```

### `Config.get()`

Get the current global configuration. If not set, returns a `Config` with default values.

```python
from asynctasq.config import Config

config = Config.get()
print(config.driver)  # 'redis'
```

---

## Configuration Options

All configuration options are set via keyword arguments to `Config.set()`.

### Driver Selection

| Option   | Type | Description         | Choices                                         | Default |
| -------- | ---: | ------------------- | ----------------------------------------------- | ------- |
| `driver` |  str | Queue driver to use | `redis`, `postgres`, `mysql`, `rabbitmq`, `sqs` | `redis` |

```python
from asynctasq.config import Config

Config.set(driver='postgres')
```

---

### Task Defaults

| Option                       |        Type | Description                                         | Choices                | Default       |
| ---------------------------- | ----------: | --------------------------------------------------- | ---------------------- | ------------- |
| `default_queue`              |         str | Default queue name for tasks                        | —                      | `default`     |
| `default_max_attempts`       |         int | Default maximum retry attempts                      | —                      | `3`           |
| `default_retry_strategy`     |         str | Retry delay strategy                                | `fixed`, `exponential` | `exponential` |
| `default_retry_delay`        |         int | Base retry delay in seconds                         | —                      | `60`          |
| `default_timeout`            | int \| None | Default task timeout in seconds (None = no timeout) | —                      | `None`        |
| `default_visibility_timeout` |         int | Visibility timeout for crash recovery in seconds    | —                      | `300`         |

```python
from asynctasq.config import Config

Config.set(
    default_queue='high-priority',
    default_max_attempts=5,
    default_retry_strategy='exponential',
    default_retry_delay=120,
    default_timeout=600,
    default_visibility_timeout=300
)
```

---

### Process Pool Configuration

For CPU-bound tasks using `AsyncProcessTask` or `SyncProcessTask`.

| Option                             |        Type | Description                                                    | Default |
| ---------------------------------- | ----------: | -------------------------------------------------------------- | ------- |
| `process_pool_size`                | int \| None | Number of worker processes (None = auto-detect CPU count)      | `None`  |
| `process_pool_max_tasks_per_child` | int \| None | Recycle worker processes after N tasks (recommended: 100–1000) | `None`  |

```python
from asynctasq.config import Config

Config.set(
    process_pool_size=4,
    process_pool_max_tasks_per_child=100
)
```

---

### Redis Driver Configuration

| Option                  |        Type | Description                       | Default                  |
| ----------------------- | ----------: | --------------------------------- | ------------------------ |
| `redis_url`             |         str | Redis connection URL              | `redis://localhost:6379` |
| `redis_password`        | str \| None | Redis password                    | `None`                   |
| `redis_db`              |         int | Redis database number (0–15)      | `0`                      |
| `redis_max_connections` |         int | Maximum connections in Redis pool | `100`                    |

```python
from asynctasq.config import Config

Config.set(
    driver='redis',
    redis_url='redis://prod.example.com:6379',
    redis_password='secure_password',
    redis_db=1,
    redis_max_connections=200
)
```

---

### PostgreSQL Driver Configuration

| Option                       | Type | Description                            | Default                                         |
| ---------------------------- | ---: | -------------------------------------- | ----------------------------------------------- |
| `postgres_dsn`               |  str | PostgreSQL connection DSN              | `postgresql://test:test@localhost:5432/test_db` |
| `postgres_queue_table`       |  str | Queue table name                       | `task_queue`                                    |
| `postgres_dead_letter_table` |  str | Dead letter queue table name           | `dead_letter_queue`                             |
| `postgres_max_attempts`      |  int | Maximum attempts before dead-lettering | `3`                                             |
| `postgres_min_pool_size`     |  int | Minimum connection pool size           | `10`                                            |
| `postgres_max_pool_size`     |  int | Maximum connection pool size           | `10`                                            |

```python
from asynctasq.config import Config

Config.set(
    driver='postgres',
    postgres_dsn='postgresql://user:pass@localhost:5432/mydb',
    postgres_queue_table='task_queue',
    postgres_dead_letter_table='dead_letter_queue',
    postgres_max_attempts=5,
    postgres_min_pool_size=10,
    postgres_max_pool_size=50
)
```

---

### MySQL Driver Configuration

| Option                    | Type | Description                            | Default                                    |
| ------------------------- | ---: | -------------------------------------- | ------------------------------------------ |
| `mysql_dsn`               |  str | MySQL connection DSN                   | `mysql://test:test@localhost:3306/test_db` |
| `mysql_queue_table`       |  str | Queue table name                       | `task_queue`                               |
| `mysql_dead_letter_table` |  str | Dead letter queue table name           | `dead_letter_queue`                        |
| `mysql_max_attempts`      |  int | Maximum attempts before dead-lettering | `3`                                        |
| `mysql_min_pool_size`     |  int | Minimum connection pool size           | `10`                                       |
| `mysql_max_pool_size`     |  int | Maximum connection pool size           | `10`                                       |

```python
from asynctasq.config import Config

Config.set(
    driver='mysql',
    mysql_dsn='mysql://user:pass@localhost:3306/mydb',
    mysql_queue_table='task_queue',
    mysql_dead_letter_table='dead_letter_queue',
    mysql_max_attempts=5,
    mysql_min_pool_size=10,
    mysql_max_pool_size=50
)
```

---

### RabbitMQ Driver Configuration

| Option                    | Type | Description             | Default                              |
| ------------------------- | ---: | ----------------------- | ------------------------------------ |
| `rabbitmq_url`            |  str | RabbitMQ connection URL | `amqp://guest:guest@localhost:5672/` |
| `rabbitmq_exchange_name`  |  str | RabbitMQ exchange name  | `asynctasq`                          |
| `rabbitmq_prefetch_count` |  int | Consumer prefetch count | `1`                                  |

```python
from asynctasq.config import Config

Config.set(
    driver='rabbitmq',
    rabbitmq_url='amqp://user:pass@localhost:5672/',
    rabbitmq_exchange_name='my_exchange',
    rabbitmq_prefetch_count=10
)
```

---

### AWS SQS Driver Configuration

| Option                  |        Type | Description                                        | Default     |
| ----------------------- | ----------: | -------------------------------------------------- | ----------- |
| `sqs_region`            |         str | AWS SQS region                                     | `us-east-1` |
| `sqs_queue_url_prefix`  | str \| None | SQS queue URL prefix                               | `None`      |
| `aws_access_key_id`     | str \| None | AWS access key ID (None uses credential chain)     | `None`      |
| `aws_secret_access_key` | str \| None | AWS secret access key (None uses credential chain) | `None`      |

```python
from asynctasq.config import Config

Config.set(
    driver='sqs',
    sqs_region='us-west-2',
    sqs_queue_url_prefix='https://sqs.us-west-2.amazonaws.com/123456789/',
    aws_access_key_id='your_key',
    aws_secret_access_key='your_secret'
)
```

---

### Events & Monitoring Configuration

For Redis Pub/Sub event monitoring.

| Option             |        Type | Description                                             | Default            |
| ------------------ | ----------: | ------------------------------------------------------- | ------------------ |
| `events_redis_url` | str \| None | Redis URL for event Pub/Sub (falls back to `redis_url`) | `None`             |
| `events_channel`   |         str | Redis Pub/Sub channel name                              | `asynctasq:events` |

```python
from asynctasq.config import Config

Config.set(
    events_redis_url='redis://events.example.com:6379',
    events_channel='asynctasq:prod:events'
)
```

---

### Task Repository Configuration

| Option                 | Type | Description                                                     | Default |
| ---------------------- | ---: | --------------------------------------------------------------- | ------- |
| `task_scan_limit`      |  int | Maximum tasks to scan in repository queries                     | `10000` |
| `keep_completed_tasks` | bool | Keep completed tasks for history/audit (not applicable for SQS) | `False` |

```python
from asynctasq.config import Config

Config.set(
    task_scan_limit=50000,
    keep_completed_tasks=True
)
```

---

## Complete Example

```python
from asynctasq.config import Config

# Production PostgreSQL configuration
Config.set(
    # Driver selection
    driver='postgres',

    # PostgreSQL connection
    postgres_dsn='postgresql://worker:secure_pass@db.prod.example.com:5432/asynctasq',
    postgres_queue_table='task_queue',
    postgres_dead_letter_table='dead_letter_queue',
    postgres_max_attempts=3,
    postgres_min_pool_size=10,
    postgres_max_pool_size=50,

    # Task defaults
    default_queue='default',
    default_max_attempts=3,
    default_retry_strategy='exponential',
    default_retry_delay=60,
    default_timeout=300,
    default_visibility_timeout=300,

    # Process pool for CPU-bound tasks
    process_pool_size=4,
    process_pool_max_tasks_per_child=100,

    # Events monitoring
    events_redis_url='redis://events.prod.example.com:6379',
    events_channel='asynctasq:prod:events',

    # Task retention for audit
    keep_completed_tasks=True,
    task_scan_limit=50000
)
```

---

## Best Practices

1. **Call `Config.set()` once** at application startup before creating tasks or workers
2. **Use different configurations** for different environments (dev, staging, production)
3. **Store sensitive credentials** securely (environment variables, secret managers, etc.)
4. **Configure appropriate pool sizes** for database drivers based on your workload
5. **Set reasonable timeouts** to prevent hung tasks from blocking workers
6. **Use `keep_completed_tasks=True`** if you need task history for audit/compliance

---

## Environment-driven configuration example

This example shows a simple, 12-factor-friendly way to configure AsyncTasQ from
environment variables. It reads commonly used settings, provides sensible
defaults, and includes a note about using `python-dotenv` for local
development.

```python
import os
from asynctasq.config import Config

# Optional: load a .env file in development (install python-dotenv)
# from dotenv import load_dotenv
# load_dotenv()

# Helper to read booleans from env
def env_bool(name: str, default: bool = False) -> bool:
    val = os.getenv(name)
    if val is None:
        return default
    return val.lower() not in ("0", "false", "no", "off")

# Read configuration from environment with sensible defaults
from asynctasq.config import Config

Config.set(
    driver=os.getenv("ASYNCTASQ_DRIVER", "redis"),
    redis_url=os.getenv("ASYNCTASQ_REDIS_URL", "redis://localhost:6379"),
    postgres_dsn=os.getenv("ASYNCTASQ_POSTGRES_DSN"),
    default_queue=os.getenv("ASYNCTASQ_DEFAULT_QUEUE", "default"),
    default_max_attempts=int(os.getenv("ASYNCTASQ_MAX_ATTEMPTS", "3")),
    default_retry_strategy=os.getenv("ASYNCTASQ_RETRY_STRATEGY", "exponential"),
    default_retry_delay=int(os.getenv("ASYNCTASQ_RETRY_DELAY", "60")),
    default_timeout=(int(os.getenv("ASYNCTASQ_TIMEOUT")) if os.getenv("ASYNCTASQ_TIMEOUT") else None),
    default_visibility_timeout=int(os.getenv("ASYNCTASQ_VISIBILITY_TIMEOUT", "300")),
    keep_completed_tasks=env_bool("ASYNCTASQ_KEEP_COMPLETED_TASKS", False),
)

# Notes:
# - Prefer distinct environment variables per deployment (dev/staging/prod).
# - Use a secrets manager or CI/CD environment injection to provide credentials.
# - For local development you can store variables in a `.env` file and load it
#   with `python-dotenv` as shown above.
```
