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

```python
import asynctasq
from asynctasq.core.worker import Worker
from asynctasq.core.driver_factory import DriverFactory

# Initialize AsyncTasQ with configuration
asynctasq.init({
    'driver': 'redis',
    'redis_url': 'redis://redis-master:6379',
    'redis_password': 'your-redis-password',
    'default_max_attempts': 5,
    'default_retry_delay': 120,  # 2 minutes
    'default_timeout': 300,      # 5 minutes
    # Event streaming for monitoring (asynctasq-monitor)
    'enable_event_emitter_redis': True,
    'events_redis_url': 'redis://redis-master:6379',
    'events_channel': 'asynctasq:events',
    # Process pool configuration (for CPU-bound tasks)
    'process_pool_size': 4,
    'process_pool_max_tasks_per_child': 100
})

# Create and start multiple worker processes for different priorities
import asyncio
import multiprocessing

async def run_worker(queues, concurrency):
    config = Config.get()
    driver = DriverFactory.create_from_config(config)

    worker = Worker(
        queue_driver=driver,
        queues=queues,
        concurrency=concurrency
    )

    await worker.start()

def start_worker_process(queues, concurrency):
    asyncio.run(run_worker(queues, concurrency))

# Start multiple worker processes
processes = [
    multiprocessing.Process(target=start_worker_process, args=(["critical"], 20)),
    multiprocessing.Process(target=start_worker_process, args=(["default"], 10)),
    multiprocessing.Process(target=start_worker_process, args=(["low-priority"], 5)),
]

for p in processes:
    p.start()
for p in processes:
    p.join()
```
