# Best Practices

## Table of Contents

- [Best Practices](#best-practices)
  - [Table of Contents](#table-of-contents)
  - [Task Design](#task-design)
  - [Queue Organization](#queue-organization)
  - [Error Handling](#error-handling)
  - [Performance](#performance)
  - [Production Deployment](#production-deployment)

## Task Design

✅ **Do:**

- Keep tasks small and focused (single responsibility principle)
- Make tasks idempotent when possible (safe to run multiple times with same result)
- **⚠️ CRITICAL: Set `visibility_timeout` longer than task execution time** - Default is 3600s (1 hour). If your task takes 10 minutes, set it to at least 30 minutes to prevent duplicate processing.
- Use timeouts for long-running tasks to prevent resource exhaustion
- Implement custom `failed()` handlers for cleanup, logging, and alerting
- Use `should_retry()` for intelligent retry logic based on exception type
- Pass ORM models directly as parameters - they're automatically serialized as lightweight references and re-fetched with fresh data when the task executes (Supported ORMs: SQLAlchemy, Django ORM, Tortoise ORM)
- Use type hints on task parameters for better IDE support and documentation
- Name tasks descriptively (class name or function name should explain purpose)
- Use `correlation_id` for distributed tracing and tracking related tasks across systems
- For CPU-bound async tasks (`AsyncProcessTask`), initialize warm event loops in production for better performance (see [Configuration docs](configuration.md#warm-event-loops-for-asyncprocesstask))

❌ **Don't:**

- Include blocking I/O in async tasks (use `SyncTask` with thread pool or `SyncProcessTask` for CPU-bound work)
- Share mutable state between tasks (each task execution should be isolated)
- Perform network calls without timeouts (always use `timeout` parameter)
- Store large objects in task parameters (serialize references instead, e.g., database IDs)
- Use reserved parameter names (`config`, `run`, `execute`, `dispatch`, `failed`, `should_retry`, `on_queue`, `delay`, `retry_after`, `max_attempts`, `timeout`)
- Start parameter names with underscore (reserved for internal use)
- Create new database connections in subprocesses without using proper ORM patterns (see [ORM Integrations](orm-integrations.md) for SQLAlchemy/Django/Tortoise best practices)

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
- **⚠️ Configure visibility_timeout properly** - Default is 3600s (1 hour). Set to (expected_duration × 2) + buffer for each task to prevent duplicate processing on crashes.
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
- **Configure process pools** for CPU-bound tasks (use `ProcessPoolConfig` with `size` and `max_tasks_per_child` options)
- **Set task retention policy** (`keep_completed_tasks=False` by default to save memory)

**Example Production Setup:**

```python
from asynctasq import init, RedisConfig, TaskDefaultsConfig, EventsConfig, ProcessPoolConfig, Worker, DriverFactory, Config

# Option 1: Code configuration
init({
    'driver': 'redis',
    'redis': RedisConfig(
        url='redis://redis-master:6379',
        password='your-redis-password'
    ),
    'task_defaults': TaskDefaultsConfig(
        max_attempts=5,
        retry_delay=120  # 2 minutes
    ),
    # Event streaming for monitoring (asynctasq-monitor)
    'events': EventsConfig(
        enable_event_emitter_redis=True,
        redis_url='redis://redis-master:6379',
        channel='asynctasq:events'
    ),
    # Process pool configuration (for CPU-bound tasks)
    'process_pool': ProcessPoolConfig(
        size=4,
        max_tasks_per_child=100
    )
})

# Option 2: Environment variables (set in your shell/container)
# See environment-variables.md for complete list
# ASYNCTASQ_DRIVER=redis
# ASYNCTASQ_REDIS_URL=redis://redis-master:6379
# ASYNCTASQ_REDIS_PASSWORD=your-redis-password
# ASYNCTASQ_TASK_DEFAULTS_MAX_ATTEMPTS=5
# ASYNCTASQ_EVENTS_ENABLE_EVENT_EMITTER_REDIS=true
init()  # Loads from environment variables

# Option 3: .env file (recommended for production)
# Create a .env file in project root with:
# ASYNCTASQ_DRIVER=redis
# ASYNCTASQ_REDIS_URL=redis://redis-master:6379
# ASYNCTASQ_REDIS_PASSWORD=your-redis-password
# ASYNCTASQ_TASK_DEFAULTS_MAX_ATTEMPTS=5
# ASYNCTASQ_EVENTS_ENABLE_EVENT_EMITTER_REDIS=true
init()  # Automatically loads from .env file

# Option 1: Using CLI (Recommended for production)
# Deploy multiple worker processes using systemd, supervisor, or Kubernetes
# Example:
#   asynctasq worker --queues critical --concurrency 20
#   asynctasq worker --queues default --concurrency 10
#   asynctasq worker --queues low-priority --concurrency 5

# Option 2: Programmatic worker (for custom integrations)
async def run_worker(queues: list[str], concurrency: int):
    """Start a worker programmatically."""
    config = Config.get()
    driver = DriverFactory.create(config.driver, config)

    worker = Worker(
        queue_driver=driver,
        queues=queues,
        concurrency=concurrency
    )

    await worker.start()

# Example: Single worker in async context
import asyncio
await run_worker(["default"], 10)

# For multiple workers, use process managers (systemd/supervisor/K8s) instead of multiprocessing.Process
```

**Deployment Recommendations:**

1. **Use Process Managers** (systemd, supervisor, Kubernetes) to run multiple worker processes - this is the standard production approach
2. **Use CLI** (`asynctasq worker`) for most deployments - it handles all configuration from environment variables
3. **Use multiprocessing** only if you need programmatic control over worker lifecycle in the same Python process

**Example systemd service:**

```ini
[Unit]
Description=AsyncTasQ Worker - Critical Queue
After=network.target redis.service

[Service]
Type=simple
User=asynctasq
WorkingDirectory=/app
Environment="REDIS_URL=redis://redis-master:6379"
Environment="REDIS_PASSWORD=your-password"
ExecStart=/usr/local/bin/asynctasq worker --queues critical --concurrency 20
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```
