# Configuration

AsyncTasQ uses the `init()` function as the primary configuration interface. Configuration can be provided via:
- **Code** (passing a dictionary to `init()`)
- **Environment variables** (with `ASYNCTASQ_` prefix)
- **.env files** (automatically loaded from project root)

See [Environment Variables](environment-variables.md) for complete details on environment-based configuration.

## Configuration Contexts

AsyncTasQ configuration properties apply to different contexts depending on their usage:

### Dispatch Context
The **dispatch context** refers to when you're enqueuing/dispatching tasks to the queue (e.g., calling `task.dispatch()` in your application code).

### Worker Context
The **worker context** refers to when the worker process is running and processing tasks from the queue (e.g., running `asynctasq worker`).

### Context Applicability

| Configuration Group                                                  | Context     | Description                                                     |
| -------------------------------------------------------------------- | ----------- | --------------------------------------------------------------- |
| **Driver Selection** (`driver`)                                      | Both        | Required for both dispatching and processing tasks              |
| **Driver Configs** (`redis`, `sqs`, `postgres`, `mysql`, `rabbitmq`) | Both        | Queue connections needed in both contexts                       |
| **Events** (`events`)                                                | Both        | Event emission happens during both dispatch and processing      |
| **Task Defaults**                                                    | Both        | Used when dispatching tasks and by workers when processing them |
| **Process Pool** (`process_pool`)                                    | Worker only | Only used by workers executing CPU-bound tasks                  |
| **Repository** (`repository`)                                        | Worker only | Only used by workers when completing tasks                      |

#### Task Defaults Context Breakdown

| Property         | Context | Usage                                                  |
| ---------------- | ------- | ------------------------------------------------------ |
| `queue`          | Both    | Used when dispatching and by workers                   |
| `max_attempts`   | Both    | Set during dispatch, enforced by worker during retries |
| `retry_strategy` | Both    | Set during dispatch, used by worker for retry logic    |
| `retry_delay`    | Both    | Set during dispatch, used by worker for retry delays   |

## Table of Contents

- [Configuration](#configuration)
  - [Configuration Contexts](#configuration-contexts)
    - [Dispatch Context](#dispatch-context)
    - [Worker Context](#worker-context)
    - [Context Applicability](#context-applicability)
      - [Task Defaults Context Breakdown](#task-defaults-context-breakdown)
  - [Table of Contents](#table-of-contents)
  - [Configuration Functions](#configuration-functions)
    - [`init()`](#init)
    - [`Config.get()`](#configget)
  - [Configuration Structure](#configuration-structure)
  - [Configuration Options](#configuration-options)
    - [Driver Selection](#driver-selection)
    - [Redis Configuration](#redis-configuration)
    - [SQS Configuration](#sqs-configuration)
    - [PostgreSQL Configuration](#postgresql-configuration)
    - [MySQL Configuration](#mysql-configuration)
    - [RabbitMQ Configuration](#rabbitmq-configuration)
    - [Events Configuration](#events-configuration)
    - [Task Defaults Configuration](#task-defaults-configuration)
    - [Process Pool Configuration](#process-pool-configuration)
      - [Warm Event Loops for AsyncProcessTask](#warm-event-loops-for-asyncprocesstask)
    - [Repository Configuration](#repository-configuration)

## Configuration Functions

### `init()`

Initialize AsyncTasQ with configuration and event emitters. **This function must be called before using any AsyncTasQ functionality.** It is recommended to call it as early as possible in your main script.

**Configuration Priority (highest to lowest):**
1. Arguments passed to `init()` (highest priority)
2. Environment variables
3. `.env` file
4. Default values (lowest priority)

```python
from asynctasq import init

# Option 1: .env file (recommended)
# Use the publish command to get a complete template:
#   asynctasq publish
#   cp .env.example .env
# Then edit .env with: ASYNCTASQ_DRIVER=redis
init()  # Loads from .env automatically

# Option 2: Environment variables
# Set ASYNCTASQ_DRIVER=redis and ASYNCTASQ_REDIS_URL=redis://localhost:6379
init()  # Loads from environment automatically

# Option 3: Code configuration (for quick testing or overrides)
from asynctasq import RedisConfig

init({
    'driver': 'redis',
    'redis': RedisConfig(url='redis://localhost:6379')
})
```

**💡 Tip:** Use `asynctasq publish` to generate a complete `.env.example` template with all available configuration options and documentation. See the [CLI Reference](cli-reference.md#publish-command) for details.

**Parameters:**
- `config` (optional): Configuration dictionary. Values passed here override environment variables and .env settings
- `event_emitters` (optional): List of additional event emitters to register
- `tortoise_config` (optional): Tortoise ORM configuration dictionary for automatic initialization when lazy ORM proxies are resolved in workers

**Example with custom event emitters:**
```python
from asynctasq import init, LoggingEventEmitter

# Create custom emitter
custom_emitter = LoggingEventEmitter()

# Initialize with additional emitters
# Config can come from environment variables or .env file
init(
    event_emitters=[custom_emitter]
)
```

**Example with Tortoise ORM:**
```python
from asynctasq import init

# Tortoise ORM config for automatic initialization
init(
    tortoise_config={
        'db_url': 'postgres://user:pass@localhost/db',
        'modules': {'models': ['myapp.models']}
    }
)
```

For more configuration examples and environment variable usage, see:
- [Environment Variables Guide](environment-variables.md) - Complete guide to .env files and environment variables
- [Queue Drivers](queue-drivers.md) - Driver-specific configuration examples

### `Config.get()`

Get the current global configuration. If not set, returns a `Config` with default values.

```python
from asynctasq import Config

config = Config.get()
print(config.driver)  # 'redis'
print(config.redis.url)  # 'redis://localhost:6379'
```

---

## Configuration Structure

AsyncTasQ uses a grouped configuration structure where related settings are organized into dataclasses. This provides better organization and type safety.

**Configuration Groups:**
- `driver`: Driver selection (top-level string)
- `redis`: Redis driver configuration (RedisConfig)
- `sqs`: AWS SQS driver configuration (SQSConfig)
- `postgres`: PostgreSQL driver configuration (PostgresConfig)
- `mysql`: MySQL driver configuration (MySQLConfig)
- `rabbitmq`: RabbitMQ driver configuration (RabbitMQConfig)
- `events`: Events and monitoring configuration (EventsConfig)
- `task_defaults`: Default task settings (TaskDefaultsConfig)
- `process_pool`: Process pool settings (ProcessPoolConfig)
- `repository`: Task repository settings (RepositoryConfig)
- `sqlalchemy_engine`: SQLAlchemy engine for cleanup (top-level, optional)
- `tortoise_orm`: Tortoise ORM configuration dictionary (top-level, optional)

---

## Configuration Options

All configuration options are set via the `config` parameter of `init()` (a dictionary), environment variables, or .env file.

### Driver Selection

| Option   | Type | Description         | Choices                                         | Default |
| -------- | ---: | ------------------- | ----------------------------------------------- | ------- |
| `driver` |  str | Queue driver to use | `redis`, `postgres`, `mysql`, `rabbitmq`, `sqs` | `redis` |

```python
from asynctasq import init

init({'driver': 'postgres'})
```

---

### Redis Configuration

Configuration group: `redis` (type: `RedisConfig`)

**Context: Both dispatch and worker contexts** – Used for queue connections in both task dispatching and processing.

| Option            |        Type | Description                       | Default                  |
| ----------------- | ----------: | --------------------------------- | ------------------------ |
| `url`             |         str | Redis connection URL              | `redis://localhost:6379` |
| `password`        | str \| None | Redis password                    | `None`                   |
| `db`              |         int | Redis database number (0–15)      | `0`                      |
| `max_connections` |         int | Maximum connections in Redis pool | `100`                    |

```python
from asynctasq import init, RedisConfig

init({
    'driver': 'redis',
    'redis': RedisConfig(
        url='redis://prod.example.com:6379',
        password='secure_password',
        db=1,
        max_connections=200
    )
})
```

---

### SQS Configuration

Configuration group: `sqs` (type: `SQSConfig`)

**Context: Both dispatch and worker contexts** – Used for queue connections in both task dispatching and processing.

| Option                  |        Type | Description                                        | Default     |
| ----------------------- | ----------: | -------------------------------------------------- | ----------- |
| `region`                |         str | AWS SQS region                                     | `us-east-1` |
| `queue_url_prefix`      | str \| None | SQS queue URL prefix                               | `None`      |
| `endpoint_url`          | str \| None | Custom SQS endpoint URL (for LocalStack, etc.)     | `None`      |
| `aws_access_key_id`     | str \| None | AWS access key ID (None uses credential chain)     | `None`      |
| `aws_secret_access_key` | str \| None | AWS secret access key (None uses credential chain) | `None`      |

```python
from asynctasq import init, SQSConfig

init({
    'driver': 'sqs',
    'sqs': SQSConfig(
        region='us-west-2',
        queue_url_prefix='https://sqs.us-west-2.amazonaws.com/123456789/',
        aws_access_key_id='your_key',
        aws_secret_access_key='your_secret'
    )
})
```

---

### PostgreSQL Configuration

Configuration group: `postgres` (type: `PostgresConfig`)

**Context: Both dispatch and worker contexts** – Used for queue connections in both task dispatching and processing.

**⚠️ Migration Required:** Before using the PostgreSQL driver, you must run migrations to create the required database tables:

```bash
uv run asynctasq migrate --driver postgres
```

This creates the `task_queue` and `dead_letter_queue` tables with the necessary schema.

| Option              | Type | Description                            | Default                                         |
| ------------------- | ---: | -------------------------------------- | ----------------------------------------------- |
| `dsn`               |  str | PostgreSQL connection DSN              | `postgresql://test:test@localhost:5432/test_db` |
| `queue_table`       |  str | Queue table name                       | `task_queue`                                    |
| `dead_letter_table` |  str | Dead letter queue table name           | `dead_letter_queue`                             |
| `min_pool_size`     |  int | Minimum connection pool size           | `10`                                            |
| `max_pool_size`     |  int | Maximum connection pool size           | `10`                                            |

```python
from asynctasq import init, PostgresConfig

init({
    'driver': 'postgres',
    'postgres': PostgresConfig(
        dsn='postgresql://user:pass@localhost:5432/mydb',
        queue_table='task_queue',
        dead_letter_table='dead_letter_queue',
        min_pool_size=10,
        max_pool_size=50
    )
})
```

---

### MySQL Configuration

Configuration group: `mysql` (type: `MySQLConfig`)

**Context: Both dispatch and worker contexts** – Used for queue connections in both task dispatching and processing.

**⚠️ Migration Required:** Before using the MySQL driver, you must run migrations to create the required database tables:

```bash
uv run asynctasq migrate --driver mysql
```

This creates the `task_queue` and `dead_letter_queue` tables with the necessary schema.

| Option              | Type | Description                            | Default                                    |
| ------------------- | ---: | -------------------------------------- | ------------------------------------------ |
| `dsn`               |  str | MySQL connection DSN                   | `mysql://test:test@localhost:3306/test_db` |
| `queue_table`       |  str | Queue table name                       | `task_queue`                               |
| `dead_letter_table` |  str | Dead letter queue table name           | `dead_letter_queue`                        |
| `min_pool_size`     |  int | Minimum connection pool size           | `10`                                       |
| `max_pool_size`     |  int | Maximum connection pool size           | `10`                                       |

```python
from asynctasq import init, MySQLConfig

init({
    'driver': 'mysql',
    'mysql': MySQLConfig(
        dsn='mysql://user:pass@localhost:3306/mydb',
        queue_table='task_queue',
        dead_letter_table='dead_letter_queue',
        min_pool_size=10,
        max_pool_size=50
    )
})
```

---

### RabbitMQ Configuration

Configuration group: `rabbitmq` (type: `RabbitMQConfig`)

**Context: Both dispatch and worker contexts** – Used for queue connections in both task dispatching and processing.

| Option           | Type | Description             | Default                              |
| ---------------- | ---: | ----------------------- | ------------------------------------ |
| `url`            |  str | RabbitMQ connection URL | `amqp://guest:guest@localhost:5672/` |
| `exchange_name`  |  str | RabbitMQ exchange name  | `asynctasq`                          |
| `prefetch_count` |  int | Consumer prefetch count | `1`                                  |

```python
from asynctasq import init, RabbitMQConfig

init({
    'driver': 'rabbitmq',
    'rabbitmq': RabbitMQConfig(
        url='amqp://user:pass@localhost:5672/',
        exchange_name='my_exchange',
        prefetch_count=10
    )
})
```

---

### Events Configuration

Configuration group: `events` (type: `EventsConfig`)

**Context: Both dispatch and worker contexts** – Event emission happens during both task dispatching and processing contexts.

Controls monitoring and event emission for task lifecycle events.

| Option                       |        Type | Description                                                             | Default            |
| ---------------------------- | ----------: | ----------------------------------------------------------------------- | ------------------ |
| `redis_url`                  | str \| None | Redis URL for event pub/sub (None uses main redis.url)                  | `None`             |
| `channel`                    |         str | Redis Pub/Sub channel name for events                                   | `asynctasq:events` |
| `enable_event_emitter_redis` |        bool | Enable Redis Pub/Sub event emitter for monitoring (task_enqueued, etc.) | `False`            |

```python
from asynctasq import init, EventsConfig, RedisConfig

init({
    'driver': 'redis',
    'redis': RedisConfig(url='redis://queue-redis:6379'),
    'events': EventsConfig(
        enable_event_emitter_redis=True,
        redis_url='redis://events-redis:6379',  # Separate Redis for events
        channel='asynctasq:prod:events'
    )
})
```

**Event Types Emitted:**
- `task_enqueued`: Task added to queue
- `task_started`: Worker started processing task
- `task_completed`: Task completed successfully
- `task_failed`: Task failed with error
- `task_retrying`: Task being retried after failure

---

### Task Defaults Configuration

Configuration group: `task_defaults` (type: `TaskDefaultsConfig`)

**Context: Both dispatch and worker contexts** – Used when dispatching tasks and by workers when processing them.

Default settings for all tasks.

**Important Distinction: Global Defaults vs Per-Task Configuration**

- **TaskDefaultsConfig** (this section): Global defaults set via `init()` that apply to all tasks unless overridden
- **TaskConfig** (per-task): Configuration set on individual task classes or via method chaining (`.timeout()`, `.visibility_timeout()`, etc.)

Per-task configuration always takes precedence over global defaults. The following are **only** configurable per-task:
- `timeout`: Task execution timeout (not a global default)
- `visibility_timeout`: **⚠️ CRITICAL - Default: 3600s (1 hour)** - Crash recovery timeout. Must be longer than task execution time to prevent duplicate processing.
- `correlation_id`: Distributed tracing ID (per-task only)
- `driver`: Driver override for routing specific tasks

See [Task Definitions](task-definitions.md) for complete TaskConfig documentation.

| Option           | Type | Context | Description                         | Choices                | Default       |
| ---------------- | ---: | ------- | ----------------------------------- | ---------------------- | ------------- |
| `queue`          |  str | Both    | Default queue name for tasks        | —                      | `default`     |
| `max_attempts`   |  int | Both    | Default maximum retry attempts      | —                      | `3`           |
| `retry_strategy` |  str | Both    | Default retry delay strategy        | `fixed`, `exponential` | `exponential` |
| `retry_delay`    |  int | Both    | Default base retry delay in seconds | —                      | `60`          |

```python
from asynctasq import init, TaskDefaultsConfig

init({
    'task_defaults': TaskDefaultsConfig(
        queue='high-priority',
        max_attempts=5,
        retry_strategy='exponential',
        retry_delay=120
    )
})
```

---

### Process Pool Configuration

Configuration group: `process_pool` (type: `ProcessPoolConfig`)

**Context: Worker context only** – Only used by workers when executing CPU-bound tasks (`AsyncProcessTask` or `SyncProcessTask`).

| Option                |        Type | Description                                                    | Default |
| --------------------- | ----------: | -------------------------------------------------------------- | ------- |
| `size`                | int \| None | Number of worker processes (None = auto-detect CPU count)      | `None`  |
| `max_tasks_per_child` | int \| None | Recycle worker processes after N tasks (recommended: 100–1000) | `None`  |

```python
from asynctasq import init, ProcessPoolConfig

init({
    'process_pool': ProcessPoolConfig(
        size=4,
        max_tasks_per_child=100
    )
})
```

#### Warm Event Loops for AsyncProcessTask

AsyncProcessTask requires an event loop in each worker process. AsyncTasQ provides two initialization modes:

1. **Warm Event Loops (Recommended)** - Pre-initialize event loops during worker startup for better performance
2. **On-Demand Event Loops** - Create event loops as needed (fallback, shows warnings)

**Initializing Warm Event Loops:**

```python
from asynctasq import ProcessPoolManager

# Initialize the process pool with warm event loops
async def init_worker():
    """Call this during worker startup (before processing tasks)."""
    manager = ProcessPoolManager(
        async_max_workers=4,  # Number of worker processes for async pool
        async_max_tasks_per_child=100  # Recycle after 100 tasks
    )
    await manager.initialize()
    # Event loops are now pre-initialized in all worker processes

# In your worker startup code
import asyncio
asyncio.run(init_worker())
```

**Note:** The `set_default_manager()` function is available from `asynctasq.tasks.infrastructure.process_pool_manager` if you need to set a custom default manager for the current process.

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

### Repository Configuration

Configuration group: `repository` (type: `RepositoryConfig`)

**Context: Worker context only** – Only used by workers when completing tasks to determine if they should be kept or removed.

| Option                 | Type | Description                                                     | Default |
| ---------------------- | ---: | --------------------------------------------------------------- | ------- |
| `keep_completed_tasks` | bool | Keep completed tasks for history/audit (not applicable for SQS) | `False` |

```python
from asynctasq import init, RepositoryConfig

init({
    'repository': RepositoryConfig(keep_completed_tasks=True)
})
```
