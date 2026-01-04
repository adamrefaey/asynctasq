# Class-Based Tasks: Complete Examples Guide

## Overview

**Prerequisites:**
- AsyncTasQ installed: `uv add asynctasq` or `pip install asynctasq`
- A queue driver configured (Redis, PostgreSQL, MySQL, SQS, or RabbitMQ)
- Workers running to execute tasks (see [Running Workers](../running-workers.md))

This guide covers **all capabilities** of class-based tasks in AsyncTasQ. Everything you need is documented here - no need to visit other docs.

Class-based tasks use base classes (`AsyncTask`, `SyncTask`, `AsyncProcessTask`, or `SyncProcessTask`) to create reusable, testable tasks with lifecycle hooks and advanced configuration. They provide more structure than function-based tasks and are ideal for complex task logic, testing, and reusability.

For conceptual information about task types and execution modes, see [Task Definitions](../task-definitions.md).

**Note:** Example snippets in this guide use the project's event loop runner helper. For runnable examples, import it as:

```python
from asynctasq import run
```

## Table of Contents

- [Basic Usage](#basic-usage)
- [Class Definition Syntax](#class-definition-syntax)
- [Configuration](#configuration)
- [Lifecycle Hooks](#lifecycle-hooks)
- [Dispatching Tasks](#dispatching-tasks)
- [All Four Task Types](#all-four-task-types)
- [Method Chaining](#method-chaining)
- [Task Metadata](#task-metadata)
- [Real-World Examples](#real-world-examples)
- [Complete Working Example](#complete-working-example)
- [Best Practices](#best-practices)

---

## Basic Usage

### Simple AsyncTask

The simplest class-based task extends `AsyncTask` and implements the `execute()` method. All parameters passed to the constructor are automatically available as instance attributes:

```python
import asyncio
from asynctasq import init, AsyncTask

# Configure the queue driver - choose one of three options:
# Option 1: .env file (recommended)
# Create .env with: ASYNCTASQ_DRIVER=redis
init()  # Automatically loads from .env

# Option 2: Code configuration (for quick testing)
init({'driver': 'redis'})

# For complete configuration options, see: https://github.com/adamrefaey/asynctasq/blob/main/docs/configuration.md

# Define a simple task class
class SendNotification(AsyncTask[str]):
    """Send a notification message."""

    def __init__(self, message: str, **kwargs):
        super().__init__(**kwargs)
        self.message = message

    async def execute(self) -> str:
        print(f"Notification: {self.message}")
        await asyncio.sleep(0.1)  # Simulate async work
        return f"Sent: {self.message}"

# Dispatch the task
async def main():
    task_id = await SendNotification(message="Hello, World!").dispatch()
    print(f"Task dispatched with ID: {task_id}")
    # Note: Task will be executed by a worker process

if __name__ == "__main__":
    from asynctasq import run

    run(main())
```

**Important:** After dispatching tasks, you must run a worker process to execute them. See [Running Workers](https://github.com/adamrefaey/asynctasq/blob/main/docs/running-workers.md) for details.

### Task with Parameters

AsyncTasQ provides **two patterns** for passing parameters to tasks:

#### Pattern 1: Automatic Parameter Passing (Recommended for Simple Tasks)

The simplest approach is to let AsyncTasQ automatically handle parameter assignment. Any keyword arguments passed during instantiation become instance attributes:

```python
from asynctasq import init, AsyncTask

# Configure (code, environment variables, or .env file)
init({'driver': 'redis'})

class ProcessData(AsyncTask[int]):
    """Process data and return sum - no __init__ needed!"""

    async def execute(self) -> int:
        """Access parameters as instance attributes."""
        return sum(self.data)

# Dispatch - parameters automatically become attributes
async def main():
    task_id = await ProcessData(data=[1, 2, 3, 4, 5]).dispatch()
    print(f"Task dispatched: {task_id}")

if __name__ == "__main__":
    from asynctasq import run

    run(main())
```

**How it works:** `BaseTask.__init__()` accepts any keyword arguments and automatically sets them as instance attributes. No custom `__init__` needed!

#### Pattern 2: Custom `__init__` (For Validation or Transformation)

Use a custom `__init__` when you need to validate, transform, or provide default values for parameters:

```python
from asynctasq import init, AsyncTask

# Configure (code, environment variables, or .env file)
init({'driver': 'redis'})

class ProcessData(AsyncTask[int]):
    """Process data with validation."""

    def __init__(self, data: list[int], multiplier: int = 1, **kwargs):
        super().__init__(**kwargs)
        # Validation
        if not data:
            raise ValueError("Data cannot be empty")
        # Transformation
        self.data = [x * multiplier for x in data]

    async def execute(self) -> int:
        """Process the validated/transformed data."""
        return sum(self.data)

# Dispatch
async def main():
    task_id = await ProcessData(data=[1, 2, 3, 4, 5], multiplier=2).dispatch()
    print(f"Task dispatched: {task_id}")

if __name__ == "__main__":
    from asynctasq import run

    run(main())
```

**Important:** When using custom `__init__`:
- Always call `super().__init__(**kwargs)` to ensure proper task initialization
- This sets up task metadata and configuration
- Explicitly assign parameters as instance attributes (e.g., `self.data = data`)

**Which Pattern to Use:**
- ✅ **Pattern 1 (Automatic)**: Simple tasks, no validation needed, straightforward parameter passing
- ✅ **Pattern 2 (Custom __init__)**: Need validation, transformation, default values, or complex initialization logic

#### Reserved Parameter Names

AsyncTasQ reserves certain parameter names that cannot be used as task parameters because they would shadow built-in methods and attributes. Using these names will raise a `ValueError`:

**Reserved Names:**
- `config` - Task configuration object
- `run` - Framework execution method
- `execute` - User-defined task logic method
- `dispatch` - Method to queue tasks
- `failed` - Failure hook method
- `should_retry` - Retry decision hook method
- `on_queue` - Method chaining for queue override
- `delay` - Method chaining for delayed execution
- `retry_after` - Method chaining for retry delay
- `max_attempts` - Method chaining for max attempts
- `timeout` - Method chaining for timeout

**Example of Error:**

```python
from asynctasq import AsyncTask

# ❌ WRONG: Using reserved name 'config' as parameter
class BadTask(AsyncTask[None]):
    async def execute(self) -> None:
        print(self.config)

# This will raise: ValueError: Parameter name 'config' is reserved
await BadTask(config="some_value").dispatch()

# ✅ CORRECT: Use a different parameter name
class GoodTask(AsyncTask[None]):
    async def execute(self) -> None:
        print(self.task_config)

await GoodTask(task_config="some_value").dispatch()
```

**Best Practices:**
- Use descriptive parameter names that don't conflict with framework methods
- If you need configuration-like parameters, use names like `task_config`, `settings`, `options`, etc.
- The framework will raise a clear error message if you accidentally use a reserved name

---

## Class Definition Syntax

### Minimal Task (Uses Defaults)

```python
from asynctasq import AsyncTask

class SimpleTask(AsyncTask[None]):
    """Task with default configuration."""

    async def execute(self) -> None:
        print("Executing simple task")
```

### Task with Class-Level Configuration

```python
from asynctasq import AsyncTask, TaskConfig

class SendEmail(AsyncTask[bool]):
    """Send email with custom configuration."""

    # Class-level configuration (type-safe with TaskConfig)
    config: TaskConfig = {
        "queue": "emails",
        "max_attempts": 5,
        "retry_delay": 120,  # seconds
        "timeout": 30,  # seconds
    }

    def __init__(self, to: str, subject: str, body: str, **kwargs):
        super().__init__(**kwargs)
        self.to = to
        self.subject = subject
        self.body = body

    async def execute(self) -> bool:
        print(f"Sending email to {self.to}: {self.subject}")
        # Email sending logic here
        return True
```

### Task with Type Hints

```python
from asynctasq import AsyncTask, TaskConfig
from typing import Dict, Any

class ProcessOrder(AsyncTask[Dict[str, Any]]):
    """Process an order and return status."""

    # Configuration via config dict (type-safe with TaskConfig)
    config: TaskConfig = {
        "queue": "orders",
    }

    def __init__(self, order_id: int, user_id: int, **kwargs):
        super().__init__(**kwargs)
        self.order_id = order_id
        self.user_id = user_id

    async def execute(self) -> Dict[str, Any]:
        """Process the order."""
        # Order processing logic
        return {
            "order_id": self.order_id,
            "status": "processed",
            "user_id": self.user_id
        }
```

---

## Configuration

Configuration options are set via the `config` class attribute. For complete details on all options, see [Task Definitions - Task Configuration](../task-definitions.md#task-configuration).

### Example Configurations

```python
from asynctasq import AsyncTask, TaskConfig

# Basic queue configuration
class SendEmail(AsyncTask[None]):
    config: TaskConfig = {"queue": "emails"}

# High retry count for critical operations
class ProcessPayment(AsyncTask[bool]):
    config: TaskConfig = {
        "queue": "payments",
        "max_attempts": 10,
        "retry_delay": 30,
    }

# With timeout
class GenerateReport(AsyncTask[str]):
    config: TaskConfig = {
        "queue": "reports",
        "timeout": 3600,  # 1 hour
    }

# Full configuration
class CriticalTask(AsyncTask[dict]):
    config: TaskConfig = {
        "queue": "critical",
        "max_attempts": 10,
        "retry_delay": 60,
        "timeout": 300,
        "visibility_timeout": 600,
    }
```

---

## Lifecycle Hooks

Class-based tasks provide three lifecycle hooks for complete control over task execution:

1. **`execute()`** - Main task logic (required)
2. **`failed()`** - Called when task fails after all retries (optional)
3. **`should_retry()`** - Custom retry logic (optional)

### The `execute()` Method

The `execute()` method is where your main task logic goes. It's the only required method:

```python
from asynctasq import AsyncTask, TaskConfig

class ProcessOrder(AsyncTask[bool]):
    config: TaskConfig = {
        "queue": "orders",
    }

    def __init__(self, order_id: int, **kwargs):
        super().__init__(**kwargs)
        self.order_id = order_id

    async def execute(self) -> bool:
        """Main task execution logic."""
        print(f"Processing order {self.order_id}")
        # Your business logic here
        await self._validate_order()
        await self._charge_payment()
        await self._fulfill_order()
        return True

    async def _validate_order(self):
        """Private helper method."""
        pass

    async def _charge_payment(self):
        """Private helper method."""
        pass

    async def _fulfill_order(self):
        """Private helper method."""
        pass
```

### The `failed()` Hook

The `failed()` method is called when a task fails after exhausting all retry attempts. Use it for cleanup, logging, alerting, or compensation:

```python
from asynctasq import AsyncTask, TaskConfig
import logging

logger = logging.getLogger(__name__)

class ProcessPayment(AsyncTask[bool]):
    config: TaskConfig = {
        "queue": "payments",
        "max_attempts": 3,
    }

    def __init__(self, user_id: int, amount: float, **kwargs):
        super().__init__(**kwargs)
        self.user_id = user_id
        self.amount = amount

    async def execute(self) -> bool:
        """Process payment."""
        # Payment processing logic
        if self.amount < 0:
            raise ValueError("Amount cannot be negative")
        return True

    async def failed(self, exception: Exception) -> None:
        """Handle permanent failure after all retries."""
        logger.error(
            f"Payment failed permanently for user {self.user_id}: {exception}",
            exc_info=True
        )

        # Compensation: Refund if already charged
        await self._refund_if_charged()

        # Alerting: Notify administrators
        await self._notify_admins(exception)

        # Cleanup: Update order status
        await self._mark_order_failed()

    async def _refund_if_charged(self):
        """Refund user if payment was already charged."""
        pass

    async def _notify_admins(self, exception: Exception):
        """Notify administrators of failure."""
        pass

    async def _mark_order_failed(self):
        """Mark order as failed in database."""
        pass
```

**Common Use Cases for `failed()`:**

- Logging errors to external systems
- Sending alerts to monitoring services
- Compensating for partial operations (refunds, rollbacks)
- Updating database records to reflect failure
- Notifying users of permanent failures

### The `should_retry()` Hook

The `should_retry()` method allows you to implement custom retry logic based on the exception type. Return `True` to retry, `False` to fail immediately:

```python
from asynctasq import AsyncTask, TaskConfig
import httpx

class CallExternalAPI(AsyncTask[dict]):
    config: TaskConfig = {
        "queue": "api",
        "max_attempts": 5,
    }

    def __init__(self, url: str, **kwargs):
        super().__init__(**kwargs)
        self.url = url

    async def execute(self) -> dict:
        """Call external API."""
        async with httpx.AsyncClient() as client:
            response = await client.get(self.url, timeout=10.0)
            response.raise_for_status()
            return response.json()

    def should_retry(self, exception: Exception) -> bool:
        """Custom retry logic based on exception type."""
        # Don't retry validation errors (4xx)
        if isinstance(exception, httpx.HTTPStatusError):
            if 400 <= exception.response.status_code < 500:
                return False  # Client errors - don't retry

        # Always retry network errors (5xx, timeouts, connection errors)
        if isinstance(exception, (httpx.TimeoutException, httpx.ConnectError)):
            return True

        # Retry server errors (5xx)
        if isinstance(exception, httpx.HTTPStatusError):
            if exception.response.status_code >= 500:
                return True

        # Default: retry
        return True
```

**Common Retry Patterns:**

```python
from asynctasq import AsyncTask

class SmartRetryTask(AsyncTask[None]):
    """Example of various retry patterns."""

    def should_retry(self, exception: Exception) -> bool:
        # Pattern 1: Don't retry validation errors
        if isinstance(exception, ValueError):
            return False

        # Pattern 2: Always retry network errors
        if isinstance(exception, (ConnectionError, TimeoutError)):
            return True

        # Pattern 3: Retry based on exception message
        if "temporary" in str(exception).lower():
            return True

        # Pattern 4: Retry based on attempt count (1-indexed)
        if self._current_attempt < 3:  # (first run + 2 retries)
            return True

        # Pattern 5: Retry based on custom attribute
        if hasattr(exception, 'retryable') and exception.retryable:
            return True

        # Default: retry
        return True
```

### Complete Lifecycle Example

```python
from asynctasq import AsyncTask, TaskConfig
import logging

logger = logging.getLogger(__name__)

class ProcessOrder(AsyncTask[dict]):
    """Complete example with all lifecycle hooks."""

    config: TaskConfig = {
        "queue": "orders",
        "max_attempts": 3,
        "retry_delay": 60,
    }

    def __init__(self, order_id: int, user_id: int, **kwargs):
        super().__init__(**kwargs)
        self.order_id = order_id
        self.user_id = user_id

    async def execute(self) -> dict:
        """Main task logic."""
        logger.info(f"Processing order {self.order_id} for user {self.user_id}")

        # Step 1: Validate
        await self._validate_order()

        # Step 2: Charge payment
        await self._charge_payment()

        # Step 3: Fulfill order
        await self._fulfill_order()

        return {
            "order_id": self.order_id,
            "status": "completed"
        }

    def should_retry(self, exception: Exception) -> bool:
        """Custom retry logic."""
        # Don't retry validation errors
        if isinstance(exception, ValueError):
            logger.warning(f"Validation error - not retrying: {exception}")
            return False

        # Always retry network/connection errors
        if isinstance(exception, (ConnectionError, TimeoutError)):
            logger.info(f"Network error - will retry: {exception}")
            return True

        # Default: retry
        return True

    async def failed(self, exception: Exception) -> None:
        """Handle permanent failure."""
        logger.error(
            f"Order {self.order_id} failed permanently: {exception}",
            exc_info=True
        )

        # Compensation
        await self._refund_payment()

        # Update status
        await self._mark_order_failed()

        # Notify user
        await self._notify_user_failure()

    # Helper methods
    async def _validate_order(self):
        """Validate order."""
        pass

    async def _charge_payment(self):
        """Charge payment."""
        pass

    async def _fulfill_order(self):
        """Fulfill order."""
        pass

    async def _refund_payment(self):
        """Refund payment."""
        pass

    async def _mark_order_failed(self):
        """Mark order as failed."""
        pass

    async def _notify_user_failure(self):
        """Notify user of failure."""
        pass
```

---

## Dispatching Tasks

Tasks are dispatched by creating an instance and calling `.dispatch()`. The method returns a unique task ID (UUID string) for tracking.

**Important Notes:**

- Tasks are dispatched asynchronously and return immediately
- The task ID is generated before the task is queued
- Tasks will not execute until a worker process is running
- Use the task ID to track task status in your monitoring system

### Direct Dispatch (Recommended)

The simplest way to dispatch a task:

```python
from asynctasq import AsyncTask, TaskConfig

class SendEmail(AsyncTask[bool]):
    config: TaskConfig = {
        "queue": "emails",
    }

    def __init__(self, to: str, subject: str, body: str, **kwargs):
        super().__init__(**kwargs)
        self.to = to
        self.subject = subject
        self.body = body

    async def execute(self) -> bool:
        print(f"Sending email to {self.to}")
        return True

# Dispatch immediately
async def main():
    task_id = await SendEmail(
        to="user@example.com",
        subject="Welcome",
        body="Welcome to our platform!"
    ).dispatch()
    print(f"Task ID: {task_id}")
```

### Dispatch with Delay

You can delay task execution using method chaining:

```python
from asynctasq import AsyncTask, TaskConfig

class SendReminder(AsyncTask[None]):
    config: TaskConfig = {
        "queue": "reminders",
    }

    def __init__(self, user_id: int, message: str, **kwargs):
        super().__init__(**kwargs)
        self.user_id = user_id
        self.message = message

    async def execute(self) -> None:
        print(f"Sending reminder to user {self.user_id}: {self.message}")

# Dispatch with 60 second delay
async def main():
    task_id = await SendReminder(
        user_id=123,
        message="Don't forget to complete your profile!"
    ).delay(60).dispatch()
    print(f"Task will execute after 60 seconds: {task_id}")
```

**Note:** The `delay()` method specifies seconds until execution (must be greater than 0). For more complex scheduling, consider using a separate scheduling system.

---

## All Four Task Types

AsyncTasQ provides four task execution modes optimized for different workloads. For detailed comparison, concurrency characteristics, and comprehensive guidance on when to use each mode, see [Task Definitions - Task Types and Execution Modes](../task-definitions.md#task-types-and-execution-modes).

**Quick Reference:**
- **`AsyncTask`** - Async I/O-bound (API calls, async DB) - Use for 90% of tasks
- **`SyncTask`** - Sync/blocking I/O (`requests`, sync DB drivers)
- **`AsyncProcessTask`** - Async CPU-intensive work
- **`SyncProcessTask`** - Sync CPU-intensive work (>80% CPU utilization)

### Examples of Each Type

#### AsyncTask (Async I/O - Most Common)

```python
from asynctasq import AsyncTask, TaskConfig
import httpx

class FetchUserData(AsyncTask[dict]):
    config: TaskConfig = {"queue": "api"}

    def __init__(self, user_id: int, **kwargs):
        super().__init__(**kwargs)
        self.user_id = user_id

    async def execute(self) -> dict:
        async with httpx.AsyncClient() as client:
            response = await client.get(f"https://api.example.com/users/{self.user_id}")
            return response.json()
```

#### SyncTask (Sync/Blocking I/O)

```python
from asynctasq import SyncTask, TaskConfig
import requests

class FetchWebPage(SyncTask[str]):
    config: TaskConfig = {"queue": "web-scraping"}

    def __init__(self, url: str, **kwargs):
        super().__init__(**kwargs)
        self.url = url

    def execute(self) -> str:
        response = requests.get(self.url)
        return response.text
```

#### AsyncProcessTask (Async CPU-intensive)

```python
from asynctasq import AsyncProcessTask, TaskConfig
import aiofiles

class ProcessVideoAsync(AsyncProcessTask[dict]):
    config: TaskConfig = {"queue": "video-processing", "timeout": 600}

    def __init__(self, video_path: str, **kwargs):
        super().__init__(**kwargs)
        self.video_path = video_path

    async def execute(self) -> dict:
        async with aiofiles.open(self.video_path, 'rb') as f:
            data = await f.read()
        frames_processed = await self._process_frames(data)
        return {"frames": frames_processed}

    async def _process_frames(self, data: bytes) -> int:
        return len(data) // 1024
```

#### SyncProcessTask (Sync CPU-intensive)

```python
from asynctasq import SyncProcessTask, TaskConfig
import numpy as np

class ProcessLargeDataset(SyncProcessTask[dict]):
    config: TaskConfig = {"queue": "data-processing", "timeout": 600}

    def __init__(self, data: list[float], **kwargs):
        super().__init__(**kwargs)
        self.data = data

    def execute(self) -> dict:
        arr = np.array(self.data)
        result = np.fft.fft(arr)
        return {"mean": float(result.mean()), "std": float(result.std())}
```


---

## Method Chaining

Method chaining allows you to override task configuration at dispatch time. This is useful when you need different settings for specific dispatches without creating separate task classes.

**Available Chain Methods:**

- `.on_queue(queue_name)`: Override the queue name
- `.delay(seconds)`: Add execution delay (in seconds, must be > 0)
- `.retry_after(seconds)`: Override retry delay (in seconds)
- `.max_attempts(attempts)`: Override maximum retry attempts (including initial attempt)
- `.timeout(seconds)`: Override task execution timeout (in seconds, or `None` for no timeout)
- `.visibility_timeout(seconds)`: Override crash recovery timeout (in seconds)
- `.dispatch()`: Final method that actually dispatches the task

**Note:** Method chaining methods return `self` for fluent API usage. The order of chaining doesn't matter, but `.dispatch()` must be called last.

**Syntax Pattern:**

```python
await TaskClass(param=value).on_queue("queue").delay(60).dispatch()
#     ^^^^^^^^^^^^^^^^^^^^^^^^  ^^^^^^^^^^^^^^^^^^^^^^^^^^^^
#     Instance creation          Chain methods
```

### Basic Method Chaining

```python
from asynctasq import AsyncTask, TaskConfig

class ProcessData(AsyncTask[None]):
    config: TaskConfig = {
        "queue": "default",
    }

    def __init__(self, data: str, **kwargs):
        super().__init__(**kwargs)
        self.data = data

    async def execute(self) -> None:
        print(f"Processing: {self.data}")

# Chain delay and dispatch
async def main():
    # Call constructor, then chain methods
    task_id = await ProcessData(data="data").delay(60).dispatch()
    # Task will execute after 60 seconds
```

### Queue Override with Chaining

```python
from asynctasq import AsyncTask, TaskConfig

class SendNotification(AsyncTask[None]):
    config: TaskConfig = {
        "queue": "default",
    }

    def __init__(self, message: str, **kwargs):
        super().__init__(**kwargs)
        self.message = message

    async def execute(self) -> None:
        print(f"Notification: {self.message}")

# Override queue at dispatch time
async def main():
    # Send to high-priority queue
    task_id = await SendNotification(message="urgent").on_queue("high-priority").dispatch()

    # Send to low-priority queue with delay
    task_id = await SendNotification(message="reminder").on_queue("low-priority").delay(300).dispatch()
```

### Retry Configuration with Chaining

Override the retry delay for specific dispatches:

```python
from asynctasq import AsyncTask, TaskConfig

class CallAPI(AsyncTask[dict]):
    config: TaskConfig = {
        "queue": "api",
        "max_attempts": 3,
        "retry_delay": 60,
    }

    def __init__(self, endpoint: str, **kwargs):
        super().__init__(**kwargs)
        self.endpoint = endpoint

    async def execute(self) -> dict:
        print(f"Calling {self.endpoint}")
        return {}

# Override retry delay at dispatch time
async def main():
    # Use custom retry delay for this specific dispatch
    # This only affects the delay between retries, not max_attempts
    task_id = await CallAPI(endpoint="https://api.example.com/data") \
        .retry_after(120) \
        .dispatch()
    # Will retry with 120 second delays instead of default 60
```

### Complex Chaining - Override All Parameters

You can override **all** task configuration parameters at dispatch time using method chaining:

```python
from asynctasq import AsyncTask, TaskConfig

class ComplexTask(AsyncTask[None]):
    config: TaskConfig = {
        "queue": "default",
        "max_attempts": 3,
        "retry_delay": 60,
        "timeout": 30,
        "visibility_timeout": 300,
    }

    def __init__(self, data: dict, **kwargs):
        super().__init__(**kwargs)
        self.data = data

    async def execute(self) -> None:
        print(f"Processing: {self.data}")

# Override ALL parameters via chaining
async def main():
    task_id = await ComplexTask(data={"key": "value"}) \
        .on_queue("critical") \
        .max_attempts(10) \
        .timeout(120) \
        .retry_after(180) \
        .visibility_timeout(600) \
        .delay(30) \
        .dispatch()
    # All parameters overridden:
    # - Queue: 'critical' (was 'default')
    # - Max attempts: 10 (was 3)
    # - Timeout: 120s (was 30s)
    # - Retry delay: 180s (was 60s)
    # - Visibility timeout: 600s (was 300s)
    # - Execution delay: 30s
```

**Important Notes:**

- **All parameters overridable**: `queue`, `max_attempts`, `timeout`, `retry_delay`, `visibility_timeout`, and `delay` can all be overridden via chaining
- **Method order doesn't matter**: Chain methods in any order (except `.dispatch()` must be last)
- **Type safety**: All chain methods return `Self` for fluent API usage
- **Runtime flexibility**: Override configuration without creating new task classes

---

## Task Metadata

Tasks automatically track metadata that you can access in your task methods:

- `_task_id`: UUID string for task identification (set during dispatch)
- `_current_attempt`: Current retry attempt count (0-indexed: 0 = first attempt, 1 = first retry, etc.)
- `_dispatched_at`: Datetime when task was first queued (may be `None` in some edge cases)
- `correlation_id`: Optional correlation ID for distributed tracing (set via `config`)

**Note:** Metadata is set by the framework during task dispatch and execution. Access these attributes in your `execute()`, `failed()`, or `should_retry()` methods.

### Accessing Metadata

```python
from asynctasq import AsyncTask
from datetime import datetime

class MyTask(AsyncTask[None]):
    async def execute(self) -> None:
        print(f"Task ID: {self._task_id}")
        print(f"Attempt: {self._current_attempt}")  # 1-indexed (1 = first attempt, 2 = first retry)
        if self._dispatched_at:
            print(f"Dispatched at: {self._dispatched_at}")
        else:
            print("Dispatched at: Unknown")
```

**Important - Attempt Counting Behavior:**

The `_current_attempt` counter is **1-indexed** during execution:
- `_current_attempt = 1` - First execution (not a retry)
- `_current_attempt = 2` - First retry
- `_current_attempt = 3` - Second retry
- And so on...

**How it works internally:**
1. Task is created with `_current_attempt = 0`
2. Framework calls `mark_attempt_started()` before execution, which increments to `1`
3. Inside your `execute()` method, `_current_attempt` is `1` (first attempt)
4. If task fails and retries, `_current_attempt` is incremented to `2`, `3`, etc.

This means when you check `_current_attempt` in your task methods (`execute()`, `should_retry()`, `failed()`), it represents the **current execution number** starting from 1.

### Using Metadata for Logging

```python
from asynctasq import AsyncTask, TaskConfig
import logging

logger = logging.getLogger(__name__)

class LoggedTask(AsyncTask[dict]):
    config: TaskConfig = {
        "queue": "default",
    }

    async def execute(self) -> dict:
        logger.info(
            f"Task {self._task_id} executing (attempt {self._current_attempt + 1})",
            extra={
                "task_id": self._task_id,
                "attempt": self._current_attempt,
                "dispatched_at": self._dispatched_at.isoformat() if self._dispatched_at else None
            }
        )
        return {"status": "completed"}
```

### Using Metadata for Conditional Logic

```python
from asynctasq import AsyncTask, TaskConfig

class SmartRetryTask(AsyncTask[None]):
    config: TaskConfig = {
        "max_attempts": 5,
    }

    async def execute(self) -> None:
        # Adjust behavior based on attempt count (1-indexed)
        if self._current_attempt == 1:
            # First attempt - use fast method
            await self._fast_method()
        elif self._current_attempt <= 3:
            # Attempts 2-3 (retries 1-2) - use standard method
            await self._standard_method()
        else:
            # Attempts 4+ (retries 3+) - use fallback method
            await self._fallback_method()

    async def _fast_method(self):
        pass

    async def _standard_method(self):
        pass

    async def _fallback_method(self):
        pass
```

### Using Correlation IDs for Distributed Tracing

Correlation IDs allow you to track related tasks across distributed systems. Set a correlation ID to group related tasks together for monitoring and debugging:

```python
from asynctasq import AsyncTask, TaskConfig

class ProcessOrder(AsyncTask[dict]):
    """Process order with correlation tracking."""

    config: TaskConfig = {
        "queue": "orders",
    }

    async def execute(self) -> dict:
        # Access correlation ID for logging
        correlation_id = self.config.get("correlation_id")
        if correlation_id:
            print(f"Processing order {self.order_id} (trace: {correlation_id})")
        return {"order_id": self.order_id, "status": "processed"}

# Pattern 1: Set correlation ID at class level (all instances share)
class OrderNotification(AsyncTask[None]):
    config: TaskConfig = {
        "queue": "notifications",
        "correlation_id": "order-pipeline-v1",  # All instances share this ID
    }

    async def execute(self) -> None:
        print(f"Trace ID: {self.config['correlation_id']}")

# Pattern 2: Set correlation ID per-task instance for request tracing
async def handle_user_request(user_id: int, request_id: str):
    """Process user request with unique trace ID."""
    # Create task with unique correlation ID
    task = ProcessOrder(order_id=123)
    task.config["correlation_id"] = f"req-{request_id}"
    await task.dispatch()

    # All related tasks can share the same correlation ID
    task2 = OrderNotification()
    task2.config["correlation_id"] = f"req-{request_id}"
    await task2.dispatch()
```

**Use Cases for Correlation IDs:**
- **Request Tracing**: Track all tasks spawned from a single user request
- **Pipeline Tracking**: Group tasks that are part of the same data processing pipeline
- **Debugging**: Filter logs and metrics by correlation ID to debug specific workflows
- **Monitoring**: Track task execution across multiple services and queues

---

## Real-World Examples

### Email Sending Service

```python
import asyncio
from asynctasq import AsyncTask, run
from typing import Optional

class SendEmail(AsyncTask[dict]):
    config: TaskConfig = {
        "queue": "emails",
        "max_attempts": 5,
        "retry_delay": 60,
        "timeout": 30,
    }

    def __init__(
        self,
        to: str,
        subject: str,
        body: str,
        from_email: Optional[str] = None,
        **kwargs
    ):
        super().__init__(**kwargs)
        self.to = to
        self.subject = subject
        self.body = body
        self.from_email = from_email

    async def execute(self) -> dict:
        """Send an email with retry logic."""
        print(f"Sending email to {self.to}: {self.subject}")
        # Email sending logic here
        await asyncio.sleep(0.5)
        return {"status": "sent", "to": self.to}

    async def failed(self, exception: Exception) -> None:
        """Handle email sending failure."""
        print(f"Failed to send email to {self.to}: {exception}")
        # Log to external system, notify admins, etc.

# Dispatch emails
async def main():
    # Immediate email
    await SendEmail(
        to="user@example.com",
        subject="Welcome!",
        body="Welcome to our platform"
    ).dispatch()

    # Delayed welcome email (send after 1 hour)
    await SendEmail(
        to="newuser@example.com",
        subject="Getting Started",
        body="Here's how to get started...",
    ).delay(3600).dispatch()

if __name__ == "__main__":
    run(main())
```

### Payment Processing

```python
import asyncio
from asynctasq import AsyncTask
from decimal import Decimal

class ProcessPayment(AsyncTask[dict]):
    config: TaskConfig = {
        "queue": "payments",
        "max_attempts": 10,
        "retry_delay": 30,
        "timeout": 60,
    }

    def __init__(
        self,
        user_id: int,
        amount: Decimal,
        payment_method: str,
        order_id: int,
        **kwargs
    ):
        super().__init__(**kwargs)
        self.user_id = user_id
        self.amount = amount
        self.payment_method = payment_method
        self.order_id = order_id

    async def execute(self) -> dict:
        """Process payment with high retry count for reliability."""
        print(f"Processing payment: ${self.amount} for user {self.user_id}")
        # Payment processing logic
        # - Validate payment method
        # - Charge card
        # - Update order status
        # - Send confirmation
        return {"status": "completed", "order_id": self.order_id}

    def should_retry(self, exception: Exception) -> bool:
        """Don't retry validation errors."""
        if isinstance(exception, ValueError):
            return False
        return True

    async def failed(self, exception: Exception) -> None:
        """Handle payment failure."""
        print(f"Payment failed for order {self.order_id}: {exception}")
        # Refund if already charged, notify user, etc.

# Dispatch payment
async def main():
    task_id = await ProcessPayment(
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
from asynctasq import run, SyncTask, TaskConfig
from datetime import datetime, timedelta

class GenerateReport(SyncTask[dict]):
    config: TaskConfig = {
        "queue": "reports",
        "timeout": 3600,  # 1 hour timeout
    }

    def __init__(
        self,
        report_type: str,
        start_date: datetime,
        end_date: datetime,
        user_id: int,
        **kwargs
    ):
        super().__init__(**kwargs)
        self.report_type = report_type
        self.start_date = start_date
        self.end_date = end_date
        self.user_id = user_id

    def execute(self) -> dict:
        """Generate report synchronously (CPU-intensive)."""
        import time
        print(f"Generating {self.report_type} report for user {self.user_id}")
        # Heavy computation
        time.sleep(10)
        return {
            "report_type": self.report_type,
            "generated_at": datetime.now().isoformat(),
            "user_id": self.user_id
        }

# Schedule report generation
async def main():
    # Generate report for last month
    end_date = datetime.now()
    start_date = end_date - timedelta(days=30)

    task_id = await GenerateReport(
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
from asynctasq import run, AsyncTask, TaskConfig
from pathlib import Path

class ProcessImage(AsyncTask[dict]):
    config: TaskConfig = {
        "queue": "images",
        "max_attempts": 3,
        "timeout": 300,
    }

    def __init__(
        self,
        image_path: str,
        operations: list[str],
        output_path: str,
        **kwargs
    ):
        super().__init__(**kwargs)
        self.image_path = image_path
        self.operations = operations
        self.output_path = output_path

    async def execute(self) -> dict:
        """Process image with various operations."""
        print(f"Processing image: {self.image_path}")
        # Image processing logic
        # - Resize
        # - Apply filters
        # - Optimize
        # - Save to output_path
        await asyncio.sleep(2)
        return {"output": self.output_path, "operations": self.operations}

# Dispatch image processing
async def main():
    task_id = await ProcessImage(
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
from asynctasq import run, AsyncTask, TaskConfig
import httpx

class DeliverWebhook(AsyncTask[dict]):
    config: TaskConfig = {
        "queue": "webhooks",
        "max_attempts": 5,
        "retry_delay": 120,
        "timeout": 10,
    }

    def __init__(
        self,
        url: str,
        payload: dict,
        headers: dict,
        **kwargs
    ):
        super().__init__(**kwargs)
        self.url = url
        self.payload = payload
        self.headers = headers

    async def execute(self) -> dict:
        """Deliver webhook with retry logic."""
        async with httpx.AsyncClient() as client:
            response = await client.post(
                self.url,
                json=self.payload,
                headers=self.headers,
                timeout=10.0
            )
            response.raise_for_status()
            return {"status_code": response.status_code}

    def should_retry(self, exception: Exception) -> bool:
        """Retry on network errors, not client errors."""
        if isinstance(exception, httpx.HTTPStatusError):
            # Don't retry 4xx errors
            if 400 <= exception.response.status_code < 500:
                return False
        return True

# Dispatch webhook
async def main():
    task_id = await DeliverWebhook(
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
from asynctasq import run, AsyncTask, TaskConfig

class SyncUserData(AsyncTask[dict]):
    config: TaskConfig = {
        "queue": "sync",
        "max_attempts": 3,
        "retry_delay": 300,
    }

    def __init__(
        self,
        user_id: int,
        source_system: str,
        target_system: str,
        **kwargs
    ):
        super().__init__(**kwargs)
        self.user_id = user_id
        self.source_system = source_system
        self.target_system = target_system

    async def execute(self) -> dict:
        """Sync user data between systems."""
        print(f"Syncing user {self.user_id} from {self.source_system} to {self.target_system}")
        # Data synchronization logic
        # - Fetch from source
        # - Transform data
        # - Push to target
        return {"synced": True, "user_id": self.user_id}

# Schedule sync with delay
async def main():
    # Sync after 5 minutes
    task_id = await SyncUserData(
        user_id=123,
        source_system="crm",
        target_system="analytics",
    ).delay(300).dispatch()
    print(f"Sync task dispatched: {task_id}")

if __name__ == "__main__":
    run(main())
```

### Batch Processing

Process multiple items in a single task:

```python
import asyncio
from asynctasq import run, AsyncTask, TaskConfig
from typing import List

class ProcessBatch(AsyncTask[dict]):
    config: TaskConfig = {
        "queue": "batch",
        "timeout": 1800,  # 30 minutes timeout
    }

    def __init__(
        self,
        items: List[dict],
        batch_id: str,
        **kwargs
    ):
        super().__init__(**kwargs)
        self.items = items
        self.batch_id = batch_id

    async def execute(self) -> dict:
        """Process a batch of items."""
        print(f"Processing batch {self.batch_id} with {len(self.items)} items")
        results = []
        for item in self.items:
            # Process each item
            result = await self._process_item(item)
            results.append(result)
        return {"batch_id": self.batch_id, "processed": len(results)}

    async def _process_item(self, item: dict) -> dict:
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

    task_id = await ProcessBatch(
        items=items,
        batch_id="batch-2024-01-15"
    ).dispatch()
    print(f"Batch processing task dispatched: {task_id}")

if __name__ == "__main__":
    run(main())
```

**Best Practices for Batch Processing:**

- **Batch size:** Keep batches reasonably sized (typically 10-100 items) to balance throughput and error isolation
- **Large batches:** For very large batches, consider splitting into smaller batches or processing items individually as separate tasks for better parallelism and error isolation
- **Error handling:** If one item in a batch fails, the entire batch task fails. Consider processing items individually for critical operations
- **Timeout:** Set appropriate timeouts for batch tasks based on expected processing time

---

## Complete Working Example

Here's a complete, runnable example demonstrating multiple class-based task patterns. This example shows:

- Different task configurations (queue, retries, timeout)
- Async and sync tasks
- Direct dispatch and method chaining
- Driver overrides
- Delayed execution
- Lifecycle hooks

**Important:** This example uses the `redis` driver. For production, you can also use `postgres`, `mysql`, or `sqs`. Also, remember to run workers to process the dispatched tasks (see [Running Workers](https://github.com/adamrefaey/asynctasq/blob/main/docs/running-workers.md)).

```python
import asyncio
from asynctasq import init, AsyncTask, run

# Configure - choose one:
# Option 1: .env file (recommended)
# Create .env with: ASYNCTASQ_DRIVER=redis
# init()
# Option 2: Environment (set ASYNCTASQ_DRIVER=redis)
# init()
# Option 3: Code config (for quick testing)
init({'driver': 'redis'})

# Define tasks with different configurations
class SendEmail(AsyncTask[str]):
    config: TaskConfig = {
        "queue": "emails",
        "max_attempts": 3,
        "retry_delay": 60,
    }

    def __init__(self, to: str, subject: str, body: str, **kwargs):
        super().__init__(**kwargs)
        self.to = to
        self.subject = subject
        self.body = body

    async def execute(self) -> str:
        """Send an email."""
        print(f"📧 Sending email to {self.to}: {self.subject}")
        await asyncio.sleep(0.1)
        return f"Email sent to {self.to}"

class ProcessPayment(AsyncTask[dict]):
    config: TaskConfig = {
        "queue": "payments",
        "max_attempts": 10,
        "retry_delay": 30,
        "timeout": 60,
    }

    def __init__(self, user_id: int, amount: float, **kwargs):
        super().__init__(**kwargs)
        self.user_id = user_id
        self.amount = amount

    async def execute(self) -> dict:
        """Process a payment."""
        print(f"💳 Processing payment: ${self.amount} for user {self.user_id}")
        await asyncio.sleep(0.2)
        return {"status": "completed", "user_id": self.user_id}

    async def failed(self, exception: Exception) -> None:
        """Handle payment failure."""
        print(f"❌ Payment failed for user {self.user_id}: {exception}")

class GenerateReport(SyncTask[str]):
    config: TaskConfig = {
        "queue": "reports",
        "timeout": 300,
    }

    def __init__(self, report_id: int, **kwargs):
        super().__init__(**kwargs)
        self.report_id = report_id

    def execute(self) -> str:
        """Generate a report (sync function)."""
        import time
        print(f"📊 Generating report {self.report_id}")
        time.sleep(1)
        return f"Report {self.report_id} generated"

class CriticalTask(AsyncTask[None]):
    config = {"queue": "critical", "driver": "redis"}  # Override driver (requires Redis configured)

    def __init__(self, data: dict, **kwargs):
        super().__init__(**kwargs)
        self.data = data

    async def execute(self) -> None:
        """еritical task using Redis."""
        print(f"🚨 Critical task: {self.data}")
        await asyncio.sleep(0.1)

# Main function demonstrating all dispatch methods
async def main():
    print("=== Class-Based Tasks Examples ===\n")

    # 1. Direct dispatch
    print("1. Direct dispatch:")
    task_id = await SendEmail(
        to="user@example.com",
        subject="Welcome",
        body="Welcome!"
    ).dispatch()
    print(f"   Task ID: {task_id}\n")

    # 2. Dispatch with delay
    print("2. Dispatch with delay:")
    task_id = await SendEmail(
        to="user@example.com",
        subject="Reminder",
        body="Don't forget!",
    ).delay(60).dispatch()
    print(f"   Task ID: {task_id} (will execute in 60s)\n")

    # 3. Method chaining
    print("3. Method chaining:")
    task_id = await SendEmail(
        to="user@example.com",
        subject="Chained",
        body="Message"
    ).delay(30).dispatch()
    print(f"   Task ID: {task_id}\n")

    # 4. Payment processing
    print("4. Payment processing:")
    task_id = await ProcessPayment(user_id=123, amount=99.99).dispatch()
    print(f"   Task ID: {task_id}\n")

    # 5. Sync task
    print("5. Sync task:")
    task_id = await GenerateReport(report_id=1).dispatch()
    print(f"   Task ID: {task_id}\n")

    # 6. Driver override (commented out - requires Redis configuration)
    print("6. Driver override:")
    print("   (Skipped - requires Redis to be configured)")
    # Uncomment to test driver override:
    # task_id = await CriticalTask(data={"key": "value"}).dispatch()
    # print(f"   Task ID: {task_id}\n")

    print("=== All tasks dispatched! ===")
    print("Note: Run workers to process these tasks. See running-workers.md for details.")

if __name__ == "__main__":
    run(main())
```

---

## Summary

Class-based tasks in AsyncTasQ provide a powerful, flexible way to create reusable, testable background tasks with complete control over execution lifecycle.

### Key Features

✅ **Lifecycle hooks** - `execute()`, `failed()`, `should_retry()` for complete control
✅ **Reusable and testable** - Class-based design for better organization
✅ **Flexible configuration** - Queue, retries, timeout, driver via class attributes
✅ **Multiple dispatch methods** - Direct dispatch, delayed execution, method chaining
✅ **Async and sync support** - `AsyncTask` for async, `SyncTask` for blocking operations
✅ **ORM integration** - Automatic serialization for SQLAlchemy, Django, Tortoise
✅ **Driver overrides** - Per-task driver selection (string or instance)
✅ **Method chaining** - Fluent API for runtime configuration overrides
✅ **Type safety** - Full type hints and Generic support
✅ **Task metadata** - Access task ID, attempts, dispatched time
✅ **Payload optimization** - ORM models serialized as lightweight references

### Quick Start

1. **Configure your driver (choose one method):**

    ```python
    from asynctasq import init
    # Option 1: .env file (recommended)
    # Create .env with: ASYNCTASQ_DRIVER=redis
    # init()
    # Option 2: Environment variable (ASYNCTASQ_DRIVER=redis)
    # init()
    # Option 3: Code (for quick testing)
    init({'driver': 'redis'})  # or 'postgres', 'mysql', 'sqs'
    ```

2. **Define a task class:**

   ```python
   from asynctasq import AsyncTask, TaskConfig

   class SendEmail(AsyncTask[bool]):
       config: TaskConfig = {
           "queue": "emails",
       }

       def __init__(self, to: str, subject: str, **kwargs):
           super().__init__(**kwargs)
           self.to = to
           self.subject = subject

       async def execute(self) -> bool:
           print(f"Sending email to {self.to}")
           return True
   ```

3. **Dispatch it:**

   ```python
   task_id = await SendEmail(to="user@example.com", subject="Hello").dispatch()
   print(f"Task ID: {task_id}")
   ```

4. **Run workers** to process tasks (see [Running Workers](https://github.com/adamrefaey/asynctasq/blob/main/docs/running-workers.md))

**Important:** Tasks will not execute until a worker process is running. The `dispatch()` call returns immediately after queuing the task - it does not wait for task execution. The returned task ID can be used to track task status in your monitoring system.

### Next Steps

- Learn about [function-based tasks](https://github.com/adamrefaey/asynctasq/blob/main/docs/examples/function-based-tasks.md) for simpler task definitions
- Explore [queue drivers](https://github.com/adamrefaey/asynctasq/blob/main/docs/queue-drivers.md) for production setup
- Check [ORM integrations](https://github.com/adamrefaey/asynctasq/blob/main/docs/orm-integrations.md) for database model support
- Review [best practices](https://github.com/adamrefaey/asynctasq/blob/main/docs/best-practices.md) for production usage

All examples above are ready to use - just configure your driver and start dispatching tasks!

---

## Common Patterns and Best Practices

### Error Handling

Tasks should handle their own errors gracefully. The framework will retry failed tasks according to the `max_attempts` configuration and `should_retry()` logic:

```python
from asynctasq import AsyncTask, TaskConfig
import httpx

class CallExternalAPI(AsyncTask[dict]):
    config: TaskConfig = {
        "queue": "api",
        "max_attempts": 3,
        "retry_delay": 60,
    }

    def __init__(self, url: str, **kwargs):
        super().__init__(**kwargs)
        self.url = url

    async def execute(self) -> dict:
        """Call external API with automatic retry on failure."""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(self.url, timeout=10.0)
                response.raise_for_status()
                return response.json()
        except httpx.HTTPError as e:
            # Log error for debugging
            print(f"API call failed: {e}")
            # Re-raise to trigger retry mechanism
            raise

    def should_retry(self, exception: Exception) -> bool:
        """Retry on network errors, not client errors."""
        if isinstance(exception, httpx.HTTPStatusError):
            if 400 <= exception.response.status_code < 500:
                return False  # Don't retry client errors
        return True  # Retry server errors and network errors
```

### Task ID Tracking

Store task IDs for monitoring and debugging. Task IDs are UUID strings that uniquely identify each dispatched task:

```python
from asynctasq import AsyncTask, TaskConfig

class SendWelcomeEmail(AsyncTask[None]):
    config: TaskConfig = {
        "queue": "emails",
    }

    def __init__(self, user_id: int, **kwargs):
        super().__init__(**kwargs)
        self.user_id = user_id

    async def execute(self) -> None:
        # Email sending logic
        pass

class CreateUserAccount:
    """Service class that dispatches tasks."""

    async def create_user(self, email: str, name: str):
        # Create user in database
        user = await self._create_user(email, name)

        # Dispatch welcome email and store task ID
        email_task_id = await SendWelcomeEmail(user_id=user.id).dispatch()

        # Store task ID in database for tracking
        await self._store_task_reference(user.id, "welcome_email", email_task_id)

        return user
```

### Configuration Best Practices

- **Use descriptive queue names:** `'emails'`, `'payments'`, `'notifications'` instead of `'queue1'`, `'queue2'`
- **Set appropriate timeouts:** Prevent tasks from running indefinitely
- **Configure retries based on task type:** Critical tasks need more retries than validation tasks
- **Use driver overrides sparingly:** Only when necessary for specific requirements
- **Group related tasks:** Use consistent naming and queue organization

### Lifecycle Hook Best Practices

- **Keep `execute()` focused:** Main business logic only, delegate to helper methods
- **Use `failed()` for cleanup:** Compensation, logging, alerting
- **Implement `should_retry()` for smart retries:** Don't retry validation errors, always retry network errors
- **Log in lifecycle hooks:** Use task metadata (`_task_id`, `_current_attempt`) for better debugging

### Performance Tips

- **Prefer async tasks** (`Task`) for I/O-bound operations
- **Use sync tasks** (``) only when necessary (blocking libraries, CPU-bound work)
- **Keep task payloads small:** For supported ORMs (SQLAlchemy, Django, Tortoise), the framework automatically converts model instances to lightweight references (class + primary key) during serialization, so you don't need to manually extract IDs. Pass model instances directly - the framework handles serialization automatically
- **Batch related operations** when appropriate, but avoid overly large batches
- **Monitor queue sizes** and adjust worker concurrency accordingly
- **Use method chaining** for runtime overrides instead of creating multiple task classes

### Testing Class-Based Tasks

Class-based tasks are easier to test than function-based tasks because you can instantiate them directly and call methods:

```python
import pytest
from asynctasq import AsyncTask, TaskConfig

class SendEmail(AsyncTask[bool]):
    config: TaskConfig = {
        "queue": "emails",
    }

    def __init__(self, to: str, subject: str, **kwargs):
        super().__init__(**kwargs)
        self.to = to
        self.subject = subject

    async def execute(self) -> bool:
        # Email sending logic
        return True

# Test the task directly
@pytest.mark.asyncio
async def test_send_email():
    task = SendEmail(to="test@example.com", subject="Test")
    result = await task.execute()
    assert result is True
    assert task.to == "test@example.com"
    assert task.subject == "Test"

# Test lifecycle hooks
@pytest.mark.asyncio
async def test_send_email_failed():
    task = SendEmail(to="test@example.com", subject="Test")
    # Simulate failure
    await task.failed(ValueError("Email service unavailable"))
    # Verify cleanup logic executed
```

### Organizing Task Classes

- **Group by domain:** `tasks/emails.py`, `tasks/payments.py`, `tasks/notifications.py`
- **Use consistent naming:** `SendEmail`, `ProcessPayment`, `GenerateReport`
- **Document task purpose:** Use docstrings to explain what each task does
- **Share common logic:** Use base classes or mixins for shared functionality

All examples above are ready to use - just configure your driver and start dispatching tasks!
