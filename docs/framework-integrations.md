# Framework Integrations

## FastAPI Integration

Async Task provides seamless FastAPI integration with automatic lifecycle management and dependency injection.

**Installation:**

```bash
# With uv
uv add "async-task[fastapi]"

# With pip
pip install "async-task[fastapi]"
```

**Requirements:**

- fastapi >= 0.115.0

**Basic Setup:**

```python
from fastapi import FastAPI, Depends
from async_task.integrations.fastapi import AsyncTaskIntegration
from async_task.core.task import task
from async_task.core.dispatcher import Dispatcher
from async_task.drivers.base_driver import BaseDriver

# Auto-configure from environment variables
# ASYNC_TASK_DRIVER=redis
# ASYNC_TASK_REDIS_URL=redis://localhost:6379
async_task = AsyncTaskIntegration()

# Create FastAPI app with async_task lifespan
app = FastAPI(lifespan=async_task.lifespan)

# Define a task
@task(queue='emails')
async def send_email(to: str, subject: str, body: str):
    print(f"Sending email to {to}: {subject}")
    return f"Email sent to {to}"

# Use in endpoint
@app.post("/send-email")
async def send_email_route(to: str, subject: str, body: str):
    task_id = await send_email.dispatch(to=to, subject=subject, body=body)
    return {"task_id": task_id, "status": "queued"}
```

**Explicit Configuration:**

```python
from async_task.config import Config

config = Config(
    driver="redis",
    redis_url="redis://localhost:6379",
    redis_db=1
)
async_task = AsyncTaskIntegration(config=config)
app = FastAPI(lifespan=async_task.lifespan)
```

**Dependency Injection:**

```python
@app.post("/dispatch-task")
async def dispatch_task(
    dispatcher: Dispatcher = Depends(async_task.get_dispatcher)
):
    # Use dispatcher directly
    task_id = await dispatcher.dispatch(my_task)
    return {"task_id": task_id}

@app.get("/queue-stats")
async def get_stats(
    driver: BaseDriver = Depends(async_task.get_driver)
):
    # Access driver for queue inspection
    size = await driver.get_queue_size("default")
    return {"queue": "default", "size": size}
```

**Custom Driver Instance:**

```python
from async_task.drivers.redis_driver import RedisDriver

# Use pre-configured driver
custom_driver = RedisDriver(url='redis://cache-server:6379', db=2)
async_task = AsyncTaskIntegration(driver=custom_driver)
app = FastAPI(lifespan=async_task.lifespan)
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
python -m async_task worker \
    --driver redis \
    --redis-url redis://localhost:6379 \
    --queues default,emails \
    --concurrency 10
```

**Features:**

- Automatic driver connection on startup
- Graceful driver disconnection on shutdown
- Zero-configuration with environment variables
- Dependency injection for dispatcher and driver access
- Works with all drivers (Redis, PostgreSQL, MySQL, RabbitMQ, AWS SQS)
