# Best Practices

## Task Design

✅ **Do:**

- Keep tasks small and focused (single responsibility)
- Make tasks idempotent when possible (safe to run multiple times)
- Use timeouts for long-running tasks
- Implement custom `failed()` handlers for cleanup
- Use `should_retry()` for intelligent retry logic based on exception type
- Pass ORM models directly as parameters - they're automatically serialized as lightweight references and re-fetched with fresh data when the task executes (Supported ORMs: SQLAlchemy, Django ORM, Tortoise ORM)

❌ **Don't:**

- Include blocking I/O in async tasks (use sync tasks with thread pool instead)
- Share mutable state between tasks
- Perform network calls without timeouts
- Store large objects in task parameters

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
python -m async_task_q worker --queues critical --concurrency 20

# Worker 2: Normal tasks
python -m async_task_q worker --queues default --concurrency 10

# Worker 3: Background tasks
python -m async_task_q worker --queues low-priority,batch --concurrency 5
```

## Error Handling

✅ **Do:**

- Log errors comprehensively in `failed()` method
- Use retry limits to prevent infinite loops
- Monitor dead-letter queues regularly
- Implement alerting for critical failures
- Add context to exception messages

```python
class ProcessPayment(Task[bool]):
    async def failed(self, exception: Exception) -> None:
        # Log with context (ensure `logger` is defined/imported in your module)
        logger.error(
            f"Payment failed for user {self.user_id}",
            extra={
                "task_id": self._task_id,
                "attempts": self._attempts,
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

- **Use Redis, PostgreSQL, or MySQL** for production
- **Configure proper retry delays** to avoid overwhelming systems during outages
- **Set up monitoring and alerting** for queue sizes, worker health, failed tasks
- **Use environment variables** for configuration (never hardcode credentials)
- **Deploy multiple workers** for high availability and load distribution
- **Use process managers** (systemd, supervisor, Kubernetes) for automatic restarts
- **Monitor dead-letter queues** to catch permanently failed tasks
- **Set appropriate timeouts** to prevent tasks from hanging indefinitely
- **Test thoroughly** before deploying to production

**Example Production Setup:**

```bash
# Environment variables in production
export async_task_q_DRIVER=redis
export async_task_q_REDIS_URL=redis://redis-master:6379
export async_task_q_REDIS_PASSWORD=${REDIS_PASSWORD}
export async_task_q_DEFAULT_MAX_RETRIES=5
export async_task_q_DEFAULT_RETRY_DELAY=120
export async_task_q_DEFAULT_TIMEOUT=300

# Multiple worker processes
python -m async_task_q worker --queues critical --concurrency 20 &
python -m async_task_q worker --queues default --concurrency 10 &
python -m async_task_q worker --queues low-priority --concurrency 5 &
```

## Monitoring

✅ **Monitor:**

- Queue sizes (alert when queues grow too large)
- Task processing rate (tasks/second)
- Worker health (process uptime, memory usage)
- Dead-letter queue size (alert on growth)
- Task execution times (p50, p95, p99)
- Retry rates (alert on high retry rates)

**Example Monitoring Script:**

```python
from async_task_q.config import Config
from async_task_q.core.driver_factory import DriverFactory

async def check_queue_health():
    config = Config.from_env()
    driver = DriverFactory.create_from_config(config)
    await driver.connect()

    try:
        for queue in ['critical', 'default', 'low-priority']:
            size = await driver.get_queue_size(queue)
            print(f"Queue '{queue}': {size} tasks")

            # Alert if queue is too large
            if size > 1000:
                await send_alert(f"Queue '{queue}' has {size} tasks")
    finally:
        await driver.disconnect()
```
