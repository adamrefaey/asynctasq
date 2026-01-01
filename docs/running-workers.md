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

```bash
# Start worker with default settings
python -m asynctasq worker

# Or with uv
uv run python -m asynctasq worker
```

**With Driver Configuration:**

```bash
# Redis worker
python -m asynctasq worker \
    --driver redis \
    --redis-url redis://localhost:6379 \
    --redis-password secret \
    --redis-db 1

# PostgreSQL worker
python -m asynctasq worker \
    --driver postgres \
    --postgres-dsn postgresql://user:pass@localhost/dbname \
    --queues default,emails \
    --concurrency 10

# MySQL worker
python -m asynctasq worker \
    --driver mysql \
    --mysql-dsn mysql://user:pass@localhost:3306/dbname \
    --queues default,emails \
    --concurrency 10

# RabbitMQ worker
python -m asynctasq worker \
    --driver rabbitmq \
    --rabbitmq-url amqp://user:pass@localhost:5672/ \
    --queues default,emails \
    --concurrency 10

# AWS SQS worker
python -m asynctasq worker \
    --driver sqs \
    --sqs-region us-west-2 \
    --sqs-queue-url-prefix https://sqs.us-west-2.amazonaws.com/123456789/ \
    --queues default,emails
```

**Multiple Queues with Priority:**

```bash
# Process queues in priority order: high → default → low
python -m asynctasq worker --queues high,default,low --concurrency 20
```

**Advanced CLI Options:**

```bash
# Worker with process pool for CPU-bound tasks
python -m asynctasq worker \
    --driver redis \
    --queues default \
    --concurrency 10 \
    --process-pool-size 4 \
    --process-pool-max-tasks-per-child 100

# Worker with monitoring enabled
python -m asynctasq worker \
    --driver redis \
    --queues default \
    --events-enable-event-emitter-redis \
    --events-redis-url redis://localhost:6379 \
    --events-channel asynctasq:prod:events

# Worker with completed task retention (for PostgreSQL/MySQL/Redis)
python -m asynctasq worker \
    --driver postgres \
    --postgres-dsn postgresql://user:pass@localhost/db \
    --queues default \
    --repository-keep-completed-tasks
```

**Worker Options:**

| Option                                | Description                                      | Default            |
| ------------------------------------- | ------------------------------------------------ | ------------------ |
| `--driver`                            | Queue driver (redis/postgres/mysql/rabbitmq/sqs) | `redis`            |
| `--queues`                            | Comma-separated queue names (priority order)     | `default`          |
| `--concurrency`                       | Max concurrent tasks                             | `10`               |
| `--process-pool-size`                 | Process pool size for CPU-bound tasks            | `None`             |
| `--process-pool-max-tasks-per-child`  | Recycle worker processes after N tasks           | `None`             |
| `--repository-keep-completed-tasks`   | Keep completed tasks for history/audit           | `False`            |
| `--events-enable-event-emitter-redis` | Enable Redis event pub/sub for monitoring        | `False`            |
| `--events-redis-url`                  | Redis URL for event pub/sub                      | `None`             |
| `--events-channel`                    | Redis Pub/Sub channel name for events            | `asynctasq:events` |
| `--task-defaults-queue`               | Default queue name for tasks                     | `default`          |
| `--task-defaults-max-attempts`        | Default maximum retry attempts                   | `3`                |
| `--task-defaults-retry-strategy`      | Retry delay strategy (fixed/exponential)         | `exponential`      |
| `--task-defaults-retry-delay`         | Base retry delay in seconds                      | `60`               |
| `--task-defaults-timeout`             | Default task timeout in seconds                  | `None`             |
| `--task-defaults-visibility-timeout`  | Visibility timeout for crash recovery (seconds)  | `300`              |

**Driver-Specific Options:**

<details>
<summary><strong>Redis Options</strong></summary>

| Option                    | Description           | Default                  |
| ------------------------- | --------------------- | ------------------------ |
| `--redis-url`             | Redis connection URL  | `redis://localhost:6379` |
| `--redis-password`        | Redis password        | `None`                   |
| `--redis-db`              | Redis database number | `0`                      |
| `--redis-max-connections` | Redis max connections | `100`                    |

</details>

<details>
<summary><strong>PostgreSQL Options</strong></summary>

| Option                         | Description                        | Default                                         |
| ------------------------------ | ---------------------------------- | ----------------------------------------------- |
| `--postgres-dsn`               | PostgreSQL connection DSN          | `postgresql://test:test@localhost:5432/test_db` |
| `--postgres-queue-table`       | Queue table name                   | `task_queue`                                    |
| `--postgres-dead-letter-table` | Dead letter table name             | `dead_letter_queue`                             |
| `--postgres-max-attempts`      | Max attempts before dead-lettering | `3`                                             |
| `--postgres-min-pool-size`     | Minimum connection pool size       | `10`                                            |
| `--postgres-max-pool-size`     | Maximum connection pool size       | `10`                                            |

</details>

<details>
<summary><strong>MySQL Options</strong></summary>

| Option                      | Description                        | Default                                    |
| --------------------------- | ---------------------------------- | ------------------------------------------ |
| `--mysql-dsn`               | MySQL connection DSN               | `mysql://test:test@localhost:3306/test_db` |
| `--mysql-queue-table`       | Queue table name                   | `task_queue`                               |
| `--mysql-dead-letter-table` | Dead letter table name             | `dead_letter_queue`                        |
| `--mysql-max-attempts`      | Max attempts before dead-lettering | `3`                                        |
| `--mysql-min-pool-size`     | Minimum connection pool size       | `10`                                       |
| `--mysql-max-pool-size`     | Maximum connection pool size       | `10`                                       |

</details>

<details>
<summary><strong>RabbitMQ Options</strong></summary>

| Option                      | Description             | Default                              |
| --------------------------- | ----------------------- | ------------------------------------ |
| `--rabbitmq-url`            | RabbitMQ connection URL | `amqp://guest:guest@localhost:5672/` |
| `--rabbitmq-exchange-name`  | RabbitMQ exchange name  | `asynctasq`                          |
| `--rabbitmq-prefetch-count` | Consumer prefetch count | `1`                                  |

</details>

<details>
<summary><strong>AWS SQS Options</strong></summary>

| Option                    | Description                       | Default                              |
| ------------------------- | --------------------------------- | ------------------------------------ |
| `--sqs-region`            | AWS SQS region                    | `us-east-1`                          |
| `--sqs-queue-url-prefix`  | SQS queue URL prefix              | `None`                               |
| `--sqs-endpoint-url`      | SQS endpoint URL (for LocalStack) | `None`                               |
| `--aws-access-key-id`     | AWS access key ID                 | From `AWS_ACCESS_KEY_ID` env var     |
| `--aws-secret-access-key` | AWS secret access key             | From `AWS_SECRET_ACCESS_KEY` env var |

</details>

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
python -m asynctasq worker --queues high-priority --concurrency 20

# Terminal 2: Default queue with moderate concurrency
python -m asynctasq worker --queues default --concurrency 10

# Terminal 3: Low-priority and batch jobs with low concurrency
python -m asynctasq worker --queues low-priority,batch --concurrency 5
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
ExecStart=/usr/bin/python -m asynctasq worker --driver redis --queues default
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

AsyncTasQ uses visibility timeout to handle worker crashes:

- **Default:** 300 seconds (5 minutes)
- **Behavior:** If a worker crashes mid-task, the task becomes visible again after the timeout
- **Configuration:** Set via `visibility_timeout` parameter on tasks

```python
@task(visibility_timeout=600)  # 10 minutes
async def long_running_task():
    # If worker crashes, task reappears after 10 minutes
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
python -m asynctasq worker \
    --driver redis \
    --events-enable-event-emitter-redis \
    --events-redis-url redis://localhost:6379 \
    --events-channel asynctasq:events
```
