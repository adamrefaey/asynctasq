# Framework Integrations

## Table of Contents

- [Framework Integrations](#framework-integrations)
  - [Table of Contents](#table-of-contents)
  - [FastAPI Integration](#fastapi-integration)

## FastAPI Integration

AsyncTasQ provides seamless FastAPI integration with automatic lifecycle management and dependency injection.

**Installation:**

```bash
# With uv
uv add "asynctasq[fastapi]"

# With pip
pip install "asynctasq[fastapi]"
```

**Requirements:**

- fastapi >= 0.109.0

**Basic Setup:**

```python
from fastapi import FastAPI, Depends
from asynctasq import AsyncTasQIntegration, task, Dispatcher
from asynctasq.drivers.base_driver import BaseDriver

# Create AsyncTasQ integration (uses global config or defaults)
asynctasq = AsyncTasQIntegration()

# Create FastAPI app with asynctasq lifespan
app = FastAPI(lifespan=asynctasq.lifespan)

# Define a task
@task(queue='emails')
async def send_email(to: str, subject: str, body: str):
    print(f"Sending email to {to}: {subject}")
    return f"Email sent to {to}"

# Use in endpoint
@app.post("/send-email")
async def send_email_route(to: str, subject: str, body: str):
    task_id = await send_email(to=to, subject=subject, body=body).dispatch()
    return {"task_id": task_id, "status": "queued"}
```

**Note:** `AsyncTasQIntegration` manages its own driver instance and lifecycle. You don't need to call `init()` when using this integration pattern.

**Explicit Configuration:**

```python
from fastapi import FastAPI
from asynctasq import AsyncTasQIntegration, Config, RedisConfig

# Create config with specific settings
config = Config(
    driver="redis",
    redis=RedisConfig(
        url="redis://localhost:6379",
        db=1
    )
)

# Pass config to integration
asynctasq = AsyncTasQIntegration(config=config)
app = FastAPI(lifespan=asynctasq.lifespan)
```

**Dependency Injection:**

```python
@app.post("/dispatch-task")
async def dispatch_task(
    dispatcher: Dispatcher = Depends(asynctasq.get_dispatcher)
):
    # Use dispatcher directly
    task_id = await dispatcher.dispatch(my_task)
    return {"task_id": task_id}

@app.get("/queue-stats")
async def get_stats(
    driver: BaseDriver = Depends(asynctasq.get_driver)
):
    # Access driver for queue inspection
    size = await driver.get_queue_size("default")
    return {"queue": "default", "size": size}
```

**Custom Driver Instance:**

```python
from fastapi import FastAPI
from asynctasq import AsyncTasQIntegration
from asynctasq.drivers.redis_driver import RedisDriver

# Create and configure custom driver instance
custom_driver = RedisDriver(url='redis://cache-server:6379', db=2)

# Pass driver to integration
asynctasq = AsyncTasQIntegration(driver=custom_driver)
app = FastAPI(lifespan=asynctasq.lifespan)
```

**Note:** You don't need to call `connect()` on the driver manually. `AsyncTasQIntegration` handles connection during startup and disconnection during shutdown automatically.

**Alternative Pattern:** For simpler setups without dependency injection, you can use `init()` directly. See [Event Loop Integration](event-loop-integration.md#pattern-3-fastapi-integration-recommended) for this pattern.

**Configuration Priority:**

`AsyncTasQIntegration` uses the following priority order:

1. **Explicit driver instance** - Highest priority (passed via `driver` parameter)
2. **Explicit config** - Medium priority (passed via `config` parameter)
3. **Global config** - Lowest priority (set via `init()`, environment variables, .env file, or defaults to Redis localhost)

```python
# Priority 1: Explicit driver (highest)
custom_driver = RedisDriver(url='redis://prod:6379')
AsyncTasQIntegration(driver=custom_driver)

# Priority 2: Explicit config
config = Config(driver='redis', redis=RedisConfig(url='redis://prod:6379'))
AsyncTasQIntegration(config=config)

# Priority 3: Global config (lowest)
# Option 1: .env file (recommended)
# Create .env with: ASYNCTASQ_DRIVER=redis
init()  # Automatically loads from .env
AsyncTasQIntegration()  # Uses .env-loaded config

# Option 2: Code configuration (for quick testing)
init({'driver': 'redis'})  # Set global config first
AsyncTasQIntegration()      # Uses global config

# For all configuration options, see environment-variables.md
```

**Important Notes:**

- FastAPI integration handles **task dispatching only**
- **Workers must run separately** to process tasks
- Two processes required:
  - **Terminal 1:** FastAPI app (dispatch tasks)
  - **Terminal 2:** Worker (process tasks)

**Example Deployment:**

```bash
# Terminal 1: Start FastAPI app
uvicorn app:app --host 0.0.0.0 --port 8000

# Terminal 2: Start worker
# Configuration loaded from .env file automatically
uv run asynctasq worker --queues default,emails --concurrency 10
```

**Features:**

- Automatic driver connection on startup
- Graceful driver disconnection on shutdown
- Multiple configuration options (explicit config, driver instance, or global config)
- Dependency injection for dispatcher and driver access
- Works with all drivers (Redis, PostgreSQL, MySQL, RabbitMQ, AWS SQS)
