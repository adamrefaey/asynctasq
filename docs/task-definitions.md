# Task Definitions

This document explains how to define tasks in AsyncTasQ, covering both function-based and class-based approaches, task types, and configuration options.

For complete working examples, see:
- [Function-Based Tasks Examples](examples/function-based-tasks.md)
- [Class-Based Tasks Examples](examples/class-based-tasks.md)

## Table of Contents

- [Function-Based Tasks](#function-based-tasks)
- [Class-Based Tasks](#class-based-tasks)
- [Task Types and Execution Modes](#task-types-and-execution-modes)
- [Task Configuration](#task-configuration)
- [Configuration Approaches](#configuration-approaches)

AsyncTasQ supports two task definition styles: **function-based** (simple, inline) and **class-based** (reusable, testable).

## Function-Based Tasks

Use the `@task` decorator for simple, inline task definitions. The decorator provides **all 4 execution modes** through a combination of function type and the `process` parameter:

| Mode                 | Function Type | `process=`        | Execution            | Best For            |
| -------------------- | ------------- | ----------------- | -------------------- | ------------------- |
| **AsyncTask**        | `async def`   | `False` (default) | Event loop           | Async I/O-bound     |
| **SyncTask**         | `def`         | `False` (default) | Thread pool          | Sync/blocking I/O   |
| **AsyncProcessTask** | `async def`   | `True`            | Process pool (async) | Async CPU-intensive |
| **SyncProcessTask**  | `def`         | `True`            | Process pool (sync)  | Sync CPU-intensive  |

**Basic Syntax:**

```python
from asynctasq import task

# Async I/O task (default)
@task
async def send_email(to: str, subject: str, body: str):
    print(f"Sending email to {to}")
    return f"Email sent"

# Sync I/O task
@task(queue='web-scraping')
def fetch_web_page(url: str):
    import requests
    return requests.get(url).text

# CPU-intensive task
@task(queue='data-processing', process=True)
def heavy_computation(data: list[float]):
    import numpy as np
    return np.fft.fft(data).tolist()
```

**Dispatching:**

Function tasks use a two-step dispatch pattern - call the function first, then `.dispatch()`:

```python
# Basic dispatch
task_id = await send_email(to="user@example.com", subject="Hello", body="Hi").dispatch()

# With delay
task_id = await send_email(...).delay(60).dispatch()

# With method chaining
task_id = await send_email(...).on_queue("high").retry_after(120).dispatch()
```

For detailed examples, see [Function-Based Tasks Guide](examples/function-based-tasks.md).

---

## Class-Based Tasks

AsyncTasQ provides **4 base classes** for different execution patterns:

| Task Type          | Use For                            | Execution Context       | Example Use Cases                           |
| ------------------ | ---------------------------------- | ----------------------- | ------------------------------------------- |
| `AsyncTask`        | I/O-bound async operations         | Event loop              | API calls, async DB queries, file I/O       |
| `SyncTask`         | I/O-bound sync/blocking operations | Thread pool             | `requests` library, sync DB drivers         |
| `AsyncProcessTask` | CPU-bound async operations         | Process pool with async | ML inference with async preprocessing       |
| `SyncProcessTask`  | CPU-bound sync operations          | Process pool            | Data processing, encryption, video encoding |

**Basic Syntax:**

```python
from asynctasq import AsyncTask, TaskConfig

class ProcessPayment(AsyncTask[bool]):
    # Configuration via config dict
    config: TaskConfig = {
        "queue": "payments",
        "max_attempts": 3,
        "retry_delay": 60,
        "timeout": 30,
    }

    def __init__(self, user_id: int, amount: float, **kwargs):
        super().__init__(**kwargs)
        self.user_id = user_id
        self.amount = amount

    async def execute(self) -> bool:
        print(f"Processing ${self.amount} for user {self.user_id}")
        return True

    async def failed(self, exception: Exception) -> None:
        # Optional: Called when task fails after all retries
        print(f"Payment failed: {exception}")

    def should_retry(self, exception: Exception) -> bool:
        # Optional: Custom retry logic
        return not isinstance(exception, ValueError)
```

**Dispatching:**

```python
# Basic dispatch
task_id = await ProcessPayment(user_id=123, amount=99.99).dispatch()

# With method chaining
task_id = await ProcessPayment(user_id=123, amount=99.99) \
    .on_queue("high-priority") \
    .retry_after(120) \
    .dispatch()
```

For detailed examples including all task types and lifecycle hooks, see [Class-Based Tasks Guide](examples/class-based-tasks.md).

---

## Task Types and Execution Modes

AsyncTasQ provides **4 task execution modes** optimized for different workloads:

### The Four Modes

1. **AsyncTask** - Event loop execution for async I/O-bound operations
2. **SyncTask** - Thread pool execution for sync/blocking I/O operations
3. **AsyncProcessTask** - Process pool execution for async CPU-intensive operations
4. **SyncProcessTask** - Process pool execution for sync CPU-intensive operations

### Comparison Table

| Task Type          | Execution Context    | Best For            | Concurrency      | Example Use Cases                                      |
| ------------------ | -------------------- | ------------------- | ---------------- | ------------------------------------------------------ |
| `AsyncTask`        | Event loop (async)   | Async I/O-bound     | 1000s concurrent | API calls, async DB queries, WebSocket, async file I/O |
| `SyncTask`         | Thread pool          | Sync/blocking I/O   | 100s concurrent  | `requests` library, sync DB drivers, file operations   |
| `AsyncProcessTask` | Process pool (async) | Async CPU-intensive | CPU cores        | ML inference with async I/O, async video processing    |
| `SyncProcessTask`  | Process pool (sync)  | Sync CPU-intensive  | CPU cores        | NumPy/Pandas processing, encryption, image processing  |

### When to Use Each Type

**AsyncTask (Default - Use for 90% of tasks):**
- I/O-bound async operations (API calls, async database queries)
- Async libraries available (httpx, aiohttp, asyncpg, aiofiles)
- High concurrency needed (1000s of tasks)

**SyncTask (For blocking I/O):**
- Blocking I/O libraries (`requests`, sync DB drivers like `psycopg2`)
- Legacy sync code that can't be easily converted to async

**AsyncProcessTask (For async CPU-intensive work):**
- CPU-intensive work that also needs async I/O
- ML inference with async preprocessing/postprocessing

**SyncProcessTask (For sync CPU-intensive work):**
- CPU utilization > 80% (verified with profiling)
- Heavy computation (NumPy, Pandas, encryption)
- Task duration > 100ms (amortizes process overhead)

---

## Task Configuration

All tasks support the following configuration options:

| Attribute            | Type                               | Default     | Description                                                                         |
| -------------------- | ---------------------------------- | ----------- | ----------------------------------------------------------------------------------- |
| `queue`              | `str`                              | `"default"` | Target queue name for task execution                                                |
| `max_attempts`       | `int`                              | `3`         | Maximum execution attempts (including initial attempt)                              |
| `retry_delay`        | `int`                              | `60`        | Delay in seconds between retry attempts                                             |
| `timeout`            | `int \| None`                      | `None`      | Task execution timeout in seconds (None = no timeout)                               |
| `visibility_timeout` | `int`                              | `300`       | Crash recovery timeout - seconds task is invisible before auto-recovery (5 minutes) |
| `driver`             | `DriverType \| BaseDriver \| None` | `None`      | Override default queue driver for this task                                         |
| `correlation_id`     | `str \| None`                      | `None`      | Correlation ID for distributed tracing                                              |

### Class-Based Configuration

```python
from asynctasq import AsyncTask, TaskConfig

class SendEmail(AsyncTask[str]):
    config: TaskConfig = {
        "queue": "emails",
        "max_attempts": 5,
        "retry_delay": 120,
        "timeout": 30,
    }

    def __init__(self, to: str, subject: str, **kwargs):
        super().__init__(**kwargs)
        self.to = to
        self.subject = subject

    async def execute(self) -> str:
        return f"Email sent to {self.to}"
```

### Function-Based Configuration

```python
from asynctasq import task

@task(queue="emails", max_attempts=5, retry_delay=120, timeout=30)
async def send_email(to: str, subject: str):
    return f"Email sent to {to}"
```

### Method Chaining

Both function and class-based tasks support method chaining to override configuration at dispatch time:

**Available Methods:**
- `.on_queue(name)` - Override queue name
- `.delay(seconds)` - Delay execution
- `.retry_after(seconds)` - Override retry delay
- `.max_attempts(n)` - Override max attempts
- `.timeout(seconds)` - Override timeout
- `.visibility_timeout(seconds)` - Override visibility timeout

**Example:**

```python
# Class-based
task_id = await SendEmail(to="user@example.com", subject="Hi") \
    .on_queue("high-priority") \
    .max_attempts(10) \
    .dispatch()

# Function-based
task_id = await send_email(to="user@example.com", subject="Hi") \
    .on_queue("high-priority") \
    .max_attempts(10) \
    .dispatch()
```

### Understanding Visibility Timeout

Visibility timeout is AsyncTasQ's automatic crash recovery mechanism. When a worker crashes before completing a task, the task automatically becomes available again after the timeout expires.

**How it works:**
1. Worker dequeues task → Task locked for `visibility_timeout` seconds
2. Worker crashes → Task remains locked
3. Timeout expires → Task becomes available for retry

**Choosing the right value:**
- **Too short**: Duplicate processing if task takes longer than timeout
- **Too long**: Slow recovery from crashes
- **Recommended**: `visibility_timeout = (expected_duration × 2) + buffer`

**Example:**
```python
# Quick task
config: TaskConfig = {
    "timeout": 60,
    "visibility_timeout": 180,  # (60 × 2) + 60
}

# Long task
config: TaskConfig = {
    "timeout": 600,
    "visibility_timeout": 1500,  # (600 × 2) + 300
}
```

**Driver support:** PostgreSQL, MySQL, SQS (Redis and RabbitMQ use different mechanisms)

---

## Configuration Approaches

AsyncTasQ supports two configuration approaches:

| Task Style        | Configuration Source | Priority (Highest to Lowest)                                  |
| ----------------- | -------------------- | ------------------------------------------------------------- |
| **Function-based** | Decorator arguments  | 1. Method chaining → 2. Decorator arguments → 3. Defaults     |
| **Class-based**    | `config` dict        | 1. Method chaining → 2. Class config dict → 3. Defaults       |

**Key Points:**

- Function tasks: Use `@task(queue='emails', max_attempts=5)`
- Class tasks: Use `config: TaskConfig = {"queue": "emails", "max_attempts": 5}`
- Both support method chaining for runtime overrides
- Always call `super().__init__(**kwargs)` in class task `__init__` methods

**Common Pitfalls:**

```python
# ❌ WRONG: Local variables don't configure function tasks
@task
async def send_email(to: str):
    queue = "emails"  # This is just a variable, not configuration!

# ✅ CORRECT: Use decorator arguments
@task(queue="emails")
async def send_email(to: str):
    pass
```

For comprehensive examples and best practices, see:
- [Function-Based Tasks Guide](examples/function-based-tasks.md)
- [Class-Based Tasks Guide](examples/class-based-tasks.md)
