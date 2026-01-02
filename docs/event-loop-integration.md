# Event Loop Integration

## Table of Contents

- [Event Loop Integration](#event-loop-integration)
  - [Table of Contents](#table-of-contents)
  - [Overview](#overview)
  - [How It Works](#how-it-works)
  - [Usage Patterns](#usage-patterns)
    - [Pattern 1: Standard Scripts with asyncio.run()](#pattern-1-standard-scripts-with-asynciorun)
    - [Pattern 2: Using AsyncTasQ's Runner (with uvloop support)](#pattern-2-using-asynctasqs-runner-with-uvloop-support)
    - [Pattern 3: FastAPI Integration (Recommended)](#pattern-3-fastapi-integration-recommended)
    - [Pattern 4: uvloop Direct Usage](#pattern-4-uvloop-direct-usage)
    - [Pattern 5: Jupyter Notebooks](#pattern-5-jupyter-notebooks)
    - [Pattern 6: Custom Event Loop Policy](#pattern-6-custom-event-loop-policy)
  - [Cleanup Behavior](#cleanup-behavior)
    - [Automatic Cleanup](#automatic-cleanup)
    - [Manual Cleanup](#manual-cleanup)
    - [What Gets Cleaned Up](#what-gets-cleaned-up)
  - [Event Loop Detection](#event-loop-detection)
  - [Best Practices](#best-practices)
    - [✅ Do's](#-dos)
    - [❌ Don'ts](#-donts)
  - [Troubleshooting](#troubleshooting)
    - [RuntimeError: cannot be called from a running event loop](#runtimeerror-cannot-be-called-from-a-running-event-loop)
    - [Cleanup not running](#cleanup-not-running)
    - [Connection warnings on shutdown](#connection-warnings-on-shutdown)
    - [FastAPI deprecation warnings](#fastapi-deprecation-warnings)
  - [Technical Details](#technical-details)
    - [Cleanup Hook Implementation](#cleanup-hook-implementation)
    - [Compatibility](#compatibility)
  - [Related Documentation](#related-documentation)
  - [Sources](#sources)

AsyncTasQ is designed to work seamlessly with any async event loop implementation. This guide explains how AsyncTasQ integrates with different event loop contexts and provides examples for various use cases.

## Overview

AsyncTasQ uses an intelligent cleanup hook system that automatically detects your event loop context and registers appropriate cleanup handlers. This means you can use AsyncTasQ with:

- **Standard asyncio** - `asyncio.run()`
- **uvloop** - High-performance event loop implementation
- **FastAPI** - Web frameworks with managed event loops
- **Jupyter Notebooks** - Interactive async environments
- **Custom event loops** - Any asyncio-compatible implementation

## How It Works

When you call `init()`, the library:

1. **Detects the event loop context** - Checks if an event loop is currently running
2. **Registers cleanup hooks** - Attaches cleanup to the appropriate lifecycle:
   - For **running loops**: Hooks into `loop.close()`
   - For **non-running contexts**: Registers with `atexit`
3. **Handles cleanup automatically** - When the event loop closes, AsyncTasQ properly disconnects from drivers and cleans up resources

This design is inspired by [asyncio-atexit](https://github.com/minrk/asyncio-atexit) but tailored specifically for AsyncTasQ's needs.

## Usage Patterns

### Pattern 1: Standard Scripts with asyncio.run()

The most straightforward approach for simple scripts:

```python
import asyncio
from asynctasq import init, RedisConfig, task

# Initialize AsyncTasQ
init({
    'driver': 'redis',
    'redis': RedisConfig(url='redis://localhost:6379')
})

@task()
async def process_data(data: str):
    print(f"Processing: {data}")
    return f"Processed {data}"

async def main():
    # Dispatch tasks
    for i in range(10):
        await process_data(f"item-{i}").dispatch()

if __name__ == "__main__":
    # Use standard asyncio
    asyncio.run(main())
    # Cleanup happens automatically when the event loop closes
```

### Pattern 2: Using AsyncTasQ's Runner (with uvloop support)

For optimal performance, use AsyncTasQ's built-in runner that automatically uses uvloop when available:

```python
from asynctasq import init, run, task

# Initialize AsyncTasQ
init({'driver': 'redis'})

@task()
async def send_email(to: str, subject: str):
    # Send email logic
    pass

async def main():
    await send_email("user@example.com", "Hello!").dispatch()

if __name__ == "__main__":
    # AsyncTasQ's runner - uses uvloop if available, falls back to asyncio
    run(main())
```

**Benefits of `run()`:**
- Automatically uses uvloop when available for ~2x performance boost
- Gracefully falls back to asyncio if uvloop is not available
- Handles proper cleanup of AsyncTasQ resources
- Mimics `asyncio.run()` semantics

**Note:** uvloop (>=0.22.1) is included as a core dependency of AsyncTasQ, so it's available by default. The `run()` function is exported directly from `asynctasq` (not `asynctasq.utils.loop.run`), though both import paths work.

### Pattern 3: FastAPI Integration (Recommended)

AsyncTasQ provides a dedicated `AsyncTasQIntegration` class for FastAPI with automatic lifecycle management:

```python
from fastapi import FastAPI, Depends
from asynctasq import AsyncTasQIntegration, RedisConfig, task
from asynctasq.core.dispatcher import Dispatcher
from asynctasq.config import Config

# Configure AsyncTasQ
config = Config(
    driver='redis',
    redis=RedisConfig(url='redis://localhost:6379')
)

# Create integration instance with config
asynctasq = AsyncTasQIntegration(config=config)

# Use lifespan for automatic driver management
app = FastAPI(lifespan=asynctasq.lifespan)

@task()
async def process_order(order_id: int):
    # Process order logic
    return f"Order {order_id} processed"

# Use dependency injection for dispatcher access
@app.post("/orders/{order_id}/process")
async def trigger_processing(
    order_id: int,
    dispatcher: Dispatcher = Depends(asynctasq.get_dispatcher)
):
    """Dispatch using injected dispatcher."""
    task = process_order(order_id)
    task_id = await dispatcher.dispatch(task)
    return {"task_id": task_id, "status": "dispatched"}

# Cleanup happens automatically when FastAPI shuts down
```

**Benefits:**
- Uses modern FastAPI `lifespan` context manager (FastAPI 0.109.0+)
- Automatic driver connection on startup
- Graceful driver disconnection on shutdown
- Dependency injection support for `Dispatcher` and `BaseDriver`
- Works with all queue drivers

**Alternative: Manual init() Pattern**

For simple use cases without dependency injection:

```python
from fastapi import FastAPI
from asynctasq import init, RedisConfig, task

# Initialize AsyncTasQ before creating the app
init({
    'driver': 'redis',
    'redis': RedisConfig(url='redis://localhost:6379')
})

app = FastAPI()

@task()
async def process_order(order_id: int):
    return f"Order {order_id} processed"

@app.post("/orders/{order_id}/process")
async def trigger_processing(order_id: int):
    task_id = await process_order(order_id).dispatch()
    return {"task_id": task_id, "status": "dispatched"}

# Cleanup hooks are automatically registered when tasks are dispatched
# If init() is called before a loop starts, cleanup registration is deferred
# until the first dispatch, ensuring proper attachment to the running loop
```

**Note:** The `@app.on_event("startup")` decorator is deprecated in FastAPI 0.109.0+. Use the `lifespan` pattern shown above instead.

### Pattern 4: uvloop Direct Usage

If you want to use uvloop directly:

```python
import uvloop
from asynctasq import init, task

# Initialize AsyncTasQ
init({'driver': 'redis'})

@task()
async def background_job(data: dict):
    # Job logic
    pass

async def main():
    await background_job({"key": "value"}).dispatch()

if __name__ == "__main__":
    # Use uvloop directly
    uvloop.run(main())
```

### Pattern 5: Jupyter Notebooks

AsyncTasQ works in Jupyter notebooks where an event loop is already running:

```python
# In a Jupyter notebook cell
from asynctasq import init, task

# Initialize (this registers cleanup hooks to the notebook's event loop)
init({'driver': 'redis'})

@task()
async def analyze_data(dataset: str):
    # Analysis logic
    pass

# Dispatch tasks - use await directly (no need for asyncio.run())
await analyze_data("my_dataset").dispatch()
```

### Pattern 6: Custom Event Loop Policy

AsyncTasQ works with custom event loop policies:

```python
import asyncio
from asynctasq import init

# Set a custom event loop policy
class CustomEventLoopPolicy(asyncio.DefaultEventLoopPolicy):
    def new_event_loop(self):
        # Your custom loop creation
        return super().new_event_loop()

asyncio.set_event_loop_policy(CustomEventLoopPolicy())

# Initialize AsyncTasQ
init({'driver': 'redis'})

async def main():
    # Your async code
    pass

# AsyncTasQ works with your custom loop
asyncio.run(main())
```

## Cleanup Behavior

### Automatic Cleanup

AsyncTasQ automatically handles cleanup in all contexts:

1. **Running event loops** (FastAPI, Jupyter, etc.):
   - Cleanup hook is attached to `loop.close()`
   - Runs when the framework shuts down the event loop

2. **Script contexts** (`asyncio.run()`, `uvloop.run()`, etc.):
   - Cleanup runs as part of loop shutdown via the patched `loop.close()` method
   - No separate atexit handler needed - cleanup is guaranteed when the loop closes

### Manual Cleanup

You can also manually trigger cleanup if needed:

```python
from asynctasq import cleanup

async def shutdown():
    """Manual cleanup before event loop closes."""
    await cleanup()
    # Your other shutdown logic

# In your application shutdown handler
await shutdown()
```

### What Gets Cleaned Up

The cleanup process handles:
- **Driver connections** - Properly closes Redis/PostgreSQL/MySQL/RabbitMQ/SQS connections
- **Connection pools** - Drains and closes connection pools
- **SQLAlchemy engines** - Disposes of user-supplied async engines
- **Process pools** - Shuts down process pools for `AsyncProcessTask` and `SyncProcessTask`
- **Event registries** - Cleans up event emitters

## Event Loop Detection

AsyncTasQ uses the following strategy to detect the event loop:

```python
# Simplified version of what AsyncTasQ does internally
try:
    # Try to get the running event loop
    loop = asyncio.get_running_loop()
    # Running loop found - register cleanup hook
    register_cleanup_hook(loop)  # Patches loop.close()
except RuntimeError:
    # No running loop - cleanup will be registered when first async call happens
    # via ensure_cleanup_registered() in dispatchers
    pass
```

## Best Practices

### ✅ Do's

1. **Call `init()` early** - Before dispatching any tasks
2. **Use `await` in running loops** - Don't call `run()` from within FastAPI, Jupyter, etc.
3. **Let AsyncTasQ handle cleanup** - Trust the automatic cleanup hooks
4. **Choose the right pattern** - Use `asyncio.run()` for simplicity, `run()` for uvloop performance
5. **Use AsyncTasQIntegration for FastAPI** - Leverage the modern `lifespan` pattern for proper lifecycle management

### ❌ Don'ts

1. **Don't call `run()` from running loops** - Will raise `RuntimeError`
2. **Don't manually close connections** - Let AsyncTasQ's cleanup handle it
3. **Don't mix event loop patterns** - Stick to one approach per application
4. **Don't use deprecated FastAPI patterns** - Avoid `@app.on_event()`, use `lifespan` instead

## Troubleshooting

### RuntimeError: cannot be called from a running event loop

**Problem:** You're trying to use `run()` inside a running event loop.

**Solution:** Use `await` directly instead:

```python
# ❌ Wrong - in FastAPI, Jupyter, etc.
from asynctasq import run
run(my_coroutine())

# ✅ Correct
await my_coroutine()
```

### Cleanup not running

**Problem:** AsyncTasQ resources aren't being cleaned up.

**Solution:** Ensure you're calling `init()`:

```python
from asynctasq import init

# Must call init() to register cleanup hooks
init({'driver': 'redis'})
```

### Connection warnings on shutdown

**Problem:** Seeing warnings about unclosed connections.

**Solution:** Make sure `init()` is called and the event loop is properly closed:

```python
# For scripts
asyncio.run(main())  # Properly closes the loop

# For FastAPI - use AsyncTasQIntegration
asynctasq = AsyncTasQIntegration()
app = FastAPI(lifespan=asynctasq.lifespan)
```

### FastAPI deprecation warnings

**Problem:** Seeing warnings about `@app.on_event()` being deprecated.

**Solution:** Migrate to the modern `lifespan` pattern:

```python
# ❌ Old way (deprecated in FastAPI 0.109.0+)
@app.on_event("startup")
async def startup():
    init(...)

# ✅ New way
asynctasq = AsyncTasQIntegration()
app = FastAPI(lifespan=asynctasq.lifespan)
```

## Technical Details

### Cleanup Hook Implementation

AsyncTasQ's cleanup hook system:

1. **Patches `loop.close()`** - Wraps the event loop's close method
2. **Executes cleanup first** - Runs AsyncTasQ cleanup before original close
3. **Supports async callbacks** - Can execute async cleanup functions
4. **Handles exceptions** - One failing cleanup doesn't break others
5. **Uses weak references** - Doesn't prevent loop garbage collection

### Compatibility

AsyncTasQ's event loop integration works with:

- **Python 3.12+** - Uses modern asyncio APIs (minimum version requirement)
- **asyncio** - Standard library event loop
- **uvloop 0.22+** - High-performance event loop (via `asyncio.Runner` with loop factory)
- **Any asyncio-compatible loop** - Follows standard event loop protocol

**Note:** AsyncTasQ uses `asyncio.Runner` (introduced in Python 3.11) for proper cleanup sequencing and modern event loop management. Python 3.12+ is required as the minimum version per the package's requirements.

## Related Documentation

- [Configuration](configuration.md) - AsyncTasQ configuration options
- [Running Workers](running-workers.md) - Worker deployment patterns
- [Framework Integrations](framework-integrations.md) - FastAPI and other frameworks
- [Best Practices](best-practices.md) - Production deployment guidelines

## Sources

This implementation is inspired by:
- [asyncio-atexit](https://github.com/minrk/asyncio-atexit) - atexit for asyncio
- [Python asyncio documentation](https://docs.python.org/3/library/asyncio-eventloop.html) - Event loop reference
- [uvloop documentation](https://uvloop.readthedocs.io/) - High-performance event loop
