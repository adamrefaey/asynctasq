# Error Handling Architecture

## Table of Contents

- [Error Handling Architecture](#error-handling-architecture)
  - [Table of Contents](#table-of-contents)
  - [Overview](#overview)
  - [Architecture Diagram](#architecture-diagram)
  - [Layer Responsibilities](#layer-responsibilities)
    - [1. Framework Layer (TaskExecutor)](#1-framework-layer-taskexecutor)
    - [2. User Layer (BaseTask)](#2-user-layer-basetask)
  - [Error Flow Examples](#error-flow-examples)
    - [Example 1: Successful Execution (No Error)](#example-1-successful-execution-no-error)
    - [Example 2: Transient Error with Retry](#example-2-transient-error-with-retry)
    - [Example 3: Permanent Failure (Retries Exhausted)](#example-3-permanent-failure-retries-exhausted)
    - [Example 4: Custom Retry Logic (Fail Fast)](#example-4-custom-retry-logic-fail-fast)
    - [Example 5: Custom Failure Handling](#example-5-custom-failure-handling)
  - [Common Patterns](#common-patterns)
    - [Pattern 1: Retry Only on Specific Errors](#pattern-1-retry-only-on-specific-errors)
    - [Pattern 2: Exponential Backoff (Framework Handles)](#pattern-2-exponential-backoff-framework-handles)
    - [Pattern 3: Compensation Logic on Failure](#pattern-3-compensation-logic-on-failure)
    - [Pattern 4: No Retry for Business Logic Errors](#pattern-4-no-retry-for-business-logic-errors)
  - [Exception Types](#exception-types)
    - [Framework-Raised Exceptions](#framework-raised-exceptions)
    - [User-Raised Exceptions](#user-raised-exceptions)
    - [Dead Letter Queue](#dead-letter-queue)
  - [Best Practices](#best-practices)
    - [✅ DO](#-do)
    - [❌ DON'T](#-dont)
  - [Configuration](#configuration)
    - [Task-Level Configuration](#task-level-configuration)
    - [Runtime Configuration](#runtime-configuration)
  - [Observability](#observability)
    - [Logging](#logging)
    - [Events (if enabled)](#events-if-enabled)
  - [Testing Error Handling](#testing-error-handling)
    - [Unit Test Example](#unit-test-example)
  - [Summary](#summary)

## Overview

The asynctasq error handling system is designed with clear separation of concerns between framework-level error management and user-level error hooks. This document outlines the error handling flow, responsibilities, and extension points.

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                          Worker Loop                            │
│  (Continuously polls queues for tasks)                          │
└─────────────────┬───────────────────────────────────────────────┘
                  │
                  ▼
┌─────────────────────────────────────────────────────────────────┐
│                      TaskExecutor.execute()                     │
│  Framework Entry Point - Wraps execution with timeout           │
│                                                                 │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │  try:                                                    │   │
│  │      result = await asyncio.wait_for(                    │   │
│  │          task.run(),  # Calls task.execute()            │   │
│  │          timeout=task.config.get("timeout")              │   │
│  │      )                                                   │   │
│  │      return SUCCESS                                      │   │
│  │  except asyncio.TimeoutError:                            │   │
│  │      # Framework handles timeout → retry                 │   │
│  │  except Exception as e:                                  │   │
│  │      # Framework catches all exceptions                  │   │
│  │      raise (propagated to Worker)                        │   │
│  └──────────────────────────────────────────────────────────┘   │
└─────────────────┬───────────────────────────────────────────────┘
                  │ (Exception propagates to Worker)
                  ▼
┌─────────────────────────────────────────────────────────────────┐
│                 Worker._handle_task_failure()                   │
│  Framework Error Recovery Logic                                 │
│                                                                 │
│  1. Check TaskExecutor.should_retry(task, exception)            │
│     → Combines current_attempt < max_attempts AND               │
│       task.should_retry(exception) → User Hook                  │
│  2. If retry: Emit task_reenqueued event                        │
│              Calculate retry delay (fixed/exponential)          │
│              Re-queue task with delay                           │
│  3. If exhausted: Emit task_failed event                        │
│                   Call TaskExecutor.handle_failed()             │
│                   → task.failed(exception) → User Hook          │
│                   Move to dead letter queue (if supported)      │
└─────────────────────────────────────────────────────────────────┘
                  │
                  ▼
┌─────────────────────────────────────────────────────────────────┐
│                     User Extension Points                       │
│                                                                 │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │  BaseTask.should_retry(exception: Exception) -> bool     │   │
│  │  ─────────────────────────────────────────────────────   │   │
│  │  Purpose: Decide if task should retry after failure      │   │
│  │  Default: Always return True (retry until max_attempts)  │   │
│  │  Override: Custom retry logic (e.g., fail fast on        │   │
│  │           validation errors, retry on network errors)    │   │
│  └──────────────────────────────────────────────────────────┘   │
│                                                                 │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │  async BaseTask.failed(exception: Exception) -> None     │   │
│  │  ─────────────────────────────────────────────────────   │   │
│  │  Purpose: Handle task failure after retries exhausted    │   │
│  │  Default: No-op (pass)                                   │   │
│  │  Override: Custom failure handling (alerts, logging,     │   │
│  │           cleanup, compensation logic)                   │   │
│  │  Note: Exceptions raised here are logged but don't       │   │
│  │        affect task processing (fail-safe)                │   │
│  └──────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
```

## Layer Responsibilities

### 1. Framework Layer (TaskExecutor)

**File:** `src/asynctasq/tasks/services/executor.py`

**Responsibilities:**
- Wrap task execution with timeout (`asyncio.wait_for`)
- Catch ALL exceptions from task execution
- Implement retry logic (attempts counting, re-queueing)
- Call user hooks (`should_retry()`, `failed()`)
- Handle timeout errors specifically
- Ensure worker stability (no unhandled exceptions escape)

**Key Methods:**
- `execute(task)` - Main entry point with timeout wrapper
- `handle_failed(task, exception)` - Retry/failure decision logic

**Error Handling Rules:**
1. All task exceptions are caught at this level
2. Timeout errors are treated as retriable failures
3. User hooks (`failed()`) are called in try-except to prevent worker crashes
4. Framework NEVER lets exceptions escape to worker loop

### 2. User Layer (BaseTask)

**File:** `src/asynctasq/tasks/core/base_task.py`

**Responsibilities:**
- Implement business logic in `execute()` method (called by framework via `run()`)
- Optionally override `should_retry()` for custom retry decisions
- Optionally override `failed()` for custom failure handling
- Let exceptions propagate to framework (don't catch unless recovering in-place)

**Key Methods:**
- `should_retry(exception)` - User hook for retry decision
- `failed(exception)` - User hook for exhausted retries

**Error Handling Rules:**
1. Users implement business logic in `execute()`; framework handles errors via `run()`
2. Override `should_retry()` ONLY if custom retry logic needed
3. Override `failed()` ONLY if custom failure handling needed (called via `TaskExecutor.handle_failed()`)
4. Don't catch exceptions in `execute()` unless recovering in-place

## Error Flow Examples

### Example 1: Successful Execution (No Error)

```
Worker → TaskExecutor.execute()
       → task.run()
       → task.execute() [User Code]
       ← Returns result
       ← SUCCESS
       → Mark task complete
```

### Example 2: Transient Error with Retry

```
Worker → TaskExecutor.execute()
       → task.run()
       → task.execute() [User Code]
       ← Raises ConnectionError
       → Worker._handle_task_failure()
       → Check TaskExecutor.should_retry(ConnectionError) → True (default)
       → Check current_attempt < max_attempts → True
       → Re-queue task with retry delay
       ← RETRY (task_reenqueued event emitted)
```

### Example 3: Permanent Failure (Retries Exhausted)

```
Worker → TaskExecutor.execute()
       → task.run()
       → task.execute() [User Code]
       ← Raises ValueError
       → Worker._handle_task_failure()
       → Check TaskExecutor.should_retry(ValueError) → True (default)
       → Check current_attempt < max_attempts → False (exhausted)
       → Call TaskExecutor.handle_failed() → task.failed(ValueError) [User Hook]
       → Emit task_failed event
       → Move to dead letter queue (PostgreSQL/MySQL) or mark failed (Redis)
       ← FAILED
```

### Example 4: Custom Retry Logic (Fail Fast)

```python
class ValidateDataTask(AsyncTask[None]):
    async def execute(self) -> None:
        if not self.data:
            raise ValueError("Invalid data")
        # Process data...

    def should_retry(self, exception: Exception) -> bool:
        # Don't retry validation errors
        if isinstance(exception, ValueError):
            return False
        return True  # Retry other errors

# Execution flow:
Worker → TaskExecutor.execute()
       → task.run()
       → task.execute() [User Code]
       ← Raises ValueError("Invalid data")
       → Worker._handle_task_failure()
       → Check TaskExecutor.should_retry(ValueError) → False (custom logic)
       → Call TaskExecutor.handle_failed() → task.failed(ValueError) immediately
       → Emit task_failed event
       ← FAILED (no retry)
```

### Example 5: Custom Failure Handling

```python
class SendEmailTask(AsyncTask[None]):
    email: str

    async def execute(self) -> None:
        # Send email logic...
        raise ConnectionError("SMTP server unavailable")

    async def failed(self, exception: Exception) -> None:
        # Custom failure handling
        await alert_team(f"Email to {self.email} failed: {exception}")
        await log_to_monitoring(exception)

# Execution flow:
Worker → TaskExecutor.execute()
       → task.run()
       → task.execute() [User Code]
       ← Raises ConnectionError
       → Worker._handle_task_failure()
       → Retry logic... (retries with exponential backoff)
       → After max_attempts exhausted:
         → Call TaskExecutor.handle_failed() → task.failed(ConnectionError) [User Hook]
           → alert_team() called
           → log_to_monitoring() called
         → Emit task_failed event
       ← FAILED
```

## Common Patterns

### Pattern 1: Retry Only on Specific Errors

```python
class ResilientTask(AsyncTask[int]):
    def should_retry(self, exception: Exception) -> bool:
        # Retry only on transient network/timeout errors
        return isinstance(exception, (ConnectionError, TimeoutError))
```

### Pattern 2: Exponential Backoff (Framework Handles)

```python
# Framework automatically calculates retry delay using exponential backoff
# Default retry_strategy is 'exponential', base delay is 60 seconds
# Attempt 1 fails -> retry after 60s
# Attempt 2 fails -> retry after 120s (60 * 2^1)
# Attempt 3 fails -> retry after 240s (60 * 2^2)
task = MyTask().retry_after(60).dispatch()  # Base retry delay of 60s

# For fixed delay (same delay every time):
from asynctasq import init, TaskDefaultsConfig
init(task_defaults=TaskDefaultsConfig(retry_strategy='fixed', retry_delay=60))
```

### Pattern 3: Compensation Logic on Failure

```python
class TransactionTask(AsyncTask[None]):
    transaction_id: str

    async def failed(self, exception: Exception) -> None:
        # Rollback transaction on permanent failure
        await rollback_transaction(self.transaction_id)
        await notify_user(self.transaction_id, "failed")
```

### Pattern 4: No Retry for Business Logic Errors

```python
class ProcessOrderTask(AsyncTask[None]):
    def should_retry(self, exception: Exception) -> bool:
        # Don't retry business logic errors
        if isinstance(exception, (ValueError, ValidationError)):
            return False
        return True  # Retry infrastructure errors
```

## Exception Types

### Framework-Raised Exceptions

- `asyncio.TimeoutError` - Task exceeded timeout (retriable by default)
- `SerializationError` - Task serialization/deserialization failed (re-enqueued with delay)
- `DriverError` - Queue driver error (connection, etc.)

### User-Raised Exceptions

- Any exception from `task.execute()` is caught by framework via `task.run()`
- Framework doesn't interpret exception types (delegates to `should_retry()`)
- All exceptions are logged with full context (task_id, attempt, exception type/message)

### Dead Letter Queue

When tasks permanently fail (retries exhausted), behavior depends on driver:

- **PostgreSQL/MySQL**: Failed tasks are moved to a `dead_letter_queue` table for manual inspection
- **Redis**: Failed tasks are marked in a separate failed tasks list (if `mark_failed()` is implemented)
- **RabbitMQ/SQS**: Tasks are acknowledged and removed (use `failed()` hook for custom DLQ)

## Best Practices

### ✅ DO

1. **Let exceptions propagate** - Don't catch in `execute()` unless recovering
2. **Override `should_retry()` for custom logic** - Framework calls it
3. **Override `failed()` for cleanup** - Compensation, alerts, logging
4. **Use specific exception types** - Easier to distinguish in `should_retry()`
5. **Keep `failed()` idempotent** - It might be called multiple times (e.g., on worker restart)

### ❌ DON'T

1. **Don't catch all exceptions in `execute()`** - Defeats retry mechanism
2. **Don't raise exceptions in `failed()`** - They're logged but ignored
3. **Don't depend on `failed()` for critical logic** - It's best-effort
4. **Don't use `should_retry()` for side effects** - It's a decision function
5. **Don't retry indefinitely** - Set reasonable `max_attempts`

## Configuration

### Task-Level Configuration

```python
from asynctasq import AsyncTask, TaskConfig

class MyTask(AsyncTask[None]):
    config: TaskConfig = {
        "queue": "high-priority",
        "max_attempts": 5,          # Retry up to 5 times
        "retry_delay": 120,        # 2 minutes between retries
        "timeout": 300,            # 5-minute timeout per attempt
    }
```

### Runtime Configuration

```python
task = MyTask(data="x")
task.on_queue("urgent").retry_after(60).dispatch()
```

## Observability

### Logging

All error events are logged with structured context:

```python
logger.error(
    "Task execution failed",
    extra={
        "task_id": task._task_id,
        "task_class": task.__class__.__name__,
        "attempt": task._current_attempt,
        "max_attempts": task.config.max_attempts,
        "exception_type": type(exception).__name__,
        "exception_message": str(exception),
    }
)
```

### Events (if enabled)

- `task_failed` - Emitted when task permanently fails after retries exhausted
- `task_reenqueued` - Emitted when task is re-queued for retry (includes attempt number and error)

## Testing Error Handling

### Unit Test Example

```python
import pytest
from asynctasq import AsyncTask

class FailingTask(AsyncTask[None]):
    fail_count: int = 0

    async def execute(self) -> None:
        self.fail_count += 1
        if self.fail_count < 3:
            raise ConnectionError("Transient error")
        # Success on 3rd attempt

@pytest.mark.asyncio
async def test_task_retries():
    task = FailingTask()
    task.config.max_attempts = 3

    # Simulate 3 execution attempts
    for attempt in range(1, 4):
        task._current_attempt = attempt
        if attempt < 3:
            with pytest.raises(ConnectionError):
                await task.execute()
        else:
            await task.execute()  # Succeeds on 3rd attempt
```

## Summary

| Component        | Responsibility                                 | Entry Points                                     |
| ---------------- | ---------------------------------------------- | ------------------------------------------------ |
| **TaskExecutor** | Framework error handling, retry logic, timeout | `execute()`, `should_retry()`, `handle_failed()` |
| **BaseTask**     | Business logic, custom error decisions         | `execute()`, `should_retry()`, `failed()`        |
| **Worker**       | Task polling, deserialization, lifecycle       | `_process_task()`, `_handle_task_failure()`      |

**Key Principle:** Framework manages error recovery; users implement business logic and custom error decisions via hooks.
---

## Common Error Scenarios

This section covers real-world error scenarios and recommended handling patterns.

### Scenario 1: External API Failures

**Problem:** Task depends on external API that may be temporarily unavailable.

**Pattern:** Retry with exponential backoff, fail fast on 4xx errors.

```python
from asynctasq import AsyncTask
import httpx

class FetchUserDataTask(AsyncTask[None]):
    config = {
        "queue": "api_calls",
        "max_attempts": 5,
        "retry_strategy": "exponential",
        "retry_delay": 60,  # Start with 1 minute
        "timeout": 30,
    }

    def should_retry(self, exception: Exception) -> bool:
        """Retry on 5xx errors and network issues, fail fast on 4xx."""
        if isinstance(exception, httpx.HTTPStatusError):
            # 4xx = client error (bad request, not found, etc.) - don't retry
            if 400 <= exception.response.status_code < 500:
                return False
            # 5xx = server error - retry
            return True

        # Network errors, timeouts - retry
        if isinstance(exception, (httpx.ConnectError, httpx.TimeoutException)):
            return True

        return False  # Other errors - don't retry

    async def execute(self, user_id: int) -> None:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"https://api.example.com/users/{user_id}",
                timeout=25.0  # Slightly less than task timeout
            )
            response.raise_for_status()
            data = response.json()
            # Process user data...

    async def failed(self, exception: Exception) -> None:
        """Alert team if API is consistently failing."""
        # Log to monitoring system
        logger.error(
            "User data fetch permanently failed",
            extra={
                "user_id": self.kwargs.get("user_id"),
                "error": str(exception),
                "attempts": self._current_attempt,
            }
        )
        # Send alert to Slack/PagerDuty
        # await alert_team(f"User data API failing: {exception}")
```

### Scenario 2: Database Connection Issues

**Problem:** Database connections may be temporarily unavailable or experience deadlocks.

**Pattern:** Retry on connection/deadlock errors, fail fast on constraint violations.

```python
from asynctasq import AsyncTask
from sqlalchemy.exc import (
    OperationalError,
    IntegrityError,
    DBAPIError,
    DisconnectionError
)
import asyncio

class UpdateUserTask(AsyncTask[None]):
    config = {
        "queue": "database",
        "max_attempts": 5,
        "retry_strategy": "exponential",
        "retry_delay": 30,
        "timeout": 60,
    }

    def should_retry(self, exception: Exception) -> bool:
        """Retry on transient DB errors, fail fast on integrity violations."""
        # Connection issues - retry
        if isinstance(exception, (OperationalError, DisconnectionError)):
            return True

        # Deadlock or lock timeout - retry
        if isinstance(exception, DBAPIError):
            if "deadlock" in str(exception).lower():
                return True
            if "lock timeout" in str(exception).lower():
                return True

        # Integrity errors (unique constraint, foreign key) - don't retry
        if isinstance(exception, IntegrityError):
            return False

        return False

    async def execute(self, user_id: int, email: str) -> None:
        # Add jitter to reduce thundering herd on retries
        await asyncio.sleep(0.1 * self._current_attempt)

        # Your SQLAlchemy session logic here
        # async with async_session() as session:
        #     user = await session.get(User, user_id)
        #     user.email = email
        #     await session.commit()
        pass

    async def failed(self, exception: Exception) -> None:
        """Handle permanent database failures."""
        if isinstance(exception, IntegrityError):
            # Log data quality issue
            logger.warning(
                "Data integrity violation",
                extra={"user_id": self.kwargs.get("user_id"), "email": self.kwargs.get("email")}
            )
        else:
            # Alert on infrastructure issue
            logger.error("Database operation permanently failed", exc_info=exception)
```

### Scenario 3: File Processing with Validation

**Problem:** Processing uploaded files that may be corrupted or invalid.

**Pattern:** Fail fast on validation errors, retry on I/O errors.

```python
from asynctasq import AsyncTask
from pathlib import Path
import aiofiles

class ProcessImageTask(AsyncTask[None]):
    config = {
        "queue": "images",
        "max_attempts": 3,
        "retry_delay": 60,
        "timeout": 300,
    }

    def should_retry(self, exception: Exception) -> bool:
        """Retry on I/O errors, fail fast on validation errors."""
        # Validation errors - user's fault, don't retry
        if isinstance(exception, (ValueError, TypeError)):
            return False

        # I/O errors, transient issues - retry
        if isinstance(exception, (IOError, OSError)):
            return True

        return True  # Default: retry

    async def execute(self, file_path: str, user_id: int) -> None:
        path = Path(file_path)

        # Validate file exists
        if not path.exists():
            raise ValueError(f"File not found: {file_path}")

        # Validate file size
        file_size = path.stat().st_size
        if file_size > 10 * 1024 * 1024:  # 10 MB
            raise ValueError(f"File too large: {file_size} bytes")

        # Validate file type
        if not path.suffix.lower() in {'.jpg', '.jpeg', '.png'}:
            raise ValueError(f"Invalid file type: {path.suffix}")

        # Process image
        async with aiofiles.open(path, 'rb') as f:
            content = await f.read()
            # Process image content...

    async def failed(self, exception: Exception) -> None:
        """Notify user of processing failure."""
        user_id = self.kwargs.get("user_id")
        file_path = self.kwargs.get("file_path")

        if isinstance(exception, ValueError):
            # Validation error - user action needed
            # await notify_user(user_id, f"Invalid file: {exception}")
            logger.info(f"User {user_id} uploaded invalid file: {file_path}")
        else:
            # System error - alert team
            logger.error(f"Image processing failed for user {user_id}", exc_info=exception)
```

### Scenario 4: Rate-Limited Third-Party Service

**Problem:** Third-party service has rate limits, need to back off appropriately.

**Pattern:** Custom retry delay based on rate limit headers, with exponential backoff.

```python
from asynctasq import AsyncTask
import httpx
import asyncio

class SendEmailTask(AsyncTask[None]):
    config = {
        "queue": "emails",
        "max_attempts": 10,  # More attempts for rate-limited services
        "retry_strategy": "exponential",
        "retry_delay": 60,
        "timeout": 30,
    }

    def should_retry(self, exception: Exception) -> bool:
        """Always retry rate limit errors."""
        if isinstance(exception, httpx.HTTPStatusError):
            # 429 = Too Many Requests - always retry
            if exception.response.status_code == 429:
                return True
            # 5xx errors - retry
            if exception.response.status_code >= 500:
                return True
        return False

    async def execute(self, to_email: str, subject: str, body: str) -> None:
        # Add jitter to spread out requests
        await asyncio.sleep(0.5 * self._current_attempt)

        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(
                    "https://api.emailservice.com/send",
                    json={"to": to_email, "subject": subject, "body": body},
                    headers={"Authorization": f"Bearer {API_KEY}"},
                    timeout=25.0
                )
                response.raise_for_status()
            except httpx.HTTPStatusError as e:
                if e.response.status_code == 429:
                    # Check for Retry-After header
                    retry_after = e.response.headers.get("Retry-After")
                    if retry_after:
                        logger.warning(f"Rate limited, should retry after {retry_after}s")
                raise

    async def failed(self, exception: Exception) -> None:
        """Move to dead letter queue or alternative service."""
        logger.error(
            f"Email delivery permanently failed",
            extra={
                "to_email": self.kwargs.get("to_email"),
                "subject": self.kwargs.get("subject"),
                "attempts": self._current_attempt,
            }
        )
        # Try alternative email service or queue for manual review
```

### Scenario 5: Idempotent Operations

**Problem:** Task may be executed multiple times due to failures/retries.

**Pattern:** Check if work already done before executing.

```python
from asynctasq import AsyncTask

class ChargeCustomerTask(AsyncTask[None]):
    config = {
        "queue": "payments",
        "max_attempts": 3,
        "retry_delay": 120,
        "timeout": 60,
    }

    async def execute(self, order_id: str, amount: float, idempotency_key: str) -> None:
        """Charge customer with idempotency guarantee."""
        # Check if payment already processed
        # existing_charge = await get_charge_by_idempotency_key(idempotency_key)
        # if existing_charge:
        #     logger.info(f"Payment already processed: {idempotency_key}")
        #     return

        # Process payment with idempotency key
        # await stripe.Charge.create(
        #     amount=int(amount * 100),
        #     currency="usd",
        #     source=token,
        #     idempotency_key=idempotency_key,  # Prevents duplicate charges
        # )

        # Update order status
        # await update_order_status(order_id, "paid")
        pass

    def should_retry(self, exception: Exception) -> bool:
        """Don't retry payment errors that indicate permanent failure."""
        # Example: Check for specific Stripe errors
        if "card_declined" in str(exception).lower():
            return False
        if "insufficient_funds" in str(exception).lower():
            return False
        return True

    async def failed(self, exception: Exception) -> None:
        """Handle payment failure."""
        order_id = self.kwargs.get("order_id")
        # Update order status to failed
        # await update_order_status(order_id, "payment_failed")
        # Notify customer
        # await notify_customer_payment_failed(order_id)
```

### Scenario 6: Batch Processing with Partial Failures

**Problem:** Processing batch of items where some may fail.

**Pattern:** Process items individually, track failures, retry only failed items.

```python
from asynctasq import AsyncTask
import asyncio

class ProcessBatchTask(AsyncTask[None]):
    config = {
        "queue": "batch",
        "max_attempts": 3,
        "retry_delay": 300,
        "timeout": 600,
    }

    async def execute(self, item_ids: list[int]) -> None:
        """Process batch of items, handling partial failures."""
        failed_items = []

        for item_id in item_ids:
            try:
                await self._process_single_item(item_id)
            except Exception as e:
                logger.warning(f"Item {item_id} failed: {e}")
                failed_items.append(item_id)

        if failed_items:
            # Raise exception to trigger retry with only failed items
            raise ValueError(f"{len(failed_items)} items failed: {failed_items}")

    async def _process_single_item(self, item_id: int) -> None:
        """Process a single item."""
        # Your processing logic here
        await asyncio.sleep(0.1)  # Simulate work

    def should_retry(self, exception: Exception) -> bool:
        """Always retry if any items failed."""
        return True

    async def failed(self, exception: Exception) -> None:
        """Log permanently failed items."""
        logger.error(
            "Batch processing permanently failed",
            extra={"item_ids": self.kwargs.get("item_ids"), "error": str(exception)}
        )
```

### Scenario 7: Cascading Task Failures

**Problem:** Task failure should trigger cleanup or compensation tasks.

**Pattern:** Use `failed()` hook to dispatch cleanup tasks.

```python
from asynctasq import AsyncTask

class CreateUserAccountTask(AsyncTask[None]):
    config = {
        "queue": "accounts",
        "max_attempts": 3,
        "retry_delay": 60,
    }

    async def execute(self, email: str, username: str) -> None:
        """Create user account with multiple steps."""
        # Step 1: Create database record
        # user_id = await create_user_db_record(email, username)
        user_id = 123

        # Step 2: Create auth account
        # await create_auth_account(user_id, email)

        # Step 3: Setup user storage
        # await create_user_storage(user_id)

        # If any step fails, exception is raised and task retries
        pass

    async def failed(self, exception: Exception) -> None:
        """Cleanup partial account creation."""
        email = self.kwargs.get("email")

        logger.error(f"Account creation failed for {email}: {exception}")

        # Dispatch cleanup task
        # await CleanupPartialAccountTask(email=email).dispatch()

        # Or perform cleanup directly
        # await cleanup_partial_account(email)
```

### Error Handling Best Practices Summary

| Scenario                      | Retry Strategy                        | Error Handling                                    |
| ----------------------------- | ------------------------------------- | ------------------------------------------------- |
| **External API**              | Retry 5xx, fail fast 4xx              | Exponential backoff, timeout < task timeout       |
| **Database**                  | Retry connection/deadlock errors      | Add jitter, fail fast on integrity violations     |
| **File Processing**           | Retry I/O errors                      | Validate early, fail fast on validation errors    |
| **Rate Limits**               | Many retries with backoff             | Respect Retry-After headers, add jitter           |
| **Idempotent Operations**     | Safe to retry                         | Use idempotency keys, check if already done       |
| **Batch Processing**          | Retry with failed items only          | Track partial failures, process individually      |
| **Cascading Operations**      | Cleanup on permanent failure          | Use `failed()` hook to dispatch cleanup tasks     |

**Key Principles:**

1. **Fail Fast on User Errors** - Don't waste retries on 4xx errors or validation failures
2. **Retry Transient Failures** - Network issues, timeouts, 5xx errors, deadlocks
3. **Add Jitter** - Prevent thundering herd when many tasks retry simultaneously
4. **Use Idempotency** - Ensure operations are safe to execute multiple times
5. **Timeout Management** - Set task timeout > operation timeout to allow graceful error handling
6. **Monitor and Alert** - Use `failed()` hook for production monitoring
7. **Compensate on Failure** - Cleanup partial work in `failed()` hook
