# Best Practices

## Task Design

✅ **Do:**

- Keep tasks small and focused (single responsibility principle)
- Make tasks idempotent when possible (safe to run multiple times with same result)
- Use timeouts for long-running tasks to prevent resource exhaustion
- Implement custom `failed()` handlers for cleanup, logging, and alerting
- Use `should_retry()` for intelligent retry logic based on exception type
- Pass ORM models directly as parameters - they're automatically serialized as lightweight references and re-fetched with fresh data when the task executes (Supported ORMs: SQLAlchemy, Django ORM, Tortoise ORM)
- Use type hints on task parameters for better IDE support and documentation
- Name tasks descriptively (class name or function name should explain purpose)

❌ **Don't:**

- Include blocking I/O in async tasks (use `SyncTask` with thread pool or `SyncProcessTask` for CPU-bound work)
- Share mutable state between tasks (each task execution should be isolated)
- Perform network calls without timeouts (always use `timeout` parameter)
- Store large objects in task parameters (serialize references instead, e.g., database IDs)
- Use reserved parameter names (`config`, `run`, `execute`, `dispatch`, `failed`, `should_retry`, `on_queue`, `delay`, `retry_after`)
- Start parameter names with underscore (reserved for internal use)

## Queue Organization

✅ **Do:**

- Use separate queues for different priorities (high/default/low)
- Isolate slow tasks in dedicated queues
- Group related tasks by queue (emails, reports, notifications)
- Consider worker capacity when designing queues
- Use descriptive queue names

**Example:**

```bash
# Worker 1: Critical tasks
python -m asynctasq worker --queues critical --concurrency 20

# Worker 2: Normal tasks
python -m asynctasq worker --queues default --concurrency 10

# Worker 3: Background tasks
python -m asynctasq worker --queues low-priority,batch --concurrency 5
```

## Error Handling

✅ **Do:**

- Log errors comprehensively in `failed()` method
- Use retry limits to prevent infinite loops
- Monitor dead-letter queues regularly
- Implement alerting for critical failures
- Add context to exception messages

```python
class ProcessPayment(AsyncTask[bool]):
    async def failed(self, exception: Exception) -> None:
        # Log with context (ensure `logger` is defined/imported in your module)
        logger.error(
            f"Payment failed for user {self.user_id}",
            extra={
                "task_id": self._task_id,
                "current_attempt": self._current_attempt,
                "user_id": self.user_id,
                "amount": self.amount,
            },
            exc_info=exception,
        )
        # Alert on critical failures
        await notify_admin(exception)
```

## Performance

✅ **Do:**

- Tune worker concurrency based on task characteristics
  - I/O-bound tasks: High concurrency (20-50)
  - CPU-bound tasks: Low concurrency (number of CPU cores)
- Use connection pooling (configured automatically)
- Monitor queue sizes and adjust worker count accordingly
- Consider task batching for high-volume operations
- Prefer `redis` for general production use; use `postgres` or `mysql` when you need ACID guarantees

## Production Deployment

✅ **Do:**

- **Use Redis for high-throughput** or **PostgreSQL/MySQL for ACID guarantees** in production
- **Configure proper retry delays** to avoid overwhelming systems during outages (exponential backoff recommended)
- **Set up monitoring and alerting** for queue sizes, worker health, failed tasks, and retry rates
- **Use environment variables** for configuration (never hardcode credentials)
- **Deploy multiple workers** for high availability and load distribution across queues
- **Use process managers** (systemd, supervisor, Kubernetes) for automatic worker restarts
- **Monitor dead-letter queues** to catch permanently failed tasks and trigger alerts
- **Set appropriate timeouts** to prevent tasks from hanging indefinitely (use `timeout` in TaskConfig)
- **Test thoroughly** before deploying to production (unit tests + integration tests)
- **Use structured logging** with context (task_id, worker_id, queue_name, current_attempt)
- **Enable event streaming** (Redis Pub/Sub) for real-time monitoring and observability
- **Configure process pools** for CPU-bound tasks (`process_pool_size`, `process_pool_max_tasks_per_child`)
- **Set task retention policy** (`keep_completed_tasks=False` by default to save memory)

**Example Production Setup:**

```bash
# Environment variables in production
export ASYNCTASQ_DRIVER=redis
export ASYNCTASQ_REDIS_URL=redis://redis-master:6379
export ASYNCTASQ_REDIS_PASSWORD=${REDIS_PASSWORD}
export ASYNCTASQ_DEFAULT_MAX_ATTEMPTS=5
export ASYNCTASQ_DEFAULT_RETRY_DELAY=120  # 2 minutes
export ASYNCTASQ_DEFAULT_TIMEOUT=300      # 5 minutes

# Event streaming for monitoring (asynctasq-monitor)
export ASYNCTASQ_EVENTS_REDIS_URL=redis://redis-master:6379
export ASYNCTASQ_EVENTS_CHANNEL=asynctasq:events

# Process pool configuration (for CPU-bound tasks)
export ASYNCTASQ_PROCESS_POOL_SIZE=4
export ASYNCTASQ_PROCESS_POOL_MAX_TASKS_PER_CHILD=100

# Multiple worker processes for different priorities
python -m asynctasq worker --queues critical --concurrency 20 &
python -m asynctasq worker --queues default --concurrency 10 &
python -m asynctasq worker --queues low-priority --concurrency 5 &
```

## Monitoring

✅ **Monitor:**

- Queue sizes (alert when queues grow beyond threshold)
- Task processing rate (tasks/second, tasks/minute)
- Worker health (process uptime, memory usage, CPU usage)
- Dead-letter queue size (alert on growth indicating systemic failures)
- Task execution times (p50, p95, p99 percentiles)
- Retry rates (alert on high retry rates indicating external service issues)
- Failed task patterns (group by exception type, queue, task type)
- Worker heartbeat status (detect stale/offline workers)

**Using Event Streaming for Real-Time Monitoring:**

AsyncTasQ integrates with `asynctasq-monitor` via Redis Pub/Sub for real-time observability:

```python
from asynctasq.core.events import create_event_emitter
from asynctasq.core.worker import Worker
from asynctasq.core.driver_factory import DriverFactory
from asynctasq.config import get_global_config

# Worker with event streaming enabled
async def start_worker_with_events():
    config = get_global_config()
    driver = DriverFactory.create_from_config(config)

    # Event emitter publishes to Redis Pub/Sub (asynctasq:events channel)
    emitter = create_event_emitter()  # Reads from ASYNCTASQ_EVENTS_REDIS_URL

    worker = Worker(
        queue_driver=driver,
        queues=['default'],
        event_emitter=emitter,
        worker_id="worker-1",
        heartbeat_interval=60.0  # Send heartbeat every 60s
    )

    try:
        await worker.start()
    finally:
        await emitter.close()
        await driver.disconnect()

# Event consumer for custom monitoring
from asynctasq.core.events import EventSubscriber

async def consume_events():
    subscriber = EventSubscriber(redis_url="redis://localhost:6379")
    await subscriber.connect()

    async for event in subscriber.listen():
        if event.event_type == "task_failed":
            # Alert on critical failures
            await send_alert(f"Task {event.task_id} failed: {event.error}")
        elif event.event_type == "task_completed":
            # Record metrics
            log_metric("task_duration_ms", event.duration_ms)
        elif event.event_type == "worker_heartbeat":
            # Track worker health
            update_worker_status(event.worker_id, active=event.active)
```

**Example Queue Health Check:**

```python
from asynctasq.config import Config
from asynctasq.core.driver_factory import DriverFactory

async def check_queue_health():
    """Check queue health and alert on issues."""
    config = Config.from_env()
    driver = DriverFactory.create_from_config(config)
    await driver.connect()

    try:
        for queue in ['critical', 'default', 'low-priority']:
            stats = await driver.get_queue_stats(queue)
            print(f"Queue '{queue}': {stats.depth} pending, {stats.processing} processing")

            # Alert if queue is too large
            if stats.depth > 1000:
                await send_alert(f"Queue '{queue}' has {stats.depth} tasks")

            # Alert if processing is stuck
            if stats.processing > 0 and stats.depth > 500:
                await send_alert(f"Queue '{queue}' may have stuck workers")
    finally:
        await driver.disconnect()
```
