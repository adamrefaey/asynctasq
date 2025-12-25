# Monitoring

## Table of Contents

- [Overview](#overview)
- [Event System](#event-system)
  - [Event Types](#event-types)
    - [Task Events](#task-events)
    - [Worker Events](#worker-events)
  - [Event Data Structures](#event-data-structures)
  - [Event Emitters](#event-emitters)
    - [Logging Emitter (Default)](#logging-emitter-default)
    - [Redis Emitter](#redis-emitter)
  - [Event Registry](#event-registry)
- [Configuration](#configuration)
  - [Configuration Options](#configuration-options)
- [Consuming Events](#consuming-events)
  - [Using EventSubscriber](#using-eventsubscriber)
  - [WebSocket Integration](#websocket-integration)
- [Queue Statistics](#queue-statistics)
- [Integration with asynctasq-monitor](#integration-with-asynctasq-monitor)
- [Best Practices](#best-practices)
  - [Production Monitoring](#production-monitoring)
  - [Performance Considerations](#performance-considerations)
  - [Security](#security)
- [Troubleshooting](#troubleshooting)

AsyncTasQ provides comprehensive monitoring capabilities through real-time event streaming and queue statistics. This enables observability, alerting, and dashboards for production task queue operations.

## Overview

Monitoring in AsyncTasQ consists of two main components:

1. **Event Streaming**: Real-time events emitted during task and worker lifecycles
2. **Queue Statistics**: Historical and current metrics about queues, workers, and tasks

Events flow from workers to Redis Pub/Sub, where they can be consumed by monitoring tools like `asynctasq-monitor` for live dashboards.

## Event System

### Event Types

AsyncTasQ emits events for all major lifecycle changes:

#### Task Events

| Event             | Description                                  |
| ----------------- | -------------------------------------------- |
| `task_enqueued`   | Task added to queue, awaiting execution      |
| `task_started`    | Worker began executing the task              |
| `task_completed`  | Task finished successfully                   |
| `task_failed`     | Task failed after exhausting retries         |
| `task_reenqueued` | Task failed but will be retried              |
| `task_cancelled`  | Task was cancelled/revoked before completion |

#### Worker Events

| Event              | Description                                 |
| ------------------ | ------------------------------------------- |
| `worker_online`    | Worker started and ready to process tasks   |
| `worker_heartbeat` | Periodic status update (default: every 60s) |
| `worker_offline`   | Worker shutting down gracefully             |

### Event Data Structures

Events are immutable dataclasses with comprehensive metadata:

```python
from asynctasq.monitoring import TaskEvent, WorkerEvent, EventType

# Task event example
task_event = TaskEvent(
    event_type=EventType.TASK_COMPLETED,
    task_id="abc123",
    task_name="SendEmailTask",
    queue="default",
    worker_id="worker-1",
    attempt=1,
    duration_ms=150,
    result={"email_sent": True}
)

# Worker event example
worker_event = WorkerEvent(
    event_type=EventType.WORKER_HEARTBEAT,
    worker_id="worker-1",
    hostname="web-01",
    active=3,  # Currently executing tasks
    processed=150,  # Total tasks processed
    queues=("default", "high-priority"),
    uptime_seconds=3600
)
```

### Event Emitters

AsyncTasQ supports multiple event emitters that can be used simultaneously:

#### Logging Emitter (Default)

Always enabled, logs events at INFO level for development and debugging:

```python
from asynctasq.monitoring import LoggingEventEmitter

emitter = LoggingEventEmitter()
# Events are logged automatically when emitted
```

#### Redis Emitter

Publishes events to Redis Pub/Sub for consumption by monitoring tools:

```python
from asynctasq.monitoring import RedisEventEmitter

emitter = RedisEventEmitter(
    redis_url="redis://localhost:6379",
    channel="asynctasq:events"
)
```

### Event Registry

The `EventRegistry` manages all emitters and broadcasts events to them:

```python
from asynctasq.monitoring import EventRegistry

# Initialize with default emitters based on config
EventRegistry.init()

# Emit an event to all registered emitters
await EventRegistry.emit(task_event)

# Clean up when shutting down
await EventRegistry.close_all()
```

## Configuration

Enable Redis event emission in your AsyncTasQ configuration:

```python
import asynctasq
from asynctasq.config import EventsConfig

asynctasq.init({
    'driver': 'redis',
    'events': EventsConfig(
        enable_event_emitter_redis=True,  # Enable Redis event emission
        redis_url='redis://events.example.com:6379',  # Optional: separate Redis for events
        channel='asynctasq:prod:events'  # Pub/Sub channel name
    )
})
```

### Configuration Options

Configuration group: `events` (type: `EventsConfig`)

| Option                       | Type        | Description                                      | Default            |
| ---------------------------- | ----------- | ------------------------------------------------ | ------------------ |
| `enable_event_emitter_redis` | bool        | Enable/disable Redis event emission              | `False`            |
| `redis_url`                  | str \| None | Redis URL for events (falls back to `redis.url`) | `None`             |
| `channel`                    | str         | Redis Pub/Sub channel name                       | `asynctasq:events` |

**Note:** Events are always logged at INFO level for development and debugging.

## Consuming Events

### Using EventSubscriber

Consume events directly from Redis Pub/Sub:

```python
# Note: EventSubscriber is provided by the asynctasq-monitor package
from asynctasq_monitor import EventSubscriber

async def monitor_events():
    subscriber = EventSubscriber(redis_url="redis://localhost:6379")
    await subscriber.connect()

    try:
        async for event in subscriber.listen():
            if event.event_type == "task_failed":
                print(f"❌ Task {event.task_id} failed: {event.error}")
            elif event.event_type == "task_completed":
                print(f"✓ Task {event.task_id} completed in {event.duration_ms}ms")
            elif event.event_type == "worker_heartbeat":
                print(f"💓 Worker {event.worker_id}: {event.active} active, {event.processed} processed")
    finally:
        await subscriber.disconnect()
```

### WebSocket Integration

Stream events to web clients via WebSocket (requires `asynctasq-monitor` or custom implementation):

```python
from fastapi import FastAPI, WebSocket
from asynctasq_monitor import EventSubscriber

app = FastAPI()

@app.websocket("/events")
async def events_websocket(websocket: WebSocket):
    await websocket.accept()

    subscriber = EventSubscriber(redis_url="redis://localhost:6379")
    await subscriber.connect()

    try:
        async for event in subscriber.listen():
            await websocket.send_json({
                "type": event.event_type,
                "task_id": event.task_id,
                "task_name": event.task_name,
                "timestamp": event.timestamp.isoformat()
            })
    finally:
        await subscriber.disconnect()
```

## Queue Statistics

Beyond events, AsyncTasQ provides APIs for historical queue statistics:

```python
from asynctasq.monitoring import MonitoringService
from asynctasq.core.driver_factory import DriverFactory

async def get_stats():
    driver = DriverFactory.create_from_config()
    monitoring = MonitoringService(driver)

    # Get stats for a specific queue
    queue_stats = await monitoring.get_queue_stats("default")
    print(f"Queue depth: {queue_stats.depth}")
    print(f"Processing: {queue_stats.processing}")
    print(f"Completed total: {queue_stats.completed_total}")

    # Get all queue stats
    all_stats = await monitoring.get_all_queue_stats()

    # Get global stats
    global_stats = await monitoring.get_global_stats()
    print(f"Total pending: {global_stats['pending']}")

    # Get worker information
    workers = await monitoring.get_worker_stats()
    for worker in workers:
        print(f"Worker {worker.worker_id}: {worker.tasks_processed} processed")
```

## Integration with asynctasq-monitor

The `asynctasq-monitor` package provides a complete monitoring dashboard:

```bash
pip install asynctasq[monitor]
asynctasq-monitor --redis-url redis://localhost:6379
```

This starts a web server that:
- Subscribes to the events channel
- Stores metrics in a database
- Provides a real-time dashboard
- Exposes REST APIs for metrics

## Best Practices

### Production Monitoring

- **Enable event streaming** in production for observability
- **Monitor queue sizes** and alert when they exceed thresholds
- **Track worker health** via heartbeats and uptime
- **Set up alerts** for failed tasks and high retry rates
- **Use separate Redis** for events if you have high event volumes

### Performance Considerations

- Event emission has minimal overhead when disabled
- Redis Pub/Sub scales horizontally with Redis clustering
- Use connection pooling for high-throughput event consumption
- Consider event sampling for very high-volume systems

### Security

- Use authentication for Redis if events contain sensitive data
- Restrict access to monitoring dashboards
- Encrypt event data in transit if required

## Troubleshooting

### Events Not Appearing

1. Check `enable_event_emitter_redis` is `True`
2. Verify Redis connectivity: `redis-cli ping`
3. Confirm the correct channel name
4. Check worker logs for emission errors

### High Memory Usage

- Reduce heartbeat frequency if not needed
- Use event sampling for high-volume systems
- Monitor Redis memory usage for event backlog

### Missing Events

- Ensure workers are started after configuration
- Check for exceptions in worker logs
- Verify emitter registration with `EventRegistry.get_all()`</content>
<parameter name="filePath">/Users/adamrefaey/Code/asynctasq/docs/monitoring.md
