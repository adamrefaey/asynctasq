# Configuration

AsyncTasQ uses the `asynctasq.init()` function as the primary configuration interface. This function initializes both configuration and event emitters.

## Configuration Contexts

AsyncTasQ configuration properties apply to different contexts depending on their usage:

### Dispatch Context
The **dispatch context** refers to when you're enqueuing/dispatching tasks to the queue (e.g., calling `task.dispatch()` in your application code).

### Worker Context
The **worker context** refers to when the worker process is running and processing tasks from the queue (e.g., running `asynctasq worker`).

### Context Applicability

| Configuration Group | Context | Description |
|-------------------|---------|-------------|
| **Driver Selection** (`driver`) | Both | Required for both dispatching and processing tasks |
| **Driver Configs** (`redis`, `sqs`, `postgres`, `mysql`, `rabbitmq`) | Both | Queue connections needed in both contexts |
| **Events** (`events`) | Both | Event emission happens during both dispatch and processing |
| **Task Defaults** | Mixed | See detailed breakdown below |
| **Process Pool** (`process_pool`) | Worker only | Only used by workers executing CPU-bound tasks |
| **Repository** (`repository`) | Worker only | Only used by workers when completing tasks |

#### Task Defaults Context Breakdown

| Property | Context | Usage |
|---------|---------|-------|
| `queue` | Both | Used when dispatching (stored in task), worker uses it as default |
| `max_attempts` | Both | Set during dispatch (stored in task), enforced by worker during retries |
| `retry_strategy` | Both | Set during dispatch (stored in task), used by worker for retry logic |
| `retry_delay` | Both | Set during dispatch (stored in task), used by worker for retry delays |
| `timeout` | **Worker only** | Enforced during task execution by the worker |
| `visibility_timeout` | **Worker only** | Used when dequeuing tasks for crash recovery |

## Table of Contents

- [Configuration](#configuration)
  - [Table of Contents](#table-of-contents)
  - [Configuration Functions](#configuration-functions)
    - [`asynctasq.init()`](#asynctasqinit)
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
      - [Understanding Visibility Timeout (Crash Recovery)](#understanding-visibility-timeout-crash-recovery)
    - [Process Pool Configuration](#process-pool-configuration)
      - [Warm Event Loops for AsyncProcessTask](#warm-event-loops-for-asyncprocesstask)
    - [Repository Configuration](#repository-configuration)

## Configuration Functions

### `asynctasq.init()`

Initialize AsyncTasQ with configuration and event emitters. **This function must be called before using any AsyncTasQ functionality.** It is recommended to call it as early as possible in your main script.

```python
import asynctasq
from asynctasq.config import RedisConfig

# Initialize with Redis driver
asynctasq.init({
    'driver': 'redis',
    'redis': RedisConfig(url='redis://localhost:6379')
})
```

**Parameters:**
- `config_overrides` (optional): Configuration overrides as a dictionary
- `event_emitters` (optional): List of additional event emitters to register

**Example with custom event emitters:**
```python
import asynctasq
from asynctasq.core.events import LoggingEventEmitter
from asynctasq.config import RedisConfig

# Create custom emitter
custom_emitter = LoggingEventEmitter()

# Initialize with config and additional emitters
asynctasq.init(
    config_overrides={
        'driver': 'redis',
        'redis': RedisConfig(url='redis://localhost:6379')
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
import asynctasq
from asynctasq.config import RedisConfig

asynctasq.init({
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
import asynctasq
from asynctasq.config import SQSConfig

asynctasq.init({
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

| Option              | Type | Description                            | Default                                         |
| ------------------- | ---: | -------------------------------------- | ----------------------------------------------- |
| `dsn`               |  str | PostgreSQL connection DSN              | `postgresql://test:test@localhost:5432/test_db` |
| `queue_table`       |  str | Queue table name                       | `task_queue`                                    |
| `dead_letter_table` |  str | Dead letter queue table name           | `dead_letter_queue`                             |
| `max_attempts`      |  int | Maximum attempts before dead-lettering | `3`                                             |
| `min_pool_size`     |  int | Minimum connection pool size           | `10`                                            |
| `max_pool_size`     |  int | Maximum connection pool size           | `10`                                            |

```python
import asynctasq
from asynctasq.config import PostgresConfig

asynctasq.init({
    'driver': 'postgres',
    'postgres': PostgresConfig(
        dsn='postgresql://user:pass@localhost:5432/mydb',
        queue_table='task_queue',
        dead_letter_table='dead_letter_queue',
        max_attempts=5,
        min_pool_size=10,
        max_pool_size=50
    )
})
```

---

### MySQL Configuration

Configuration group: `mysql` (type: `MySQLConfig`)

**Context: Both dispatch and worker contexts** – Used for queue connections in both task dispatching and processing.

| Option              | Type | Description                            | Default                                    |
| ------------------- | ---: | -------------------------------------- | ------------------------------------------ |
| `dsn`               |  str | MySQL connection DSN                   | `mysql://test:test@localhost:3306/test_db` |
| `queue_table`       |  str | Queue table name                       | `task_queue`                               |
| `dead_letter_table` |  str | Dead letter queue table name           | `dead_letter_queue`                        |
| `max_attempts`      |  int | Maximum attempts before dead-lettering | `3`                                        |
| `min_pool_size`     |  int | Minimum connection pool size           | `10`                                       |
| `max_pool_size`     |  int | Maximum connection pool size           | `10`                                       |

```python
import asynctasq
from asynctasq.config import MySQLConfig

asynctasq.init({
    'driver': 'mysql',
    'mysql': MySQLConfig(
        dsn='mysql://user:pass@localhost:3306/mydb',
        queue_table='task_queue',
        dead_letter_table='dead_letter_queue',
        max_attempts=5,
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
import asynctasq
from asynctasq.config import RabbitMQConfig

asynctasq.init({
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
import asynctasq
from asynctasq.config import EventsConfig, RedisConfig

asynctasq.init({
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

**Context: Mixed (see individual properties below)** – Some properties apply to both contexts, while others are worker-only.

Default settings for all tasks (can be overridden per task).

| Option               |        Type | Context | Description                                                                                           | Choices                | Default       |
| -------------------- | ----------: | ------- | ----------------------------------------------------------------------------------------------------- | ---------------------- | ------------- |
| `queue`              |         str | Both | Default queue name for tasks (used when dispatching, stored in task)                                  | —                      | `default`     |
| `max_attempts`       |         int | Both | Default maximum retry attempts (set during dispatch, enforced by worker)                              | —                      | `3`           |
| `retry_strategy`     |         str | Both | Retry delay strategy (set during dispatch, used by worker for retry logic)                            | `fixed`, `exponential` | `exponential` |
| `retry_delay`        |         int | Both | Base retry delay in seconds (set during dispatch, used by worker for retry delays)                    | —                      | `60`          |
| `timeout`            | int \| None | **Worker only** | Default task timeout in seconds - enforced during task execution (None = no timeout)         | —                      | `None`        |
| `visibility_timeout` |         int | **Worker only** | Crash recovery timeout - seconds a task is invisible before auto-recovery (PostgreSQL/MySQL/SQS only) | —                      | `300`         |

```python
import asynctasq
from asynctasq.config import TaskDefaultsConfig

asynctasq.init({
    'task_defaults': TaskDefaultsConfig(
        queue='high-priority',
        max_attempts=5,
        retry_strategy='exponential',
        retry_delay=120,
        timeout=600,
        visibility_timeout=300  # 5 minutes
    )
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
    'task_defaults': TaskDefaultsConfig(visibility_timeout=300)  # 5 minutes
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
    'task_defaults': TaskDefaultsConfig(visibility_timeout=180)  # (60 × 2) + 60 = 3 minutes
})
```

**Driver support:**
- ✅ **PostgreSQL**: Uses `locked_until` timestamp column
- ✅ **MySQL**: Uses `locked_until` timestamp column
- ✅ **SQS**: Built-in visibility timeout feature
- ❌ **Redis**: Uses consumer groups (different mechanism)
- ❌ **RabbitMQ**: Uses acknowledgment-based recovery (different mechanism)

**Important notes:**
- This is different from `task_defaults.timeout` (execution timeout per attempt)
- Only applies to PostgreSQL, MySQL, and SQS drivers
- Critical for production reliability and fault tolerance
- Prevents task loss when workers crash unexpectedly

---

### Process Pool Configuration

Configuration group: `process_pool` (type: `ProcessPoolConfig`)

**Context: Worker context only** – Only used by workers when executing CPU-bound tasks (`AsyncProcessTask` or `SyncProcessTask`).

| Option                |        Type | Description                                                    | Default |
| --------------------- | ----------: | -------------------------------------------------------------- | ------- |
| `size`                | int \| None | Number of worker processes (None = auto-detect CPU count)      | `None`  |
| `max_tasks_per_child` | int \| None | Recycle worker processes after N tasks (recommended: 100–1000) | `None`  |

```python
import asynctasq
from asynctasq.config import ProcessPoolConfig

asynctasq.init({
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

### Repository Configuration

Configuration group: `repository` (type: `RepositoryConfig`)

**Context: Worker context only** – Only used by workers when completing tasks to determine if they should be kept or removed.

| Option                 | Type | Description                                                     | Default |
| ---------------------- | ---: | --------------------------------------------------------------- | ------- |
| `keep_completed_tasks` | bool | Keep completed tasks for history/audit (not applicable for SQS) | `False` |

```python
import asynctasq
from asynctasq.config import RepositoryConfig

asynctasq.init({
    'repository': RepositoryConfig(keep_completed_tasks=True)
})
```
