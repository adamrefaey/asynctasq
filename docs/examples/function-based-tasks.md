# Function-Based Tasks: Complete Examples Guide

## Overview

**Prerequisites:**
- AsyncTasQ installed: `uv add asynctasq` or `pip install asynctasq`
- A queue driver configured (Redis, PostgreSQL, MySQL, SQS, or RabbitMQ)
- Workers running to execute tasks (see [Running Workers](#running-workers))

This guide covers **all capabilities** of function-based tasks in AsyncTasQ. Everything you need is documented here - no need to visit other docs.

Function-based tasks allow you to convert any Python function (async or sync) into a background task by simply adding the `@task` decorator. Tasks are automatically serialized, queued, and executed by workers. They provide a simpler, more concise syntax than class-based tasks and are ideal for straightforward task logic.

For conceptual information about task types and execution modes, see [Task Definitions - Task Types and Execution Modes](../task-definitions.md#task-types-and-execution-modes).

**Note:** Examples use `from asynctasq import run` - AsyncTasQ's event loop runner that provides uvloop support with automatic fallback to asyncio.

## Table of Contents

## Four Execution Modes

The `@task` decorator provides **all 4 execution modes** through a combination of function type and the `process` parameter.

**Quick Reference:**

| Mode                 | Function Type | `process=`        | Execution            | Best For                                        |
| -------------------- | ------------- | ----------------- | -------------------- | ----------------------------------------------- |
| **AsyncTask**        | `async def`   | `False` (default) | Event loop           | Async I/O-bound (API calls, async DB queries)   |
| **SyncTask**         | `def`         | `False` (default) | Thread pool          | Sync/blocking I/O (`requests`, sync DB drivers) |
| **AsyncProcessTask** | `async def`   | `True`            | Process pool (async) | Async CPU-intensive work                        |
| **SyncProcessTask**  | `def`         | `True`            | Process pool (sync)  | Sync CPU-intensive work (>80% CPU)              |

For detailed comparison, concurrency details, and when to use each mode, see [Task Definitions - Task Types and Execution Modes](../task-definitions.md#task-types-and-execution-modes).

**Examples:**

```python
from asynctasq import task

# Mode 1: AsyncTask (async I/O-bound) - DEFAULT for async functions
@task
async def fetch_data(url: str):
    async with httpx.AsyncClient() as client:
        return await client.get(url)

# Mode 2: SyncTask (sync I/O-bound) - DEFAULT for sync functions
@task
def fetch_web_page(url: str):
    import requests
    return requests.get(url).text

# Mode 3: AsyncProcessTask (async CPU-intensive)
@task(process=True)
async def process_video_async(path: str):
    async with aiofiles.open(path, 'rb') as f:
        data = await f.read()
    # CPU-intensive processing
    return process_frames(data)

# Mode 4: SyncProcessTask (sync CPU-intensive)
@task(process=True)
def heavy_computation(data: list[float]):
    import numpy as np
    return np.fft.fft(data)  # CPU-intensive
```

**Key Features:**

- **Simple decorator syntax** - Just add `@task` to any function
- **Automatic execution routing** - Framework selects appropriate executor based on function type and `process` flag
- **Full mode coverage** - Access to all 4 execution modes (same as class-based tasks)
- **Flexible configuration** - Queue, retries, timeout, driver, process via decorator or method chaining
- **Method chaining** - Override configuration at dispatch time with fluent API
- **ORM model serialization** - Automatic lightweight references for SQLAlchemy, Django, Tortoise
- **Type-safe** - Full type hints and IDE support
- **Multiple dispatch methods** - Direct dispatch, delayed execution, or method chaining

---

## Basic Usage

### Simple AsyncTasQ

The simplest way to create a task is to add the `@task` decorator to an async function:

```python
import asyncio
from asynctasq import init, task

# Configure the queue driver (see environment-variables.md for details)
init({'driver': 'redis'})  # or init() to load from .env

# Define a simple task
@task
async def send_notification(message: str):
    """Send a notification message."""
    print(f"Notification: {message}")
    await asyncio.sleep(0.1)  # Simulate async work
    return f"Sent: {message}"

# Dispatch the task
async def main():
    task_id = await send_notification(message="Hello, World!").dispatch()
    print(f"Task dispatched with ID: {task_id}")
    # Note: Task will be executed by a worker process

if __name__ == "__main__":
    from asynctasq import run

    run(main())
```

**Important:** After dispatching tasks, you must run a worker process to execute them. Workers continuously poll the queue and execute tasks. See the [Running Workers](#running-workers) section below for details.

### Simple Sync Task

Synchronous functions are automatically executed in a thread pool, so you can use blocking operations without converting to async:

```python
from asynctasq import init, task

# Configure (see environment-variables.md for all options)
init({'driver': 'redis'})  # or init() to load from .env

# Synchronous function (automatically runs in thread pool)
@task
def process_data(data: list[int]) -> int:
    """Process data synchronously."""
    import time
    time.sleep(1)  # Blocking operation is OK in sync tasks
    return sum(data)

# Dispatch
async def main():
    task_id = await process_data(data=[1, 2, 3, 4, 5]).dispatch()
    print(f"Task dispatched: {task_id}")

if __name__ == "__main__":
    from asynctasq import run

    run(main())
```

**Note:** For CPU-intensive work (>80% CPU utilization), add `process=True` to run in process pool:

```python
@task(process=True)  # Runs in ProcessPoolExecutor
def heavy_computation(data: list[float]):
    import numpy as np
    return np.fft.fft(data)  # CPU-intensive work
```

---

## Decorator Syntax

### Without Parentheses (Default Configuration)

```python
from asynctasq import task

@task  # Uses all defaults: queue='default', max_attempts=3, etc.
async def simple_task():
    """Task with default configuration."""
    print("Executing simple task")
```

### With Parentheses (Custom Configuration)

```python
from asynctasq import task

@task(queue='emails', max_attempts=5, retry_delay=120, timeout=30)
async def send_email(to: str, subject: str, body: str):
    """Send an email with custom retry configuration."""
    print(f"Sending email to {to}: {subject}")
    # Email sending logic here
```

---

## Configuration Options

All configuration options can be set via the `@task` decorator. For complete details, see [Task Definitions - Task Configuration](../task-definitions.md#task-configuration).

**Quick Reference:**

### Queue Configuration

Use different queues to organize tasks by priority, type, or processing requirements:

```python
from asynctasq import task

# Different queues for different task types
@task(queue='emails')
async def send_email(to: str, subject: str):
    """Email tasks go to 'emails' queue."""
    pass

@task(queue='payments')
async def process_payment(amount: float, user_id: int):
    """Payment tasks go to 'payments' queue."""
    pass

@task(queue='notifications')
async def send_push_notification(user_id: int, message: str):
    """Notification tasks go to 'notifications' queue."""
    pass
```

**Tips:**

- Run separate workers for different queues to control resource allocation and priority
- Use descriptive queue names that indicate the task type or priority level
- Consider queue naming conventions: `high-priority`, `low-priority`, `critical`, `background`

### Retry Configuration

```python
from asynctasq import task

# High retry count for critical operations
@task(queue='payments', max_attempts=10, retry_delay=30)
async def charge_credit_card(card_id: str, amount: float):
    """Retry up to 10 times with 30 second delays."""
    # Payment processing logic
    pass

# No retries for validation tasks
@task(queue='validation', max_attempts=0)
async def validate_data(data: dict):
    """Don't retry validation failures."""
    # Validation logic
    pass

# Custom retry delay
@task(queue='api-calls', max_attempts=5, retry_delay=300)
async def call_external_api(endpoint: str):
    """Retry with 5 minute delays (for rate-limited APIs)."""
    # API call logic
    pass
```

### Timeout Configuration

```python
from asynctasq import task

# Short timeout for quick operations
@task(queue='quick', timeout=5)
async def quick_operation():
    """Task must complete within 5 seconds."""
    # Fast operation
    pass

# Long timeout for heavy operations
@task(queue='reports', timeout=3600)
async def generate_report(report_id: int):
    """Task can take up to 1 hour."""
    # Report generation logic
    pass

# No timeout (default)
@task(queue='background', timeout=None)
async def background_cleanup():
    """No timeout limit."""
    # Cleanup logic
    pass
```

### Combined Configuration

```python
from asynctasq import task

@task(
    queue='critical',
    max_attempts=10,
    retry_delay=60,
    timeout=300
)
async def critical_operation(data: dict):
    """Fully configured critical task."""
    # Critical operation logic
    pass
```

### Process Pool Configuration

Use `process=True` for CPU-intensive work that requires true multiprocessing (bypasses GIL):

```python
from asynctasq import task

# Async CPU-intensive work
@task(queue='ml-inference', process=True, timeout=300)
async def run_ml_inference(model_path: str, data: list[float]):
    """Async + process=True - runs in subprocess with async support."""
    import aiofiles

    # Async I/O
    async with aiofiles.open(model_path, 'rb') as f:
        model_data = await f.read()

    # CPU-intensive work (bypasses GIL)
    return run_model(model_data, data)

# Sync CPU-intensive work
@task(queue='data-processing', process=True, timeout=600)
def process_large_dataset(data: list[float]):
    """Sync + process=True - runs in subprocess."""
    import numpy as np

    # Heavy CPU computation (bypasses GIL)
    arr = np.array(data)
    result = np.fft.fft(arr)

    return {
        "mean": float(result.mean()),
        "std": float(result.std())
    }
```

**When to use `process=True`:**

✅ CPU utilization > 80% (verified with profiling)
✅ Task duration > 100ms (amortizes process overhead)
✅ All arguments and return values are serializable
✅ Heavy computation: NumPy, Pandas, ML inference, video encoding, encryption

❌ Don't use for I/O-bound tasks (use default `process=False`)
❌ Don't use for short tasks < 100ms (overhead not worth it)
❌ Don't use with unserializable objects (lambdas, file handles, sockets)

---

## Dispatching Tasks

Tasks are dispatched using the unified API where you call the function first (with its parameters) to create a task instance, then call `.dispatch()` on that instance.

**Return Value:** `dispatch()` returns a unique task ID (UUID string) that can be used for tracking, monitoring, and debugging.

**Important Notes:**

- Tasks are dispatched asynchronously and return immediately
- The task ID is generated before the task is queued
- Tasks will not execute until a worker process is running
- Use the task ID to track task status in your monitoring system

### Direct Dispatch (Recommended)

The simplest way to dispatch a task is to call the function with its parameters, then call `.dispatch()`:

```python
from asynctasq import task

@task(queue='emails')
async def send_email(to: str, subject: str, body: str):
    print(f"Sending email to {to}")

# Dispatch immediately
async def main():
    task_id = await send_email(
        to="user@example.com",
        subject="Welcome",
        body="Welcome to our platform!"
    ).dispatch()
    print(f"Task ID: {task_id}")
```

### Dispatch with Delay

You can delay task execution using the `.delay()` method in the chain:

```python
from asynctasq import task

@task(queue='reminders')
async def send_reminder(user_id: int, message: str):
    print(f"Sending reminder to user {user_id}: {message}")

# Dispatch with 60 second delay
async def main():
    # Using method chaining with delay
    task_id = await send_reminder(
        user_id=123,
        message="Don't forget to complete your profile!"
    ).delay(60).dispatch()  # Execute after 60 seconds
```

**Note:** The `delay` parameter specifies seconds until execution. For more complex scheduling, consider using a separate scheduling system.

### Dispatch with Positional Arguments

```python
from asynctasq import task

@task
async def process_items(item1: str, item2: str, item3: str):
    print(f"Processing: {item1}, {item2}, {item3}")

# Dispatch with positional arguments
async def main():
    task_id = await process_items("apple", "banana", "cherry").dispatch()
```

### Dispatch with Mixed Arguments

```python
from asynctasq import task

@task
async def update_user(user_id: int, name: str, email: str, active: bool = True):
    print(f"Updating user {user_id}: {name} ({email}), active={active}")

# Dispatch with mixed positional and keyword arguments
async def main():
    task_id = await update_user(
        123,  # positional
        "John Doe",  # positional
        email="john@example.com",  # keyword
        active=False  # keyword
    ).dispatch()
```

---

## Async vs Sync Functions

The `@task` decorator provides **all 4 execution modes** through a combination of function type and the `process` parameter:

### Execution Mode Selection



**Quick Decision Flow:**

### Mode 1: AsyncTask (Default for async functions)

Use async functions for async I/O-bound operations (API calls, async database queries, async file operations):

```python
from asynctasq import task
import httpx

@task(queue='api')  # process=False is default
async def fetch_user_data(user_id: int):
    """Async function - runs in event loop via AsyncTask."""
    # Can use await for async I/O
    async with httpx.AsyncClient() as client:
        response = await client.get(f"https://api.example.com/users/{user_id}")
        return response.json()
```

**Benefits:**

- Best performance for I/O-bound operations
- Can use `await` for async libraries (httpx, aiohttp, asyncpg, aiofiles)
- More efficient resource usage (no thread overhead)
- Higher concurrency (1000s of tasks)

### Mode 2: SyncTask (Default for sync functions)

Use sync functions for sync/blocking I/O operations:

```python
from asynctasq import task
import requests

@task(queue='web-scraping')  # process=False is default
def fetch_web_page(url: str) -> str:
    """Sync function - automatically runs in thread pool via SyncTask."""
    # Blocking operations OK - runs in thread pool
    response = requests.get(url)
    return response.text
```

**Benefits:**

- No need to convert blocking code to async
- Automatic thread pool execution (managed by framework)
- Works with any synchronous library (`requests`, `psycopg2`, etc.)

### Mode 3: AsyncProcessTask (Async + `process=True`)

Use async functions with `process=True` for CPU-intensive work that also needs async I/O:

```python
from asynctasq import task
import aiofiles

@task(queue='video-processing', process=True)  # AsyncProcessTask
async def process_video_async(video_path: str) -> dict:
    """Async + process=True - runs in subprocess with asyncio.run()."""
    # Async I/O
    async with aiofiles.open(video_path, 'rb') as f:
        data = await f.read()

    # CPU-intensive work (bypasses GIL in subprocess)
    frames_processed = await process_frames(data)

    return {"frames": frames_processed}
```

**Benefits:**

- True multi-core parallelism (bypasses GIL)
- Async I/O support within subprocess
- Best for ML inference with async preprocessing

**Important:** All arguments and return values must be serializable.

### Mode 4: SyncProcessTask (Sync + `process=True`)

Use sync functions with `process=True` for heavy CPU-intensive work:

```python
from asynctasq import task
import numpy as np

@task(queue='data-processing', process=True, timeout=600)  # SyncProcessTask
def process_large_dataset(data: list[float]) -> dict:
    """Sync + process=True - runs in subprocess via ProcessPoolExecutor."""
    # Heavy CPU computation (bypasses GIL)
    arr = np.array(data)
    result = np.fft.fft(arr)

    return {
        "mean": float(result.mean()),
        "std": float(result.std())
    }
```

**Benefits:**

- True multi-core parallelism (bypasses GIL)
- Best performance for CPU-intensive workloads (>80% CPU)
- Each process has independent interpreter and memory

**Limitations:**

- All arguments and return values must be serializable (no lambdas, file handles, sockets)
- Higher memory footprint (~50MB+ per process)
- Higher startup overhead (~50ms per task)

### Choosing the Right Mode

**Decision Flow:**

1. **Is your work CPU-intensive (>80% CPU)?**
   - Yes → Use `process=True` (Mode 3 or 4)
   - No → Use `process=False` (Mode 1 or 2)

2. **Do you need async I/O?**
   - Yes → Use `async def` (Mode 1 or 3)
   - No → Use `def` (Mode 2 or 4)

**Examples:**

```python
from asynctasq import task

# ✅ Mode 1: Async I/O-bound (default)
@task
async def fetch_data(url: str):
    async with httpx.AsyncClient() as client:
        return await client.get(url)

# ✅ Mode 2: Sync I/O-bound (default)
@task
def scrape_page(url: str):
    import requests
    return requests.get(url).text

# ✅ Mode 3: Async CPU-intensive
@task(process=True)
async def ml_inference_async(data: list[float]):
    # Async preprocessing
    async with aiofiles.open('model.pkl', 'rb') as f:
        model_data = await f.read()
    # CPU-intensive work
    return run_model(model_data, data)

# ✅ Mode 4: Sync CPU-intensive
@task(process=True)
def heavy_math(matrix: list[list[float]]):
    import numpy as np
    return np.linalg.inv(np.array(matrix)).tolist()
```

### Mixed Async/Sync in Same Application

```python
from asynctasq import task
import asyncio
import time

# Async task
@task(queue='asynctasqs')
async def async_operation(data: str):
    await asyncio.sleep(0.1)
    return f"Processed: {data}"

# Sync task
@task(queue='sync-tasks')
def sync_operation(data: str):
    time.sleep(1)
    return f"Computed: {data}"

# Both can be dispatched the same way
async def main():
    task1_id = await async_operation(data="async").dispatch()
    task2_id = await sync_operation(data="sync").dispatch()
```

---

## Driver Overrides

### Per-Task Driver Override (String)

```python
from asynctasq import init, task

# Global config uses redis driver
init({'driver': 'redis'})

# This task uses Redis regardless of global config
@task(queue='critical', driver='redis')
async def critical_task(data: dict):
    """Always uses Redis driver."""
    print(f"Processing critical task: {data}")

# This task uses SQS
@task(queue='aws-tasks', driver='sqs')
async def aws_task(region: str):
    """Always uses SQS driver."""
    print(f"Processing AWS task in {region}")

# This task uses global config (redis)
@task(queue='normal')
async def normal_task(data: str):
    """Uses global config driver."""
    print(f"Processing normal task: {data}")
```

### Per-Task Driver Override (Driver Instance)

You can also pass a driver instance directly for complete control over driver configuration:

```python
from asynctasq import task
from asynctasq.drivers.redis_driver import RedisDriver

# Create a custom driver instance with specific configuration
custom_redis = RedisDriver(
    url='redis://custom-host:6379',
    password='secret',
    db=1,
    max_connections=20
)

# Use the custom driver instance
@task(queue='custom', driver=custom_redis)
async def custom_driver_task(data: dict):
    """Uses the custom Redis driver instance."""
    print(f"Using custom driver: {data}")

# Dispatch task
async def main():
    task_id = await custom_driver_task(data={"key": "value"}).dispatch()
    print(f"Task dispatched: {task_id}")
```

**Important Notes:**

- When using a driver instance, the driver is shared across all tasks using it
- For per-task isolation, use string-based driver selection instead
- Driver instances are cached and reused, so creating multiple instances with the same configuration is inefficient
- Ensure driver instances are properly initialized before task dispatch

### Multiple Drivers in Same Application

```python
from asynctasq import init, task

# Default driver
init({'driver': 'redis'})

# Tasks using different drivers
@task(queue='redis-queue', driver='redis')
async def redis_task(data: str):
    pass

@task(queue='postgres-queue', driver='postgres')
async def postgres_task(data: str):
    pass

@task(queue='sqs-queue', driver='sqs')
async def sqs_task(data: str):
    pass

@task(queue='default-queue')  # Uses global config (redis)
async def redis_task(data: str):
    pass
```

---

## ORM Integration

### SQLAlchemy Integration

**Important:** SQLAlchemy models are automatically detected and serialized as lightweight references. Only the primary key is stored in the queue, and models are fetched fresh from the database when the task executes.

**Configuration:** Set a session factory on your Base class - workers will automatically create sessions as needed.

```python
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from asynctasq import task

# Define models
class Base(DeclarativeBase):
    pass

class User(Base):
    __tablename__ = 'users'
    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str]
    name: Mapped[str]

class Order(Base):
    __tablename__ = 'orders'
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int]
    total: Mapped[float]

# Setup SQLAlchemy
engine = create_async_engine(
    'postgresql+asyncpg://user:pass@localhost/db',
    pool_pre_ping=True,  # Verify connections are alive
    pool_recycle=3600,   # Recycle connections after 1 hour
)
async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

# Configure session factory - one line! Workers create sessions automatically
Base._asynctasq_session_factory = async_session

# For multiprocessing workers, use NullPool instead:
# from sqlalchemy.pool import NullPool
# engine = create_async_engine(dsn, poolclass=NullPool, pool_pre_ping=True)
# async_session = async_sessionmaker(engine, expire_on_commit=False)
# Base._asynctasq_session_factory = async_session

# Task with ORM model parameter
@task(queue='emails')
async def send_welcome_email(user: User):
    """User is automatically serialized as reference and fetched fresh."""
    print(f"Sending welcome email to {user.email} (ID: {user.id})")
    # User data is fresh from database when task executes

@task(queue='orders')
async def process_order(order: Order, user: User):
    """Multiple ORM models supported."""
    print(f"Processing order {order.id} for user {user.name}")
    # Both models are fetched fresh in parallel

# Dispatch tasks
async def main():
    async with async_session() as session:
        # Fetch user
        user = await session.get(User, 1)

        # Only user.id is serialized to queue (90%+ payload reduction)
        task_id = await send_welcome_email(user=user).dispatch()

        # Multiple models
        order = await session.get(Order, 100)
        task_id = await process_order(order=order, user=user).dispatch()
```

**Important Notes:**

- **Simpler than context variables** - One line on Base class vs. per-model configuration
- **Worker-friendly** - Workers automatically create sessions from factory when fetching models
- Models are fetched fresh from the database when the task executes, ensuring data consistency
- Only the primary key is serialized, reducing queue payload size by 90%+ for large models
- Multiple models in the same task are fetched in parallel for efficiency
- **Multiprocessing Note:** For workers using process pools (`process=True` tasks), use `NullPool` to avoid connection sharing issues (see commented code above)

**Complete ORM Setup Guide:** For detailed SQLAlchemy, Django, and Tortoise ORM setup including session factories, connection pools, and advanced patterns, see [ORM Integrations](../orm-integrations.md).

### Django ORM Integration

```python
from django.db import models
from asynctasq import task

# Define Django model
class User(models.Model):
    email = models.EmailField()
    name = models.CharField(max_length=100)

class Product(models.Model):
    name = models.CharField(max_length=200)
    price = models.DecimalField(max_digits=10, decimal_places=2)

# Task with Django model
@task(queue='emails')
async def send_welcome_email(user: User):
    """Django model automatically serialized as reference."""
    print(f"Sending welcome email to {user.email}")

@task(queue='products')
async def update_product_price(product: Product, new_price: float):
    """Django model with additional parameters."""
    print(f"Updating {product.name} to ${new_price}")

# Dispatch tasks
async def main():
    # Django async methods (Django 3.1+)
    user = await User.objects.aget(id=1)
    await send_welcome_email(user=user).dispatch()

    product = await Product.objects.aget(id=5)
    await update_product_price(product=product, new_price=99.99).dispatch()
```

### Tortoise ORM Integration

```python
from tortoise import fields
from tortoise.models import Model
from asynctasq import task

# Define Tortoise model
class User(Model):
    id = fields.IntField(pk=True)
    email = fields.CharField(max_length=255)
    name = fields.CharField(max_length=100)

class Post(Model):
    id = fields.IntField(pk=True)
    title = fields.CharField(max_length=200)
    author = fields.ForeignKeyField('models.User', related_name='posts')

# Task with Tortoise model
@task(queue='notifications')
async def notify_new_post(post: Post, author: User):
    """Tortoise models automatically serialized as references."""
    print(f"New post '{post.title}' by {author.name}")

# Dispatch tasks
async def main():
    # Tortoise async methods
    user = await User.get(id=1)
    post = await Post.get(id=10)

    await notify_new_post(post=post, author=user).dispatch()
```

---

## Method Chaining

Method chaining allows you to override task configuration at dispatch time. This is useful when you need different settings for specific dispatches without creating separate task functions.

**Available Chain Methods:**

- `.on_queue(queue_name)`: Override the queue name
- `.delay(seconds)`: Add execution delay (in seconds)
- `.retry_after(seconds)`: Override retry delay (in seconds)
- `.max_attempts(attempts)`: Override maximum retry attempts
- `.timeout(seconds)`: Override task execution timeout
- `.visibility_timeout(seconds)`: Override visibility timeout for crash recovery
- `.dispatch()`: Final method that actually dispatches the task

**Important:** Method chaining requires calling the function first (with arguments) to create a task instance, then chaining configuration methods. The function call returns a task instance that supports chaining.

**Syntax Pattern:**

```python
await task_function(arg1, arg2).on_queue("queue").delay(60).dispatch()
#      ^^^^^^^^^^^^^^^^^^^^^^^^  ^^^^^^^^^^^^^^^^^^^^^^^^^^^^
#      Function call (creates instance)  Chain methods
```

### Basic Method Chaining

```python
from asynctasq import task

@task(queue='default')
async def process_data(data: str):
    print(f"Processing: {data}")

# Chain delay and dispatch
async def main():
    # Call function with args, then chain methods
    task_id = await process_data("data").delay(60).dispatch()
    # Task will execute after 60 seconds
```

### Queue Override with Chaining

```python
from asynctasq import task

@task(queue='default')
async def send_notification(message: str):
    print(f"Notification: {message}")

# Override queue at dispatch time
async def main():
    # Send to high-priority queue
    task_id = await send_notification("urgent").on_queue("high-priority").dispatch()

    # Send to low-priority queue with delay
    task_id = await send_notification("reminder").on_queue("low-priority").delay(300).dispatch()
```

### Retry Configuration with Chaining

Override the retry delay for specific dispatches:

```python
from asynctasq import task

@task(queue='api', max_attempts=3, retry_delay=60)
async def call_api(endpoint: str):
    print(f"Calling {endpoint}")

# Override retry delay at dispatch time
async def main():
    # Use custom retry delay for this specific dispatch
    # This only affects the delay between retries, not max_attempts
    task_id = await call_api("https://api.example.com/data") \
        .retry_after(120) \
        .dispatch()
    # Will retry with 120 second delays instead of default 60
```

### Complex Chaining

```python
from asynctasq import task

@task(queue='default')
async def complex_task(data: dict):
    print(f"Processing: {data}")

# Chain multiple configuration methods
async def main():
    task_id = await complex_task({"key": "value"}) \
        .on_queue("critical") \
        .retry_after(180) \
        .delay(30) \
        .dispatch()
    # Queued on 'critical' queue, 30s delay, 180s retry delay
```

### Override All Configuration at Dispatch Time

```python
from asynctasq import task

@task(queue='default', max_attempts=3, timeout=60)
async def flexible_task(data: str):
    print(f"Processing: {data}")

# Override ALL configuration at dispatch time
async def main():
    task_id = await flexible_task("data") \
        .on_queue("high-priority") \
        .max_attempts(10) \
        .timeout(120) \
        .retry_after(30) \
        .visibility_timeout(600) \
        .delay(60) \
        .dispatch()
    # All decorator values overridden!
```

**Note:** Method chaining allows you to override ANY configuration parameter at dispatch time, including those set in the decorator. This provides maximum flexibility for different execution scenarios.

---

## Beautiful Console Output

AsyncTasQ provides a beautiful Rich-enhanced `print()` function for task output with automatic syntax highlighting, colorization, and Rich markup support.

### Why Use `asynctasq.print()`?

- **Automatic syntax highlighting** for code, JSON, dicts, lists
- **Colorized output** with Rich markup (`[bold]`, `[red]`, `[cyan]`, etc.)
- **Beautiful formatting** for complex data structures
- **Tables, panels, and other Rich renderables**
- **Drop-in replacement** for built-in `print()`

### Basic Usage

```python
from asynctasq import task, print

@task(queue='notifications')
async def send_notification(user_id: int, message: str):
    """Send notification with beautiful console output."""
    print(f"[cyan]Sending notification to user[/cyan] [yellow]{user_id}[/yellow]")
    print(f"[bold]Message:[/bold] {message}")

    # Automatic JSON formatting
    data = {"user_id": user_id, "message": message, "sent_at": "2026-01-01"}
    print(data)  # Pretty-printed with syntax highlighting

    return f"Sent to user {user_id}"
```

### Available Rich Markup Tags

Common markup tags you can use in strings:

| Markup                    | Effect                         | Example                                          |
| ------------------------- | ------------------------------ | ------------------------------------------------ |
| `[bold]text[/bold]`       | Bold text                      | `print("[bold]Important![/bold]")`               |
| `[italic]text[/italic]`   | Italic text                    | `print("[italic]Note:[/italic] details")`        |
| `[red]text[/red]`         | Red text                       | `print("[red]Error![/red]")`                     |
| `[green]text[/green]`     | Green text                     | `print("[green]Success![/green]")`               |
| `[yellow]text[/yellow]`   | Yellow text                    | `print("[yellow]Warning[/yellow]")`              |
| `[blue]text[/blue]`       | Blue text                      | `print("[blue]Info[/blue]")`                     |
| `[cyan]text[/cyan]`       | Cyan text                      | `print("[cyan]Processing...[/cyan]")`            |
| `[magenta]text[/magenta]` | Magenta text                   | `print("[magenta]Debug[/magenta]")`              |
| `[bold red]text[/]`       | Combined styles (bold + color) | `print("[bold red]Critical Error![/]")`          |
| `[link=url]text[/link]`   | Clickable link                 | `print("[link=https://example.com]Link[/link]")` |

### Rich Console Features

You can also use Rich's advanced features:

```python
from asynctasq import task, print
from asynctasq.utils.console import Table, Panel, Syntax, console

@task(queue='reports')
async def generate_report(data: list[dict]):
    """Generate report with rich formatting."""

    # Tables
    table = Table(title="User Report")
    table.add_column("ID", style="cyan")
    table.add_column("Name", style="green")
    table.add_column("Email", style="yellow")

    for user in data:
        table.add_row(str(user["id"]), user["name"], user["email"])

    console.print(table)

    # Panels
    console.print(Panel(
        "[bold green]Report Generated Successfully![/bold green]",
        title="Status",
        border_style="green"
    ))

    # Syntax highlighting for code
    code = '''
    def hello():
        print("Hello, World!")
    '''
    syntax = Syntax(code, "python", theme="monokai", line_numbers=True)
    console.print(syntax)

    return "Report complete"
```

### Examples in Tasks

```python
from asynctasq import task, print
import asyncio
import time

@task(queue='emails')
async def send_email(to: str, subject: str, body: str):
    """Send email with beautiful output."""
    print("[cyan]📧 Email Service[/cyan]")
    print(f"[bold]To:[/bold] [yellow]{to}[/yellow]")
    print(f"[bold]Subject:[/bold] {subject}")
    print("[green]✓ Email sent successfully[/green]")
    return f"Sent to {to}"

@task(queue='payments')
async def process_payment(user_id: int, amount: float, currency: str):
    """Process payment with status indicators."""
    print(f"[cyan]💳 Processing payment for user[/cyan] [yellow]{user_id}[/yellow]")
    print(f"[bold]Amount:[/bold] {amount} {currency}")

    # Simulate payment processing
    await asyncio.sleep(1)

    # Success message
    print("[bold green]✓ Payment processed successfully![/bold green]")
    return {"status": "completed", "user_id": user_id, "amount": amount}

@task(queue='data-processing', process=True)
def process_large_dataset(dataset_id: int):
    """Process dataset with progress indication."""
    print(f"[cyan]📊 Processing dataset[/cyan] [yellow]{dataset_id}[/yellow]")

    # Simulate processing steps
    steps = ["Loading data", "Validating", "Transforming", "Saving results"]

    for i, step in enumerate(steps, 1):
        print(f"[dim]Step {i}/{len(steps)}:[/dim] {step}")
        time.sleep(0.5)

    print("[bold green]✓ Dataset processed successfully![/bold green]")
    return {"dataset_id": dataset_id, "records": 1000}
```

**Note:** Rich output works seamlessly in both local development and production environments. In environments without TTY support (like CI/CD), Rich automatically falls back to plain text output.

---

## Lifecycle Hooks

Tasks support lifecycle hooks for custom error handling and cleanup logic. These are optional methods you can define within your task function to customize behavior.

### `should_retry(exception: Exception) -> bool`

**Note:** This is a method on the task instance, not directly accessible in function-based tasks. For function-based tasks with custom retry logic, consider using class-based tasks instead or handle errors within your function.

For most use cases, the automatic retry mechanism with `max_attempts` and `retry_delay` is sufficient:

```python
from asynctasq import task
import httpx

@task(queue='api', max_attempts=5, retry_delay=60)
async def call_external_api(url: str):
    """Call external API with automatic retries."""
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(url, timeout=10.0)
            response.raise_for_status()
            return response.json()
    except httpx.HTTPError as e:
        print(f"[red]API call failed: {e}[/red]")
        # Re-raise to trigger automatic retry mechanism
        raise

# Task will automatically retry up to 5 times with 60 second delays
# For custom retry logic based on exception type, use class-based tasks
```

### Error Handling Best Practices

```python
from asynctasq import task, print
import httpx

@task(queue='webhooks', max_attempts=5, retry_delay=120)
async def deliver_webhook(url: str, payload: dict):
    """Deliver webhook with error handling."""
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(url, json=payload, timeout=10.0)
            response.raise_for_status()

            print(f"[green]✓ Webhook delivered to {url}[/green]")
            return {"status": "delivered", "status_code": response.status_code}

    except httpx.HTTPStatusError as e:
        status = e.response.status_code

        # Log different error types
        if 400 <= status < 500:
            print(f"[yellow]Client error {status} for {url}[/yellow]")
        elif 500 <= status < 600:
            print(f"[red]Server error {status} for {url}, will retry[/red]")

        # Re-raise to trigger retry
        raise

    except (httpx.ConnectError, httpx.TimeoutException) as e:
        print(f"[red]Network error for {url}: {e}[/red]")
        raise

    except Exception as e:
        print(f"[bold red]Unexpected error for {url}: {e}[/bold red]")
        raise

# Framework automatically retries on exception up to max_attempts
```

---

## Real-World Examples

### Email Sending Service

```python
import asyncio
from asynctasq import task, run
from typing import Optional

@task(queue='emails', max_attempts=5, retry_delay=60, timeout=30)
async def send_email(
    to: str,
    subject: str,
    body: str,
    from_email: Optional[str] = None
):
    """Send an email with retry logic."""
    # Email sending logic here
    print(f"Sending email to {to}: {subject}")
    # Simulate email sending
    await asyncio.sleep(0.5)
    return {"status": "sent", "to": to}

# Dispatch emails
async def main():
    # Immediate email
    await send_email(
        to="user@example.com",
        subject="Welcome!",
        body="Welcome to our platform"
    ).dispatch()

    # Delayed welcome email (send after 1 hour)
    await send_email(
        to="newuser@example.com",
        subject="Getting Started",
        body="Here's how to get started..."
    ).delay(3600).dispatch()

if __name__ == "__main__":
    run(main())
```

### Payment Processing

```python
import asyncio
from asynctasq import task, run
from decimal import Decimal

@task(
    queue='payments',
    max_attempts=10,
    retry_delay=30,
    timeout=60
)
async def process_payment(
    user_id: int,
    amount: Decimal,
    payment_method: str,
    order_id: int
):
    """Process payment with high retry count for reliability."""
    print(f"Processing payment: ${amount} for user {user_id}")
    # Payment processing logic
    # - Validate payment method
    # - Charge card
    # - Update order status
    # - Send confirmation
    return {"status": "completed", "order_id": order_id}

# Dispatch payment
async def main():
    task_id = await process_payment(
        user_id=123,
        amount=Decimal("99.99"),
        payment_method="credit_card",
        order_id=456
    ).dispatch()
    print(f"Payment task dispatched: {task_id}")

if __name__ == "__main__":
    run(main())
```

### Report Generation

```python
import asyncio
from asynctasq import task, run
from datetime import datetime, timedelta

@task(queue='reports', timeout=3600)  # 1 hour timeout
def generate_report(
    report_type: str,
    start_date: datetime,
    end_date: datetime,
    user_id: int
):
    """Generate report synchronously (CPU-intensive)."""
    import time
    print(f"Generating {report_type} report for user {user_id}")
    # Heavy computation
    time.sleep(10)
    return {
        "report_type": report_type,
        "generated_at": datetime.now().isoformat(),
        "user_id": user_id
    }

# Schedule report generation
async def main():
    # Generate report for last month
    end_date = datetime.now()
    start_date = end_date - timedelta(days=30)

    task_id = await generate_report(
        report_type="monthly_sales",
        start_date=start_date,
        end_date=end_date,
        user_id=123
    ).dispatch()
    print(f"Report generation task dispatched: {task_id}")

if __name__ == "__main__":
    run(main())
```

### Image Processing

```python
import asyncio
from asynctasq import task, run
from pathlib import Path

@task(queue='images', max_attempts=3, timeout=300)
async def process_image(
    image_path: str,
    operations: list[str],
    output_path: str
):
    """Process image with various operations."""
    print(f"Processing image: {image_path}")
    # Image processing logic
    # - Resize
    # - Apply filters
    # - Optimize
    # - Save to output_path
    await asyncio.sleep(2)
    return {"output": output_path, "operations": operations}

# Dispatch image processing
async def main():
    task_id = await process_image(
        image_path="/uploads/photo.jpg",
        operations=["resize", "optimize", "watermark"],
        output_path="/processed/photo.jpg"
    ).dispatch()
    print(f"Image processing task dispatched: {task_id}")

if __name__ == "__main__":
    run(main())
```

### Webhook Delivery

```python
import asyncio
from asynctasq import task, run
import httpx

@task(
    queue='webhooks',
    max_attempts=5,
    retry_delay=120,
    timeout=10
)
async def deliver_webhook(
    url: str,
    payload: dict,
    headers: dict
):
    """Deliver webhook with retry logic."""
    async with httpx.AsyncClient() as client:
        response = await client.post(
            url,
            json=payload,
            headers=headers,
            timeout=10.0
        )
        response.raise_for_status()
        return {"status_code": response.status_code}

# Dispatch webhook
async def main():
    task_id = await deliver_webhook(
        url="https://example.com/webhook",
        payload={"event": "user.created", "user_id": 123},
        headers={"X-API-Key": "secret"}
    ).dispatch()
    print(f"Webhook task dispatched: {task_id}")

if __name__ == "__main__":
    run(main())
```

### Data Synchronization

```python
import asyncio
from asynctasq import task, run

@task(queue='sync', max_attempts=3, retry_delay=300)
async def sync_user_data(
    user_id: int,
    source_system: str,
    target_system: str
):
    """Sync user data between systems."""
    print(f"Syncing user {user_id} from {source_system} to {target_system}")
    # Data synchronization logic
    # - Fetch from source
    # - Transform data
    # - Push to target
    return {"synced": True, "user_id": user_id}

# Schedule sync with delay
async def main():
    # Sync after 5 minutes
    task_id = await sync_user_data(
        user_id=123,
        source_system="crm",
        target_system="analytics"
    ).delay(300).dispatch()
    print(f"Sync task dispatched: {task_id}")

if __name__ == "__main__":
    run(main())
```

### Batch Processing

Process multiple items in a single task:

```python
import asyncio
from asynctasq import task, run
from typing import List

@task(queue='batch', timeout=1800)  # 30 minutes timeout
async def process_batch(
    items: List[dict],
    batch_id: str
):
    """Process a batch of items."""
    print(f"Processing batch {batch_id} with {len(items)} items")
    results = []
    for item in items:
        # Process each item
        result = await process_item(item)
        results.append(result)
    return {"batch_id": batch_id, "processed": len(results)}

async def process_item(item: dict):
    """Helper function to process individual item."""
    await asyncio.sleep(0.1)
    return {"item_id": item.get("id"), "status": "processed"}

# Dispatch batch processing
async def main():
    items = [
        {"id": 1, "data": "value1"},
        {"id": 2, "data": "value2"},
        {"id": 3, "data": "value3"},
    ]

    task_id = await process_batch(
        items=items,
        batch_id="batch-2024-01-15"
    ).dispatch()
    print(f"Batch processing task dispatched: {task_id}")

if __name__ == "__main__":
    run(main())
```

**Tip:** For very large batches, consider splitting into smaller batches or processing items individually as separate tasks for better parallelism and error isolation.

---

## Complete Working Example

**Complete Working Example:**

Here's a complete, runnable example demonstrating multiple function-based task patterns:

- Different task configurations (queue, retries, timeout)
- Async and sync functions
- Direct dispatch and method chaining
- Driver overrides (commented - requires Redis)
- Delayed execution
- Beautiful console output with Rich

```python
import asyncio
from asynctasq import init, task, run, print

# Configuration (see environment-variables.md)
init({'driver': 'redis'})  # or init() to load from .env

# Define tasks with different configurations
@task(queue='emails', max_attempts=3, retry_delay=60)
async def send_email(to: str, subject: str, body: str):
    """Send an email."""
    print(f"📧 Sending email to {to}: {subject}")
    await asyncio.sleep(0.1)
    return f"Email sent to {to}"

@task(queue='payments', max_attempts=10, retry_delay=30, timeout=60)
async def process_payment(user_id: int, amount: float):
    """Process a payment."""
    print(f"💳 Processing payment: ${amount} for user {user_id}")
    await asyncio.sleep(0.2)
    return {"status": "completed", "user_id": user_id}

@task(queue='reports', timeout=300)
def generate_report(report_id: int):
    """Generate a report (sync function)."""
    import time
    print(f"📊 Generating report {report_id}")
    time.sleep(1)
    return f"Report {report_id} generated"

@task(driver='redis')  # Override driver (requires Redis configured)
async def critical_task(data: dict):
    """Critical task using Redis."""
    print(f"🚨 Critical task: {data}")
    await asyncio.sleep(0.1)

# Main function demonstrating all dispatch methods
async def main():
    print("=== Function-Based Tasks Examples ===\n")

    # 1. Direct dispatch
    print("1. Direct dispatch:")
    task_id = await send_email(
        to="user@example.com",
        subject="Welcome",
        body="Welcome!"
    ).dispatch()
    print(f"   Task ID: {task_id}\n")

    # 2. Dispatch with delay
    print("2. Dispatch with delay:")
    task_id = await send_email(
        to="user@example.com",
        subject="Reminder",
        body="Don't forget!"
    ).delay(60).dispatch()
    print(f"   Task ID: {task_id} (will execute in 60s)\n")

    # 3. Method chaining
    print("3. Method chaining:")
    task_id = await send_email("user@example.com", "Chained", "Message") \
        .delay(30) \
        .dispatch()
    print(f"   Task ID: {task_id}\n")

    # 4. Payment processing
    print("4. Payment processing:")
    task_id = await process_payment(user_id=123, amount=99.99).dispatch()
    print(f"   Task ID: {task_id}\n")

    # 5. Sync task
    print("5. Sync task:")
    task_id = await generate_report(report_id=1).dispatch()
    print(f"   Task ID: {task_id}\n")

    # 6. Driver override
    print("6. Driver override:")
    # Note: This requires Redis to be configured
    # task_id = await critical_task(data={"key": "value"}).dispatch()
    # print(f"   Task ID: {task_id}\n")

    print("=== All tasks dispatched! ===")
    print("Note: Run workers to process these tasks. See the 'Running Workers' section above.")

if __name__ == "__main__":
    run(main())
```

---

## Summary

Function-based tasks provide the simplest way to create background tasks in AsyncTasQ. This guide covered everything you need:

### Key Features

✅ **Simple syntax** - Just add `@task` decorator to any function
✅ **All 4 execution modes** - Async/sync × I/O-bound/CPU-bound via function type + `process` flag
✅ **Flexible configuration** - Queue, retries, timeout, driver, visibility_timeout via decorator
✅ **Multiple dispatch methods** - Direct dispatch, delayed execution, method chaining
✅ **Complete override capability** - All decorator settings can be overridden at dispatch time
✅ **ORM integration** - Automatic serialization for SQLAlchemy, Django, Tortoise (90%+ payload reduction)
✅ **Driver overrides** - Per-task driver selection (string or instance)
✅ **Beautiful console output** - Rich-enhanced print() with colors, tables, and formatting
✅ **Error handling** - Automatic retries with configurable attempts and delays
✅ **Type safety** - Full type hints and IDE support
✅ **Production-ready** - Multiple queue drivers, monitoring, graceful shutdown

### Complete Checklist

To use function-based tasks, you need:

1. ✅ **Install AsyncTasQ** with desired driver:
   ```bash
   uv add "asynctasq[redis]"  # or postgres, mysql, sqs, rabbitmq
   ```

2. ✅ **Configure driver** in your application (choose one method):
   ```python
   from asynctasq import init
   # Option 1: .env file (recommended)
   # Create .env with: ASYNCTASQ_DRIVER=redis
   # Configuration (see environment-variables.md)
   init()  # Loads from .env or environment variables
   ```

3. ✅ **Define tasks** with `@task` decorator:
   ```python
   from asynctasq import task

   @task(queue='emails', max_attempts=5)
   async def send_email(to: str, subject: str):
       print(f"Sending email to {to}")
   ```

4. ✅ **Dispatch tasks** in your application:
   ```python
   task_id = await send_email(to="user@example.com", subject="Hello").dispatch()
   ```

5. ✅ **Run workers** to execute tasks:
   ```bash
   # Configuration loaded from .env automatically
   uv run asynctasq worker --queues emails --concurrency 20
   ```

### Quick Start

1. **Install with your preferred driver:**
   ```bash
   uv add "asynctasq[redis]"
   ```

2. **Configure in your app (choose one method):**
   ```python
   from asynctasq import init

   # Configuration (see environment-variables.md for all options)
   init()  # Loads from .env or environment variables
   # For quick testing: init({'driver': 'redis'})
   ```

3. **Define a task:**
   ```python
   from asynctasq import task, print

   @task(queue='emails')
   async def send_email(to: str, subject: str):
       print(f"[cyan]Sending email to[/cyan] [yellow]{to}[/yellow]")
       return f"Sent: {subject}"
   ```

4. **Dispatch it:**
   ```python
   task_id = await send_email(to="user@example.com", subject="Hello").dispatch()
   ```

5. **Run workers:**
   ```bash
   # Configuration loaded from .env automatically
   uv run asynctasq worker --queues emails
   ```

### Configuration Reference

**@task Decorator Parameters:**

| Parameter            | Type                        | Default     | Description                                   |
| -------------------- | --------------------------- | ----------- | --------------------------------------------- |
| `queue`              | `str`                       | `"default"` | Queue name for task execution                 |
| `max_attempts`       | `int`                       | `3`         | Maximum retry attempts on failure             |
| `retry_delay`        | `int`                       | `60`        | Seconds to wait between retry attempts        |
| `timeout`            | `int \| None`               | `None`      | Task timeout in seconds (`None` = no timeout) |
| `visibility_timeout` | `int`                       | `3600`      | Crash recovery timeout in seconds (1 hour) |
| `driver`             | `str \| BaseDriver \| None` | `None`      | Driver override (`None` = use global config)  |
| `process`            | `bool`                      | `False`     | Use process pool for CPU-intensive work       |

**Method Chaining:**

All configuration can be overridden at dispatch time:

```python
await task_func(args) \
    .on_queue("high-priority") \
    .max_attempts(10) \
    .timeout(120) \
    .retry_after(30) \
    .visibility_timeout(600) \
    .delay(60) \
    .dispatch()
```

### Execution Modes

For complete details on execution modes, concurrency characteristics, and when to use each type, see [Task Definitions - Task Types and Execution Modes](../task-definitions.md#task-types-and-execution-modes).

### Supported Queue Drivers

- **Redis** - Recommended for most use cases (fast, simple)
- **PostgreSQL** - When you need ACID guarantees or already use PostgreSQL
- **MySQL** - When already in your infrastructure
- **AWS SQS** - For AWS-native applications
- **RabbitMQ** - For complex routing or existing RabbitMQ setup

### What's Next?

- **Monitoring:** Track task execution with built-in monitoring
- **Advanced ORM:** Set up session factories for automatic model resolution
- **Class-based tasks:** Use when you need lifecycle hooks or complex logic
- **Production deployment:** Scale workers with Docker/Kubernetes
- **Error handling:** Implement custom retry logic with lifecycle hooks

### External Resources

While this guide is complete, you may want to reference:

- **GitHub Repository:** [github.com/adamrefaey/asynctasq](https://github.com/adamrefaey/asynctasq)
- **Full Documentation:** [github.com/adamrefaey/asynctasq/blob/main/docs/](https://github.com/adamrefaey/asynctasq/blob/main/docs/)
- **Issue Tracker:** [github.com/adamrefaey/asynctasq/issues](https://github.com/adamrefaey/asynctasq/issues)

This guide contains everything you need to use function-based tasks effectively!

For setup information:
- **Queue Drivers:** See [Queue Drivers - Overview](../queue-drivers.md#overview)
- **Running Workers:** See [Running Workers - CLI Workers](../running-workers.md#cli-workers-recommended)
- **Configuration:** See [Configuration - init() Function](../configuration.md#init)

## Common Patterns and Best Practices

### Error Handling

Tasks should handle their own errors gracefully. The framework will retry failed tasks according to the `max_attempts` configuration:

```python
@task(queue='api', max_attempts=3, retry_delay=60)
async def call_external_api(url: str):
    """Call external API with automatic retry on failure."""
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(url, timeout=10.0)
            response.raise_for_status()
            return response.json()
    except httpx.HTTPError as e:
        # Log error for debugging
        print(f"API call failed: {e}")
        # Re-raise to trigger retry mechanism
        raise
```

### Task ID Tracking

Store task IDs for monitoring and debugging:

```python
async def create_user_account(email: str, name: str):
    # Create user in database
    user = await create_user(email, name)

    # Dispatch welcome email and store task ID
    email_task_id = await send_welcome_email(user=user).dispatch()

    # Store task ID in database for tracking
    await store_task_reference(user.id, "welcome_email", email_task_id)

    return user
```

### Configuration Best Practices

- **Use descriptive queue names:** `'emails'`, `'payments'`, `'notifications'` instead of `'queue1'`, `'queue2'`
- **Set appropriate timeouts:** Prevent tasks from running indefinitely
- **Configure retries based on task type:** Critical tasks need more retries than validation tasks
- **Use driver overrides sparingly:** Only when necessary for specific requirements

### Performance Tips

- **Prefer async functions** for I/O-bound operations
- **Use sync functions** only when necessary (blocking libraries, CPU-bound work)
- **Keep task payloads small:** For supported ORMs (SQLAlchemy, Django, Tortoise), the framework automatically converts model instances to lightweight references (class + primary key) during serialization, so you don't need to manually extract IDs
- **Batch related operations** when appropriate, but avoid overly large batches
- **Monitor queue sizes** and adjust worker concurrency accordingly
