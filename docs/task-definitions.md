# Task Definitions

AsyncTasQ supports two task definition styles: **function-based** (simple, inline) and **class-based** (reusable, testable).

## Function-Based Tasks

Use the `@task` decorator for simple, inline task definitions. The decorator provides **all 4 execution modes** through a combination of function type and the `process` parameter:

| Mode | Function Type | `process=` | Execution | Best For |
|------|---------------|-----------|-----------|----------|
| **AsyncTask** | `async def` | `False` (default) | Event loop | Async I/O-bound |
| **SyncTask** | `def` | `False` (default) | Thread pool | Sync/blocking I/O |
| **AsyncProcessTask** | `async def` | `True` | Process pool (async) | Async CPU-intensive |
| **SyncProcessTask** | `def` | `True` | Process pool (sync) | Sync CPU-intensive |

**Basic Function Task:**

```python
from asynctasq.tasks import task

@task
async def send_email(to: str, subject: str, body: str):
    print(f"Sending email to {to}: {subject}")
    await asyncio.sleep(1)  # Simulate email sending
    return f"Email sent to {to}"

# Dispatch
task_id = await send_email.dispatch(
    to="user@example.com",
    subject="Welcome!",
    body="Welcome to our platform!"
)
```

**With Configuration:**

```python
@task(queue='emails', max_attempts=5, retry_delay=120, timeout=30)
async def send_welcome_email(user_id: int):
    # Task automatically retries up to 5 times with 120s delay
    # Timeout after 30 seconds
    print(f"Sending welcome email to user {user_id}")
```

**Synchronous I/O Tasks:**

For blocking I/O operations (runs in thread pool via `SyncTask`):

```python
@task(queue='web-scraping')
def fetch_web_page(url: str):
    # Synchronous function runs in thread pool
    import requests
    response = requests.get(url)  # Blocking operation OK
    return response.text
```

**CPU-Intensive Tasks:**

For heavy CPU work, add `process=True` to run in process pool:

```python
@task(queue='data-processing', process=True, timeout=600)
def heavy_computation(data: list[float]):
    # Runs in ProcessPoolExecutor - bypasses GIL
    import numpy as np
    return np.fft.fft(data).tolist()
```

**Dispatching Function Tasks:**

```python
# Direct dispatch
task_id = await send_email(to="user@example.com", subject="Hello", body="Hi!").dispatch()

# With delay (execute after 60 seconds)
task_id = await send_email(to="user@example.com", subject="Hello", body="Hi!").delay(60).dispatch()

# Method chaining with queue override
task_id = await send_email(to="user@example.com", subject="Hello", body="Hi!").on_queue("high").dispatch()
```

---

## Class-Based Tasks

AsyncTasQ provides **4 base classes** for different execution patterns:

1. **`AsyncTask`** - Async I/O-bound tasks (API calls, DB queries) - **Use this 90% of the time**
2. **`SyncTask`** - Sync I/O-bound tasks via ThreadPoolExecutor (blocking libraries)
3. **`AsyncProcessTask`** - Async CPU-bound tasks via ProcessPoolExecutor (async heavy computation)
4. **`SyncProcessTask`** - Sync CPU-bound tasks via ProcessPoolExecutor (CPU-intensive work)

### Quick Selection Guide

| Task Type | Use For | Execution Context | Example |
|-----------|---------|-------------------|----------|
| `AsyncTask` | I/O-bound async operations | Event loop | API calls, async DB queries, file I/O |
| `SyncTask` | I/O-bound sync/blocking operations | Thread pool | `requests` library, sync DB drivers |
| `AsyncProcessTask` | CPU-bound async operations | Process pool with async | ML inference with async preprocessing |
| `SyncProcessTask` | CPU-bound sync operations | Process pool | Data processing, encryption, video encoding |

### AsyncTask - Async I/O-Bound (Default Choice)

Use for async operations like API calls, database queries, file I/O:

```python
from asynctasq.tasks import AsyncTask

class ProcessPayment(AsyncTask[bool]):
    queue = "payments"
    max_attempts = 3
    retry_delay = 60
    timeout = 30

    def __init__(self, user_id: int, amount: float, **kwargs):
        super().__init__(**kwargs)
        self.user_id = user_id
        self.amount = amount

    async def execute(self) -> bool:
        # Async I/O-bound work
        print(f"Processing ${self.amount} for user {self.user_id}")
        await asyncio.sleep(2)  # Async operation
        return True
```

### SyncTask - Sync I/O-Bound via Thread Pool

Use for blocking I/O operations (e.g., `requests` library, sync DB drivers):

```python
from asynctasq.tasks import SyncTask
import requests

class FetchWebPage(SyncTask[str]):
    queue = "web-scraping"
    max_attempts = 3

    def __init__(self, url: str, **kwargs):
        super().__init__(**kwargs)
        self.url = url

    def execute(self) -> str:
        # Runs in thread pool - blocking OK
        response = requests.get(self.url)
        return response.text
```

### AsyncProcessTask - Async CPU-Bound via Process Pool

Use for CPU-intensive async operations (e.g., ML inference with async preprocessing):

```python
from asynctasq.tasks import AsyncProcessTask

class ProcessVideoAsync(AsyncProcessTask[dict]):
    queue = "video-processing"
    timeout = 3600

    def __init__(self, video_path: str, **kwargs):
        super().__init__(**kwargs)
        self.video_path = video_path

    async def execute(self) -> dict:
        # Runs in subprocess with async support
        # Async preprocessing
        async with aiofiles.open(self.video_path, 'rb') as f:
            data = await f.read()

        # CPU-intensive work (bypasses GIL)
        result = await self._process_frames(data)
        return {"frames_processed": result}
```

### SyncProcessTask - Sync CPU-Bound via Process Pool

Use for CPU-intensive synchronous operations (e.g., data processing, encryption):

```python
from asynctasq.tasks import SyncProcessTask
import numpy as np

class ProcessLargeDataset(SyncProcessTask[dict]):
    queue = "data-processing"
    timeout = 3600

    def __init__(self, data: list[float], **kwargs):
        super().__init__(**kwargs)
        self.data = data

    def execute(self) -> dict:
        # Runs in subprocess - bypasses GIL
        arr = np.array(self.data)
        result = np.fft.fft(arr)  # CPU-intensive
        return {"mean": float(result.mean())}
```

**With Lifecycle Hooks:**

```python
class ProcessPayment(AsyncTask[bool]):
    queue = "payments"
    max_attempts = 3
    retry_delay = 60

    def __init__(self, user_id: int, amount: float, **kwargs):
        super().__init__(**kwargs)
        self.user_id = user_id
        self.amount = amount

    async def execute(self) -> bool:
        # Main task logic
        print(f"Processing ${self.amount} for user {self.user_id}")
        await self._charge_card()
        await self._send_receipt()
        return True

    async def failed(self, exception: Exception) -> None:
        # Called when task fails after all retries
        print(f"Payment failed for user {self.user_id}: {exception}")
        await self._refund_user()
        await self._notify_admin(exception)

    def should_retry(self, exception: Exception) -> bool:
        # Custom retry logic
        if isinstance(exception, ValueError):
            # Don't retry validation errors
            return False
        if isinstance(exception, ConnectionError):
            # Always retry network errors
            return True
        return True  # Default: retry

    async def _charge_card(self):
        # Private helper methods
        pass

    async def _send_receipt(self):
        pass

    async def _refund_user(self):
        pass

    async def _notify_admin(self, exception: Exception):
        pass
```

**Dispatching Class Tasks:**

```python
# Method 1: Immediate dispatch
task_id = await ProcessPayment(user_id=123, amount=99.99).dispatch()

# Method 2: With delay
task_id = await ProcessPayment(user_id=123, amount=99.99).delay(60).dispatch()

# Method 3: Method chaining
task_id = await ProcessPayment(user_id=123, amount=99.99) \
    .on_queue("high-priority") \
    .delay(60) \
    .retry_after(120) \
    .dispatch()
```

---

## Task Configuration

AsyncTasQ provides flexible task configuration through **class attributes** (for defaults) and **method chaining** (for runtime configuration). All configuration lives in `task.config`.

### Configuration Attributes

All tasks have access to these configuration attributes via `task.config`:

| Attribute | Type | Default | Description |
|-----------|------|---------|-------------|
| `queue` | `str` | `"default"` | Target queue name for task execution |
| `max_attempts` | `int` | `3` | Maximum execution attempts (including initial attempt) |
| `retry_delay` | `int` | `60` | Delay in seconds between retry attempts |
| `timeout` | `int \| None` | `None` | Task execution timeout in seconds (None = no timeout) |
| `driver` | `DriverType \| None` | `None` | Override default queue driver for this task |

### Pattern 1: Using `config` Dict with `TaskConfigDict`

Define configuration using a class-level `config` dictionary with the `TaskConfigDict` TypedDict for full type safety:

```python
from asynctasq.tasks import AsyncTask, TaskConfigDict

class SendEmail(AsyncTask[str]):
    # Configuration via config dict (type-safe with TaskConfigDict)
    config: TaskConfigDict = {
        "queue": "emails",
        "max_attempts": 5,
        "retry_delay": 120,
        "timeout": 30,
    }

    to: str
    subject: str

    async def execute(self) -> str:
        # Send email logic
        return f"Email sent to {self.to}"

# Uses defaults from config dict
task_id = await SendEmail(to="user@example.com", subject="Welcome").dispatch()

# Override with method chaining
task_id = await SendEmail(to="admin@example.com", subject="Alert") \
    .max_attempts(10) \
    .timeout(60) \
    .dispatch()
```

**Benefits:**
- ✅ Full type safety with `TaskConfigDict` TypedDict
- ✅ IDE autocomplete for config keys
- ✅ Works with method chaining
- ✅ Clear separation between config and task parameters
- ✅ No type checker warnings

### Pattern 2: Method Chaining (Runtime)

Override configuration at runtime using fluent method chaining. All methods return `Self` for chaining:

```python
class ProcessOrder(AsyncTask[dict]):
    order_id: int

    async def execute(self) -> dict:
        return {"order_id": self.order_id, "status": "processed"}

# Override configuration via method chaining
task_id = await ProcessOrder(order_id=123) \
    .on_queue("high-priority") \
    .max_attempts(10) \
    .timeout(300) \
    .retry_after(60) \
    .delay(30) \
    .dispatch()
```

### Available Chainable Methods

All tasks (function-based and class-based) support these chainable methods:

#### `on_queue(queue_name: str) -> Self`

Set the target queue for task dispatch.

```python
task_id = await my_task().on_queue("high-priority").dispatch()
```

#### `delay(seconds: int) -> Self`

Delay task execution by N seconds after dispatch (scheduled execution).

```python
# Execute 1 hour from now
task_id = await my_task().delay(3600).dispatch()
```

#### `retry_after(seconds: int) -> Self`

Set delay between retry attempts (overrides `retry_delay`).

```python
# Wait 5 minutes between retries
task_id = await my_task().retry_after(300).dispatch()
```

#### `max_attempts(attempts: int) -> Self`

Set maximum number of execution attempts (including initial attempt).

```python
# Retry up to 10 times
task_id = await my_task().max_attempts(10).dispatch()
```

#### `timeout(seconds: int | None) -> Self`

Set task execution timeout in seconds (None = no timeout).

```python
# Timeout after 5 minutes
task_id = await my_task().timeout(300).dispatch()

# Disable timeout
task_id = await my_task().timeout(None).dispatch()
```

### Combining Config Dict with Method Chaining

You can set defaults via `config` dict (with `TaskConfigDict` for type safety) and override them with method chaining:

```python
from asynctasq.tasks import AsyncTask, TaskConfigDict

class SendNotification(AsyncTask[bool]):
    # Defaults via config dict (type-safe)
    config: TaskConfigDict = {
        "queue": "notifications",
        "max_attempts": 3,
        "timeout": 30,
    }

    user_id: int
    message: str

    async def execute(self) -> bool:
        # Send notification logic
        return True

# Use defaults from config
await SendNotification(user_id=123, message="Hello").dispatch()

# Override with method chaining
await SendNotification(user_id=456, message="URGENT") \
    .on_queue("critical") \
    .max_attempts(10) \
    .timeout(60) \
    .dispatch()
```

### Configuration with Function-Based Tasks

Function-based tasks support the same configuration patterns:

```python
# Via decorator
@task(queue="emails", max_attempts=5, timeout=30)
async def send_email(to: str, subject: str):
    # Email logic
    pass

# Via method chaining
task_id = await send_email(to="user@example.com", subject="Hi") \
    .max_attempts(10) \
    .timeout(60) \
    .retry_after(120) \
    .dispatch()
```

### Accessing Configuration

Configuration is stored in `task.config` (a `TaskConfig` object):

```python
task = SendEmail(to="user@example.com", subject="Welcome")
print(task.config.queue)          # "emails"
print(task.config.max_attempts)   # 5
print(task.config.timeout)        # 30

# After chaining
task = task.max_attempts(10)
print(task.config.max_attempts)   # 10
```

---

## Choosing the Right Task Type

AsyncTasQ provides **4 task execution modes** optimized for different workloads. Choosing the right mode is critical for optimal performance:

### The Four Execution Modes

1. **`AsyncTask`** - Event loop execution for async I/O-bound operations
2. **`SyncTask`** - Thread pool execution for sync/blocking I/O operations
3. **`AsyncProcessTask`** - Process pool execution for async CPU-intensive operations
4. **`SyncProcessTask`** - Process pool execution for sync CPU-intensive operations

### Comparison Table

| Task Type | Execution Context | Best For | Concurrency | Example Use Cases |
|-----------|-------------------|----------|-------------|-------------------|
| `AsyncTask` | Event loop (async) | Async I/O-bound | 1000s concurrent | API calls, async DB queries, WebSocket, async file I/O |
| `SyncTask` | Thread pool | Sync/blocking I/O | 100s concurrent | `requests` library, sync DB drivers, file operations |
| `AsyncProcessTask` | Process pool (async) | Async CPU-intensive | CPU cores | ML inference with async I/O, async video processing |
| `SyncProcessTask` | Process pool (sync) | Sync CPU-intensive | CPU cores | NumPy/Pandas processing, encryption, image processing |

### Quick Decision Matrix

**Choose based on your workload characteristics:**

```python
# ✅ Use AsyncTask for async I/O-bound work (90% of use cases)
class FetchData(AsyncTask[dict]):
    async def execute(self) -> dict:
        async with httpx.AsyncClient() as client:
            response = await client.get(url)
            return response.json()

# ✅ Use SyncTask for blocking I/O (requests, sync DB drivers)
class FetchWebPage(SyncTask[str]):
    def execute(self) -> str:
        import requests
        response = requests.get(self.url)
        return response.text

# 🚀 Use AsyncProcessTask for async CPU-intensive work
class ProcessVideoAsync(AsyncProcessTask[dict]):
    async def execute(self) -> dict:
        # Async I/O + CPU work in subprocess
        async with aiofiles.open(self.path, 'rb') as f:
            data = await f.read()
        return await self._process_frames(data)

# 🚀 Use SyncProcessTask for sync CPU-intensive work
class ProcessDataset(SyncProcessTask[dict]):
    def execute(self) -> dict:
        import numpy as np
        # Heavy computation bypasses GIL
        result = np.linalg.inv(self.large_matrix)
        return {"result": result.tolist()}
```

### Performance Characteristics

| Mode | Concurrency | Memory Overhead | Best Throughput |
|------|------------|-----------------|------------------|
| **AsyncTask** | 1000s concurrent | Minimal (~KB per task) | I/O-bound async workloads |
| **SyncTask** | 100s concurrent | Low (~MB per thread) | I/O-bound sync/blocking workloads |
| **AsyncProcessTask** | CPU cores | High (~50MB+ per process) | CPU-intensive with async I/O |
| **SyncProcessTask** | CPU cores | High (~50MB+ per process) | CPU-intensive sync workloads |

### When to Use Each Type

**AsyncTask (Default - Use for 90% of tasks):**

✅ I/O-bound async operations (API calls, async database queries)
✅ Tasks that spend time waiting (network, disk, external services)
✅ Async libraries available (httpx, aiohttp, asyncpg, aiofiles, etc.)
✅ Need high concurrency (1000s of tasks)
✅ Low CPU utilization during execution

**SyncTask (For blocking I/O):**

✅ Blocking I/O libraries (`requests`, sync DB drivers like `psycopg2`)
✅ File operations with sync libraries
✅ Legacy sync code that can't be easily converted to async
✅ Moderate concurrency needed (100s of tasks)

❌ Don't use for async code (use `AsyncTask` instead)
❌ Don't use for CPU-intensive work (use process tasks instead)

**AsyncProcessTask (For async CPU-intensive work):**

✅ CPU-intensive work that also needs async I/O
✅ ML inference with async preprocessing/postprocessing
✅ Video processing with async file operations
✅ Task duration > 100ms (amortizes process overhead)
✅ All arguments and return values are serializable (msgpack-compatible)

❌ Don't use for pure I/O-bound tasks (use `AsyncTask` instead)
❌ Don't use for short tasks < 100ms (overhead not worth it)

**SyncProcessTask (For sync CPU-intensive work):**

✅ CPU utilization > 80% (verified with profiling)
✅ Heavy computation that bypasses GIL (NumPy, Pandas, encryption)
✅ Task duration > 100ms (amortizes process overhead)
✅ All arguments and return values are serializable (msgpack-compatible)
✅ No async operations needed

❌ Don't use for I/O-bound tasks (use `AsyncTask` or `SyncTask` instead)
❌ Don't use for short tasks < 100ms (overhead not worth it)
❌ Don't use with unserializable objects like lambdas or file handles (will fail at dispatch)

---

## Task Configuration Options

**Available Configuration:**

| Option        | Type          | Default     | Description                                 |
| ------------- | ------------- | ----------- | ------------------------------------------- |
| `queue`       | `str`         | `"default"` | Queue name for task                         |
| `max_attempts` | `int`         | `3`         | Maximum retry attempts                      |
| `retry_delay` | `int`         | `60`        | Seconds to wait between retries             |
| `timeout`     | `int \| None` | `None`      | Task timeout in seconds (None = no timeout) |

---

## Configuration Approaches: Function vs Class Tasks

AsyncTasQ provides **two distinct configuration systems** depending on your task definition style. Understanding when and how to use each is essential for writing clean, maintainable code.

### Overview

| Task Style | Configuration Source | Example |
|-----------|---------------------|---------|
| **Function-based** (`@task`) | Decorator arguments | `@task(queue='emails', max_attempts=5)` |
| **Class-based** (`AsyncTask`, `SyncTask`) | Class attributes | `class MyTask: queue = 'emails'` |

### Function-Based Task Configuration

**Function tasks ALWAYS use decorator arguments for configuration.** Class attributes are ignored.

```python
# ✅ CORRECT: Use decorator arguments
@task(queue='emails', max_attempts=5, retry_delay=120, timeout=30)
async def send_email(to: str, subject: str, body: str):
    print(f"Sending email to {to}: {subject}")
    return f"Email sent to {to}"

# ❌ WRONG: Class attributes don't apply to function tasks
@task
async def send_email(to: str, subject: str, body: str):
    # These attributes are ignored!
    queue = "emails"  # This is just a local variable
    max_attempts = 5   # This does nothing
    print(f"Sending email to {to}: {subject}")
```

**Runtime Configuration with Method Chaining:**

```python
# Decorator sets defaults
@task(queue='notifications', max_attempts=3)
async def send_notification(user_id: int, message: str):
    pass

# Override at dispatch time with method chaining
task_id = await send_notification(user_id=123, message="Hello") \
    .on_queue("high-priority") \  # Override queue
    .retry_after(30) \             # Override retry_delay
    .delay(60) \                   # Add 60s delay
    .dispatch()
```

### Class-Based Task Configuration

**Class tasks use class attributes for default configuration.**

```python
# ✅ CORRECT: Use class attributes
class ProcessPayment(AsyncTask[bool]):
    # Configuration via class attributes
    queue = "payments"
    max_attempts = 3
    retry_delay = 60
    timeout = 30

    def __init__(self, user_id: int, amount: float, **kwargs):
        super().__init__(**kwargs)
        self.user_id = user_id
        self.amount = amount

    async def execute(self) -> bool:
        print(f"Processing ${self.amount} for user {self.user_id}")
        return True

# Dispatch with defaults
task_id = await ProcessPayment(user_id=123, amount=99.99).dispatch()
```

**Runtime Configuration with Method Chaining:**

```python
# Override class defaults at dispatch time
task_id = await ProcessPayment(user_id=123, amount=99.99) \
    .on_queue("high-priority") \  # Override class attribute
    .retry_after(120) \            # Override retry_delay
    .delay(60) \                   # Add delay
    .dispatch()
```

**How It Works Internally:**

```python
class BaseTask:
    @classmethod
    def _extract_config_from_class(cls) -> dict[str, Any]:
        """Extract TaskConfig values from class attributes."""
        return {
            "queue": getattr(cls, "queue", "default"),
            "max_attempts": getattr(cls, "max_attempts", 3),
            "retry_delay": getattr(cls, "retry_delay", 60),
            "timeout": getattr(cls, "timeout", None),
        }

    def __init__(self, **kwargs):
        # Read configuration from class attributes
        config_values = self._extract_config_from_class()
        self.config = TaskConfig(**config_values)
        # ...
```

### Configuration Priority Order

When multiple configuration sources are present, AsyncTasQ follows this priority order:

**For Function Tasks:**
1. **Method chaining** (highest priority) - `.on_queue("high")`
2. **Decorator arguments** - `@task(queue='emails')`
3. **Framework defaults** (lowest) - `queue='default'`

**For Class Tasks:**
1. **Method chaining** (highest priority) - `.on_queue("high")`
2. **Class attributes** - `class MyTask: queue = 'emails'`
3. **Framework defaults** (lowest) - `queue='default'`

**Example:**

```python
# Function task priority order
@task(queue='notifications', max_attempts=3)  # 2. Decorator defaults
async def send_notification(user_id: int):
    pass

# Override at runtime
task_id = await send_notification(user_id=123) \
    .on_queue("urgent") \  # 1. Highest priority - overrides decorator
    .dispatch()
# Result: Uses queue="urgent", max_attempts=3

# Class task priority order
class ProcessOrder(AsyncTask[bool]):
    queue = "orders"      # 2. Class attribute
    max_attempts = 3

    def __init__(self, order_id: int, **kwargs):
        super().__init__(**kwargs)
        self.order_id = order_id

    async def execute(self) -> bool:
        return True

# Override at runtime
task_id = await ProcessOrder(order_id=456) \
    .on_queue("express") \  # 1. Highest priority - overrides class attribute
    .dispatch()
# Result: Uses queue="express", max_attempts=3
```

### Best Practices

**✅ DO:**

- Use decorator arguments for function tasks: `@task(queue='emails')`
- Use class attributes for class tasks: `class MyTask: queue = 'emails'`
- Use method chaining for runtime overrides: `.on_queue("high").delay(60)`
- Be consistent within your codebase (pick function or class style and stick to it)

**❌ DON'T:**

- Mix configuration approaches (e.g., decorator + class attributes in same task)
- Assume class attributes work with `@task` decorated functions
- Modify `task.config` directly after instantiation (use method chaining instead)

### Common Pitfalls

**Pitfall 1: Expecting class attributes to work with `@task`**

```python
# ❌ WRONG: This doesn't work
@task
async def send_email(to: str):
    queue = "emails"  # This is just a local variable, not configuration!
    pass

# ✅ CORRECT: Use decorator arguments
@task(queue='emails')
async def send_email(to: str):
    pass
```

**Pitfall 2: Forgetting to call `super().__init__()` in class tasks**

```python
# ❌ WRONG: Missing super().__init__() call
class ProcessPayment(AsyncTask[bool]):
    def __init__(self, amount: float):
        self.amount = amount  # Config not initialized!

# ✅ CORRECT: Always call super().__init__()
class ProcessPayment(AsyncTask[bool]):
    def __init__(self, amount: float, **kwargs):
        super().__init__(**kwargs)  # Initializes config
        self.amount = amount
```

---

## Additional Configuration Methods

Beyond the two primary approaches, AsyncTasQ provides convenience methods for common scenarios:

```python
# 1. Decorator configuration (function tasks)
@task(queue='emails', max_attempts=5, retry_delay=120, timeout=30)
async def send_email(to: str, subject: str):
    pass

# 2. Class attributes (class tasks)
class ProcessPayment(AsyncTask[bool]):
    queue = "payments"
    max_attempts = 3
    retry_delay = 60
    timeout = 30

# 3. Method chaining (runtime configuration for both)
await task_instance.on_queue("high").retry_after(120).delay(60).dispatch()

# 4. Function tasks - unified API
await send_email(to="user@example.com", subject="Hello").delay(60).dispatch()
```

**Task Metadata:**

Tasks automatically track metadata:

- `_task_id`: UUID string for task identification
- `_current_attempt`: Current retry attempt count (0-indexed)
- `_dispatched_at`: ISO format datetime when task was first queued

Access metadata in task methods:

```python
class MyTask(AsyncTask[None]):
    async def execute(self) -> None:
        print(f"Task ID: {self._task_id}")
        print(f"Attempt: {self._current_attempt}")
        print(f"Dispatched at: {self._dispatched_at}")
```
