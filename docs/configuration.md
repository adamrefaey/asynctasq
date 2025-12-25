# Configuration

AsyncTasQ uses the `asynctasq.init()` function as the primary configuration interface. This function initializes both configuration and event emitters.

## Configuration Functions

## Table of Contents

- [Configuration](#configuration)
  - [Configuration Functions](#configuration-functions)
  - [Table of Contents](#table-of-contents)
    - [`asynctasq.init()`](#asynctasqinit)
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
    - [Task Repository Configuration](#task-repository-configuration)
  - [Complete Example](#complete-example)
  - [Best Practices](#best-practices)
  - [Environment-specific configuration example](#environment-specific-configuration-example)

### `asynctasq.init()`

Initialize AsyncTasQ with configuration and event emitters. **This function must be called before using any AsyncTasQ functionality.** It is recommended to call it as early as possible in your main script.

```python
import asynctasq

# Initialize with Redis driver
asynctasq.init({
    'driver': 'redis',
    'redis_url': 'redis://localhost:6379'
})
```

**Parameters:**
- `config_overrides` (optional): Configuration overrides as a dictionary
- `event_emitters` (optional): List of additional event emitters to register

**Example with custom event emitters:**
```python
import asynctasq
from asynctasq.core.events import LoggingEventEmitter

# Create custom emitter
custom_emitter = LoggingEventEmitter()

# Initialize with config and additional emitters
asynctasq.init(
    config_overrides={
        'driver': 'redis',
        'redis_url': 'redis://localhost:6379'
    },
    event_emitters=[custom_emitter]
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

All configuration options are set via the `config_overrides` parameter of `asynctasq.init()`.

### Driver Selection

| Option   | Type | Description         | Choices                                         | Default |
| -------- | ---: | ------------------- | ----------------------------------------------- | ------- |
| `driver` |  str | Queue driver to use | `redis`, `postgres`, `mysql`, `rabbitmq`, `sqs` | `redis` |

```python
import asynctasq

asynctasq.init({'driver': 'postgres'})
```

---

### Task Defaults

| Option                       |        Type | Description                                                                        | Choices                | Default       |
| ---------------------------- | ----------: | ---------------------------------------------------------------------------------- | ---------------------- | ------------- |
| `default_queue`              |         str | Default queue name for tasks                                                       | —                      | `default`     |
| `default_max_attempts`       |         int | Default maximum retry attempts                                                     | —                      | `3`           |
| `default_retry_strategy`     |         str | Retry delay strategy                                                               | `fixed`, `exponential` | `exponential` |
| `default_retry_delay`        |         int | Base retry delay in seconds                                                        | —                      | `60`          |
| `default_timeout`            | int \| None | Default task timeout in seconds (None = no timeout)                                | —                      | `None`        |
| `default_visibility_timeout` |         int | Crash recovery timeout - how long a task is invisible before auto-recovery (PostgreSQL/MySQL/SQS only) | —                      | `300`         |
| `correlation_id`             | str \| None | Optional correlation ID for distributed tracing (can be set per-task in TaskConfig) | —                      | `None`        |

```python
import asynctasq

asynctasq.init({
    'default_queue': 'high-priority',
    'default_max_attempts': 5,
    'default_retry_strategy': 'exponential',
    'default_retry_delay': 120,
    'default_timeout': 600,
    'default_visibility_timeout': 300  # 5 minutes
})
```

#### Understanding Visibility Timeout (Crash Recovery)

**What is visibility timeout?**

Visibility timeout is AsyncTasQ's **automatic crash recovery mechanism**. When a worker dequeues a task, the task becomes invisible to other workers for the specified duration. If the worker crashes and never acknowledges the task, it automatically becomes visible again after the timeout expires.

**How it works:**

1. **Worker A dequeues task** → Task marked as `processing`, locked until `NOW() + visibility_timeout`
2. **Task becomes invisible** → Other workers cannot see this task for `visibility_timeout` seconds
3. **Two possible outcomes:**
   - ✅ **Success**: Worker completes task and calls `ack()` → Task removed/completed permanently
   - ❌ **Crash**: Worker crashes without calling `ack()` → After timeout expires, task becomes visible again for another worker to retry

**Example scenario:**

```python
# Configuration
asynctasq.init({
    'driver': 'postgres',
    'default_visibility_timeout': 300  # 5 minutes
})

# Timeline:
# 11:00:00 - Worker A dequeues payment task (locked until 11:05:00)
# 11:00:45 - Worker A crashes (server dies, OOM, network failure)
# 11:00:46 - Task is invisible, other workers can't see it
# 11:05:00 - Visibility timeout expires
# 11:05:01 - Task automatically becomes visible again
# 11:05:02 - Worker B picks up the task and processes it successfully
# Result: No manual intervention needed, task recovered automatically!
```

**Choosing the right value:**

- **Too short** (e.g., 30s): Tasks taking longer than timeout will be processed by multiple workers (duplicate processing)
- **Too long** (e.g., 1 hour): Crashed tasks wait too long before retry, poor user experience
- **Recommended**: `visibility_timeout = (expected_task_duration × 2) + buffer`

**Example:**
```python
# Task typically takes 60 seconds
asynctasq.init({
    'default_visibility_timeout': 180  # (60 × 2) + 60 = 3 minutes
})
```

**Driver support:**
- ✅ **PostgreSQL**: Uses `locked_until` timestamp column
- ✅ **MySQL**: Uses `locked_until` timestamp column
- ✅ **SQS**: Built-in visibility timeout feature
- ❌ **Redis**: Uses consumer groups (different mechanism)
- ❌ **RabbitMQ**: Uses acknowledgment-based recovery (different mechanism)

**Important notes:**
- This is different from `task.timeout` (execution timeout per attempt)
- Only applies to PostgreSQL, MySQL, and SQS drivers
- Critical for production reliability and fault tolerance
- Prevents task loss when workers crash unexpectedly

---

### Process Pool Configuration

For CPU-bound tasks using `AsyncProcessTask` or `SyncProcessTask`.

| Option                             |        Type | Description                                                    | Default |
| ---------------------------------- | ----------: | -------------------------------------------------------------- | ------- |
| `process_pool_size`                | int \| None | Number of worker processes (None = auto-detect CPU count)      | `None`  |
| `process_pool_max_tasks_per_child` | int \| None | Recycle worker processes after N tasks (recommended: 100–1000) | `None`  |

```python
import asynctasq

asynctasq.init({
    'process_pool_size': 4,
    'process_pool_max_tasks_per_child': 100
})
```

#### Warm Event Loops for AsyncProcessTask

AsyncProcessTask requires an event loop in each worker process. AsyncTasQ provides two initialization modes:

1. **Warm Event Loops (Recommended)** - Pre-initialize event loops during worker startup for better performance
2. **On-Demand Event Loops** - Create event loops as needed (fallback, shows warnings)

**Initializing Warm Event Loops:**

```python
from asynctasq.tasks.infrastructure import ProcessPoolManager

# Initialize the process pool with warm event loops
async def init_worker():
    """Call this during worker startup (before processing tasks)."""
    manager = ProcessPoolManager.get_default_manager()
    await manager.initialize(
        pool_size=4,  # Number of worker processes
        max_tasks_per_child=100  # Recycle after 100 tasks
    )
    # Event loops are now pre-initialized in all worker processes

# In your worker startup code
import asyncio
asyncio.run(init_worker())
```

**Benefits of Warm Event Loops:**
- ⚡ **Faster task execution** - No loop creation overhead per task
- 🔇 **No warnings** - Eliminates "falling back to on-demand event loop" warnings
- 📊 **Better performance** - ~50ms saved per AsyncProcessTask execution

**When to Use:**
- ✅ If you use `AsyncProcessTask` (async CPU-intensive tasks)
- ✅ In production for optimal performance
- ❌ Not needed for `SyncProcessTask` (sync CPU-intensive tasks)
- ❌ Not needed for `AsyncTask` or `SyncTask` (I/O-bound tasks)

---

### Redis Driver Configuration

| Option                  |        Type | Description                       | Default                  |
| ----------------------- | ----------: | --------------------------------- | ------------------------ |
| `redis_url`             |         str | Redis connection URL              | `redis://localhost:6379` |
| `redis_password`        | str \| None | Redis password                    | `None`                   |
| `redis_db`              |         int | Redis database number (0–15)      | `0`                      |
| `redis_max_connections` |         int | Maximum connections in Redis pool | `100`                    |

```python
import asynctasq

asynctasq.init({
    'driver': 'redis',
    'redis_url': 'redis://prod.example.com:6379',
    'redis_password': 'secure_password',
    'redis_db': 1,
    'redis_max_connections': 200
})
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
import asynctasq

asynctasq.init({
    'driver': 'postgres',
    'postgres_dsn': 'postgresql://user:pass@localhost:5432/mydb',
    'postgres_queue_table': 'task_queue',
    'postgres_dead_letter_table': 'dead_letter_queue',
    'postgres_max_attempts': 5,
    'postgres_min_pool_size': 10,
    'postgres_max_pool_size': 50
})
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

asynctasq.init({
    'driver': 'mysql',
    'mysql_dsn': 'mysql://user:pass@localhost:3306/mydb',
    'mysql_queue_table': 'task_queue',
    'mysql_dead_letter_table': 'dead_letter_queue',
    'mysql_max_attempts': 5,
    'mysql_min_pool_size': 10,
    'mysql_max_pool_size': 50
})
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

asynctasq.init({
    'driver': 'rabbitmq',
    'rabbitmq_url': 'amqp://user:pass@localhost:5672/',
    'rabbitmq_exchange_name': 'my_exchange',
    'rabbitmq_prefetch_count': 10
})
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
import asynctasq

asynctasq.init({
    'driver': 'sqs',
    'sqs_region': 'us-west-2',
    'sqs_queue_url_prefix': 'https://sqs.us-west-2.amazonaws.com/123456789/',
    'aws_access_key_id': 'your_key',
    'aws_secret_access_key': 'your_secret'
})
```

---

### Task Repository Configuration

| Option                 | Type | Description                                                     | Default |
| ---------------------- | ---: | --------------------------------------------------------------- | ------- |
| `task_scan_limit`      |  int | Maximum tasks to scan in repository queries                     | `10000` |
| `keep_completed_tasks` | bool | Keep completed tasks for history/audit (not applicable for SQS) | `False` |

```python
from asynctasq.config import Config

asynctasq.init({
    'task_scan_limit': 50000,
    'keep_completed_tasks': True
})
```

---

## Complete Example

```python
import asynctasq

# Production PostgreSQL configuration
asynctasq.init({
    # Driver selection
    'driver': 'postgres',

    # PostgreSQL connection
    'postgres_dsn': 'postgresql://worker:secure_pass@db.prod.example.com:5432/asynctasq',
    'postgres_queue_table': 'task_queue',
    'postgres_dead_letter_table': 'dead_letter_queue',
    'postgres_max_attempts': 3,
    'postgres_min_pool_size': 10,
    'postgres_max_pool_size': 50,

    # Task defaults
    'default_queue': 'default',
    'default_max_attempts': 3,
    'default_retry_strategy': 'exponential',
    'default_retry_delay': 60,
    'default_timeout': 300,
    'default_visibility_timeout': 300,

    # Process pool for CPU-bound tasks
    'process_pool_size': 4,
    'process_pool_max_tasks_per_child': 100,

    # Events monitoring
    'enable_event_emitter_redis': True,
    'events_redis_url': 'redis://events.prod.example.com:6379',
    'events_channel': 'asynctasq:prod:events',

    # Task retention for audit
    'keep_completed_tasks': True,
    'task_scan_limit': 50000
})
```


---

## Best Practices

1. **Call `asynctasq.init()` once** at application startup before creating tasks or workers
2. **Use different configurations** for different environments (dev, staging, production)
3. **Store sensitive credentials** securely (secret managers, configuration files, etc.)
4. **Configure appropriate pool sizes** for database drivers based on your workload
5. **Set reasonable timeouts** to prevent hung tasks from blocking workers
6. **Use `keep_completed_tasks=True`** if you need task history for audit/compliance

---

## Environment-specific configuration example

This example shows how to configure AsyncTasQ differently for development, staging, and production environments. You can load configuration from any source (files, databases, secret managers, etc.).

```python
import os
from asynctasq.config import Config

# Determine environment
environment = os.getenv("APP_ENV", "development")

# Base configuration
base_config = {
    "default_max_attempts": 3,
    "default_retry_delay": 60,
    "default_timeout": 300,
    "process_pool_size": 4,
    "process_pool_max_tasks_per_child": 100,
}

# Environment-specific overrides
if environment == "development":
    config = {
        **base_config,
        "driver": "redis",
        "redis_url": "redis://localhost:6379",
        "enable_event_emitter_redis": False,
        "keep_completed_tasks": True,  # Keep tasks for debugging
    }
elif environment == "staging":
    config = {
        **base_config,
        "driver": "redis",
        "redis_url": "redis://staging-redis:6379",
        "redis_password": "staging-password",  # Load from secrets manager
        "enable_event_emitter_redis": True,
        "events_redis_url": "redis://staging-events:6379",
        "events_channel": "asynctasq:staging:events",
    }
elif environment == "production":
    config = {
        **base_config,
        "driver": "redis",
        "redis_url": "redis://prod-redis-cluster:6379",
        "redis_password": "prod-password",  # Load from secrets manager
        "default_max_attempts": 5,
        "default_retry_delay": 120,
        "enable_event_emitter_redis": True,
        "events_redis_url": "redis://prod-events-cluster:6379",
        "events_channel": "asynctasq:prod:events",
        "keep_completed_tasks": False,  # Don't keep completed tasks in prod
    }
else:
    raise ValueError(f"Unknown environment: {environment}")

# Apply configuration
asynctasq.init(config)

# Notes:
# - Use secret managers (AWS Secrets Manager, HashiCorp Vault, etc.) for credentials
# - Consider using configuration files (YAML, JSON, TOML) for complex setups
# - Validate configuration at startup to catch issues early
# - Use different Redis instances for events vs queues in production for better isolation
```
