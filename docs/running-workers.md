# Running Workers

## Table of Contents

- [Running Workers](#running-workers)
  - [Table of Contents](#table-of-contents)
  - [CLI Workers (Recommended)](#cli-workers-recommended)
  - [Programmatic Workers](#programmatic-workers)
  - [Multiple Workers for Different Queues](#multiple-workers-for-different-queues)
  - [Graceful Shutdown](#graceful-shutdown)
  - [Error Handling \& Reliability](#error-handling--reliability)

Workers continuously poll queues and execute tasks. Run workers via CLI (recommended) or programmatically.

## CLI Workers (Recommended)

**Basic Usage:**

Configure AsyncTasQ using a `.env` file (recommended) or environment variables:

```bash
# .env file
ASYNCTASQ_DRIVER=redis
ASYNCTASQ_REDIS_URL=redis://localhost:6379
```

```bash
# Start worker - configuration loaded from .env automatically
python -m asynctasq worker --queues default

# Or with uv
uv run asynctasq worker --queues default
```

**Multiple Queues with Priority:**

```bash
# Process queues in priority order: high → default → low
# Worker uses .env configuration automatically
uv run asynctasq worker --queues high,default,low --concurrency 20
```

**Advanced Options:**

```bash
# Worker with process pool for CPU-bound tasks
# Configuration from .env, only specify worker-specific options
uv run asynctasq worker \
    --queues default \
    --concurrency 10 \
    --process-pool-size 4 \
    --process-pool-max-tasks-per-child 100
```

**Note:** For all driver-specific configuration options and CLI reference, see [CLI Reference](cli-reference.md#worker-command). The CLI supports inline configuration arguments for testing, but **production deployments should use `.env` files** for cleaner command signatures and better configuration management.

For complete CLI options and parameters, see [CLI Reference](cli-reference.md#worker-command).

**Quick Start:**

---

## Programmatic Workers

For custom worker implementations or embedding workers in applications:

```python
import asyncio
from asynctasq import Config, DriverFactory, RedisConfig, Worker

async def main():
    # Create configuration
    config = Config(
        driver='redis',
        redis=RedisConfig(url='redis://localhost:6379')
    )

    # Create driver and connect
    driver = DriverFactory.create('redis', config)
    await driver.connect()

    try:
        # Create and start worker
        worker = Worker(
            queue_driver=driver,
            queues=['high-priority', 'default', 'low-priority'],
            concurrency=10
        )

        # Start worker (blocks until SIGTERM/SIGINT)
        await worker.start()
    finally:
        # Cleanup
        await driver.disconnect()

if __name__ == "__main__":
    from asynctasq import run

    run(main())
```

**Worker Parameters:**

| Parameter                          | Type             | Default             | Description                                       |
| ---------------------------------- | ---------------- | ------------------- | ------------------------------------------------- |
| `queue_driver`                     | `BaseDriver`     | -                   | Queue driver instance                             |
| `queues`                           | `list[str]`      | `["default"]`       | Queue names to process (priority order)           |
| `concurrency`                      | `int`            | `10`                | Maximum concurrent tasks                          |
| `max_tasks`                        | `int \| None`    | `None`              | Process N tasks then exit (None = run forever)    |
| `serializer`                       | `BaseSerializer` | `MsgpackSerializer` | Custom serializer                                 |
| `worker_id`                        | `str \| None`    | auto                | Custom worker identifier (auto-generated if None) |
| `heartbeat_interval`               | `float`          | `60.0`              | Seconds between heartbeat events                  |
| `process_pool_size`                | `int \| None`    | `None`              | Process pool size for CPU-bound tasks             |
| `process_pool_max_tasks_per_child` | `int \| None`    | `None`              | Recycle worker processes after N tasks            |

**Worker Behavior:**

1. **Polling Loop:** Continuously checks queues until stopped
2. **Round-Robin:** Processes queues in priority order (first = highest priority)
3. **Concurrency Control:** Tracks active tasks, respects concurrency limit
4. **Fair Distribution:** Polls all queues before repeating first queue
5. **Sleep on Empty:** 100ms sleep when no tasks available (prevents CPU spinning)
6. **Graceful Shutdown:** SIGTERM/SIGINT wait for in-flight tasks to complete

**Testing/Batch Mode:**

```python
# Process exactly 10 tasks then exit
worker = Worker(
    queue_driver=driver,
    queues=['default'],
    concurrency=5,
    max_tasks=10  # Exit after 10 tasks
)
await worker.start()
```

---

## Multiple Workers for Different Queues

Run multiple worker processes for different queue priorities:

```bash
# Terminal 1: High-priority queue with high concurrency
# Configuration from .env file
uv run asynctasq worker --queues high-priority --concurrency 20

# Terminal 2: Default queue with moderate concurrency
uv run asynctasq worker --queues default --concurrency 10

# Terminal 3: Low-priority and batch jobs with low concurrency
uv run asynctasq worker --queues low-priority,batch --concurrency 5
```

**Benefits:**

- Isolate critical tasks from low-priority work
- Prevent slow tasks from blocking fast tasks
- Scale different queues independently
- Dedicate resources based on queue importance

---

## Graceful Shutdown

Workers handle `SIGTERM` and `SIGINT` signals for clean shutdown:

**Shutdown Process:**

1. **Stop accepting new tasks** – No new tasks dequeued from driver
2. **Wait for completion** – Currently processing tasks finish naturally
3. **Disconnect** – Driver connections closed cleanly
4. **Exit** – Process terminates gracefully

**Trigger Shutdown:**

```bash
# Send SIGTERM for graceful shutdown
kill -TERM <worker_pid>

# Or use Ctrl+C for SIGINT (same behavior)
```

**Production Deployment:**

Use process managers that send SIGTERM for clean shutdowns:

- **systemd:** Sends SIGTERM by default
- **supervisor:** Configure `stopasgroup=true`
- **Kubernetes:** Sends SIGTERM before SIGKILL (grace period)
- **Docker:** `docker stop` sends SIGTERM

**Example systemd service:**

```ini
[Unit]
Description=AsyncTasQ Worker
After=network.target

[Service]
Type=simple
User=www-data
WorkingDirectory=/app
EnvironmentFile=/app/.env
ExecStart=/usr/bin/python -m asynctasq worker --queues default
Restart=always
KillSignal=SIGTERM
TimeoutStopSec=30

[Install]
WantedBy=multi-user.target
```

---

## Error Handling & Reliability

**Automatic Retry:**

Tasks that fail are automatically retried with configurable backoff strategies:

```python
from asynctasq import task

@task(max_attempts=5, retry_delay=30, retry_strategy='exponential')
async def process_order(order_id: int):
    # Task will retry up to 5 times with exponential backoff
    # Retry delays: 30s, 60s, 120s, 240s, 480s
    pass
```

**Dead Letter Queue:**

After exceeding `max_attempts`, failed tasks move to a dead letter queue (PostgreSQL/MySQL only). This prevents poison messages from blocking queue processing.

**Crash Recovery (Visibility Timeout):**

> **⚠️ CRITICAL:** See [Configuration - Visibility Timeout Warning](configuration.md#visibility-timeout-warning) for complete details on configuring crash recovery.

AsyncTasQ uses `visibility_timeout` to handle worker crashes:

- **Default:** `3600` seconds (1 hour)
- **Behavior:** If a worker crashes mid-task, the task becomes visible again after the timeout
- **Configuration:** Set via `visibility_timeout` parameter on tasks (see canonical warning above for best practices)

```python
@task(visibility_timeout=7200)  # 2 hours for long-running tasks
async def long_running_task():
    # If worker crashes, task reappears after 2 hours
    pass
```

**Task Timeout:**

Prevent tasks from running indefinitely:

```python
@task(timeout=300)  # 5 minutes
async def api_call():
    # Task raises TimeoutError if exceeds 5 minutes
    pass
```

**Health Monitoring:**

Workers emit events for monitoring:

- `worker_online` - Worker started
- `worker_heartbeat` - Periodic health check (default: every 60s)
- `worker_offline` - Worker shutdown
- `task_enqueued` - Task added to queue
- `task_started` - Task execution began
- `task_completed` - Task finished successfully
- `task_failed` - Task failed with error
- `task_retrying` - Task being retried

Enable Redis event emission for real-time monitoring:

```bash
# Configure in .env file:
# ASYNCTASQ_EVENTS_ENABLE_EVENT_EMITTER_REDIS=true
# ASYNCTASQ_EVENTS_REDIS_URL=redis://localhost:6379
# ASYNCTASQ_EVENTS_CHANNEL=asynctasq:events

# Then run worker with clean command signature
uv run asynctasq worker --queues default
```
