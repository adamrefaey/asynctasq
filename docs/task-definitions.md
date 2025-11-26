# Task Definitions

Async Task supports two task definition styles: **function-based** (simple, inline) and **class-based** (reusable, testable).

## Function-Based Tasks

Use the `@task` decorator for simple, inline task definitions.

**Basic Function Task:**

```python
from async_task.core.task import task

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

Use the `Task` base class for complex tasks with lifecycle hooks and custom retry logic.

**Basic Class Task:**

```python
from async_task.core.task import Task

class ProcessPayment(Task[bool]):
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
class ProcessPayment(Task[bool]):
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
from async_task.core.task import SyncTask

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
class ProcessPayment(Task[bool]):
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
class MyTask(Task[None]):
    async def handle(self) -> None:
        print(f"Task ID: {self._task_id}")
        print(f"Attempt: {self._attempts}")
        print(f"Dispatched at: {self._dispatched_at}")
```
