# Task Definitions

AsyncTasQ supports two task definition styles: **function-based** (simple, inline) and **class-based** (reusable, testable).

## Function-Based Tasks

Use the `@task` decorator for simple, inline task definitions.

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
@task(queue='emails', max_retries=5, retry_delay=120, timeout=30)
async def send_welcome_email(user_id: int):
    # Task automatically retries up to 5 times with 120s delay
    # Timeout after 30 seconds
    print(f"Sending welcome email to user {user_id}")
```

**Synchronous Tasks:**

For blocking I/O or CPU-intensive work:

```python
@task(queue='reports')
def generate_report(report_id: int):
    # Synchronous function runs in thread pool
    import time
    time.sleep(5)  # Blocking operation OK
    return f"Report {report_id} generated"
```

**Dispatching Function Tasks:**

```python
# Method 1: Direct dispatch
task_id = await send_email.dispatch(to="user@example.com", subject="Hello", body="Hi!")

# Method 2: With delay (execute after 60 seconds)
task_id = await send_email.dispatch(to="user@example.com", subject="Hello", body="Hi!", delay=60)

# Method 3: Method chaining
task_id = await send_email(to="user@example.com", subject="Hello", body="Hi!").delay(60).dispatch()
```

---

## Class-Based Tasks

Use the `BaseTask` base class for complex tasks with lifecycle hooks and custom retry logic.

**Basic Class Task:**

```python
from asynctasq.tasks import BaseTask

class ProcessPayment(BaseTask[bool]):
    queue = "payments"
    max_retries = 3
    retry_delay = 60
    timeout = 30

    def __init__(self, user_id: int, amount: float, **kwargs):
        super().__init__(**kwargs)
        self.user_id = user_id
        self.amount = amount

    async def handle(self) -> bool:
        # Your payment processing logic
        print(f"Processing ${self.amount} for user {self.user_id}")
        await asyncio.sleep(2)
        return True
```

**With Lifecycle Hooks:**

```python
class ProcessPayment(BaseTask[bool]):
    queue = "payments"
    max_retries = 3
    retry_delay = 60

    def __init__(self, user_id: int, amount: float, **kwargs):
        super().__init__(**kwargs)
        self.user_id = user_id
        self.amount = amount

    async def handle(self) -> bool:
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

**Synchronous Class Tasks:**

```python
from asynctasq.tasks import SyncTask

class GenerateReport(SyncTask[str]):
    queue = "reports"
    timeout = 300  # 5 minutes

    def __init__(self, report_id: int, **kwargs):
        super().__init__(**kwargs)
        self.report_id = report_id

    def handle_sync(self) -> str:
        # Synchronous handle method (runs in thread pool)
        import time
        time.sleep(5)  # Blocking operation OK
        return f"Report {self.report_id} generated"
```

**CPU-Intensive Class Tasks (Multiprocessing):**

```python
from asynctasq.tasks import ProcessTask

class VideoEncoding(ProcessTask[str]):
    """CPU-intensive task - runs in separate process with independent GIL."""
    queue = "heavy-cpu"
    timeout = 600  # 10 minutes

    def __init__(self, video_path: str, output_format: str, **kwargs):
        super().__init__(**kwargs)
        self.video_path = video_path
        self.output_format = output_format

    def handle_process(self) -> str:
        # Runs in subprocess - true parallelism, bypasses GIL
        import ffmpeg  # Heavy CPU work
        output_path = f"{self.video_path}.{self.output_format}"
        ffmpeg.input(self.video_path).output(output_path).run()
        return output_path
```

---

## Choosing the Right Task Type

AsyncTasQ provides **three task execution modes** optimized for different workloads. Choosing the right mode is critical for optimal performance:

### The Three Execution Modes

1. **BaseTask** (Async) - Event loop execution for I/O-bound operations
2. **SyncTask** (Thread Pool) - Thread pool execution for moderate CPU work or blocking libraries  
3. **ProcessTask** (Process Pool) - Multiprocessing execution for heavy CPU-intensive workloads

### Comparison Table

| Task Type       | Execution Context  | Best For                          | CPU Usage   | Example Use Cases                        |
| --------------- | ------------------ | --------------------------------- | ----------- | ---------------------------------------- |
| `BaseTask`      | Event loop (async) | I/O-bound operations              | < 10%       | API calls, DB queries, file I/O, network |
| `SyncTask`      | Thread pool (sync) | Moderate CPU work, blocking libs  | 10-80%      | Image resize, data parsing, sync libs    |
| `ProcessTask`   | Process pool       | Heavy CPU-intensive computation   | > 80%       | Video encoding, ML inference, encryption |

### Quick Decision Matrix

**Choose based on your workload characteristics:**

```python
# ✅ Use BaseTask (async) for I/O-bound work
class FetchData(BaseTask[dict]):
    async def handle(self) -> dict:
        async with httpx.AsyncClient() as client:
            response = await client.get(url)
            return response.json()

# ⚠️ Use SyncTask for moderate CPU work or blocking libraries
class ResizeImage(SyncTask[bytes]):
    def handle_sync(self) -> bytes:
        from PIL import Image
        img = Image.open(self.path)
        img.thumbnail((800, 600))
        return img.tobytes()

# 🚀 Use ProcessTask for heavy CPU work (>80% CPU utilization)
class TrainModel(ProcessTask[dict]):
    def handle_process(self) -> dict:
        import numpy as np
        # Heavy computation with independent GIL
        result = np.linalg.inv(large_matrix)
        return {"accuracy": 0.95}
```

### Performance Characteristics

| Mode | Concurrency | Memory Overhead | Best Throughput |
|------|------------|-----------------|------------------|
| **BaseTask** | 1000s concurrent | Minimal (~KB per task) | I/O-bound workloads |
| **SyncTask** | Thread pool limited | Moderate (~MB per thread) | Mixed I/O + CPU |
| **ProcessTask** | CPU core limited | High (~50MB+ per process) | CPU-bound workloads |

### When to Use Each Type

**BaseTask (Default - Use for 90% of tasks):**

✅ I/O-bound operations (API calls, database queries, file operations)  
✅ Tasks that spend time waiting (network, disk, external services)  
✅ Async libraries available (httpx, aiohttp, asyncpg, etc.)  
✅ Need high concurrency (1000s of tasks)  
✅ CPU usage < 10%

**SyncTask (Use for blocking code):**

✅ Using blocking/sync-only libraries (requests, PIL, pandas)  
✅ Moderate CPU work (10-80% utilization)  
✅ Don't want to convert sync code to async  
✅ Thread pool size sufficient for your concurrency needs

**ProcessTask (Use sparingly for heavy CPU work):**

✅ CPU utilization > 80% (verified with profiling)  
✅ Task duration > 100ms (amortizes process overhead)  
✅ All arguments and return values are picklable  
✅ No shared memory needed (processes are isolated)  

❌ Don't use for I/O-bound tasks (use `Task` instead)  
❌ Don't use for short tasks < 100ms (overhead not worth it)  
❌ Don't use with unpicklable objects (will fail at runtime)

---

## Task Configuration Options

**Available Configuration:**

| Option        | Type          | Default     | Description                                 |
| ------------- | ------------- | ----------- | ------------------------------------------- |
| `queue`       | `str`         | `"default"` | Queue name for task                         |
| `max_retries` | `int`         | `3`         | Maximum retry attempts                      |
| `retry_delay` | `int`         | `60`        | Seconds to wait between retries             |
| `timeout`     | `int \| None` | `None`      | Task timeout in seconds (None = no timeout) |

**Configuration Methods:**

```python
# 1. Decorator configuration (function tasks)
@task(queue='emails', max_retries=5, retry_delay=120, timeout=30)
async def send_email(to: str, subject: str):
    pass

# 2. Class attributes (class tasks)
class ProcessPayment(BaseTask[bool]):
    queue = "payments"
    max_retries = 3
    retry_delay = 60
    timeout = 30

# 3. Method chaining (runtime configuration)
await task_instance.on_queue("high").retry_after(120).delay(60).dispatch()

# 4. Dispatch parameters
await send_email.dispatch(to="user@example.com", subject="Hello", delay=60)
```

**Task Metadata:**

Tasks automatically track metadata:

- `_task_id`: UUID string for task identification
- `_attempts`: Current retry attempt count (0-indexed)
- `_dispatched_at`: ISO format datetime when task was first queued

Access metadata in task methods:

```python
class MyTask(BaseTask[None]):
    async def handle(self) -> None:
        print(f"Task ID: {self._task_id}")
        print(f"Attempt: {self._attempts}")
        print(f"Dispatched at: {self._dispatched_at}")
```
