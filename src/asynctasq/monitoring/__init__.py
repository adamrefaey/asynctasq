"""Event emission system for task queue monitoring.

This module provides a comprehensive event system for real-time monitoring
of task and worker lifecycle events. Events are published to Redis Pub/Sub
for consumption by the asynctasq-monitor package.

Task Events:
    - task_enqueued: Task added to queue, awaiting execution
    - task_started: Worker began executing the task
    - task_completed: Task finished successfully
    - task_failed: Task failed after exhausting retries
    - task_reenqueued: Task failed but will be retried
    - task_cancelled: Task was cancelled/revoked before completion

Worker Events:
    - worker_online: Worker started and ready to process tasks
    - worker_heartbeat: Periodic status update (default: every 60s)
    - worker_offline: Worker shutting down gracefully

Architecture:
    Events flow from workers → Redis Pub/Sub → Monitor → WebSocket → UI

Example:
    >>> emitters = EventRegistry.init()
    >>> for emitter in emitters:
    ...     await emitter.emit_task_event(TaskEvent(
    ...         event_type=EventType.TASK_STARTED,
    ...         task_id="abc123",
    ...         task_name="SendEmailTask",
    ...         queue="default",
    ...         worker_id="worker-1"
    ...     ))
"""

from .emitters import EventEmitter, LoggingEventEmitter, RedisEventEmitter
from .monitoring import MonitoringService
from .registry import EventRegistry
from .types import EventType, TaskEvent, WorkerEvent

__all__ = [
    "EventEmitter",
    "EventRegistry",
    "EventType",
    "LoggingEventEmitter",
    "MonitoringService",
    "RedisEventEmitter",
    "TaskEvent",
    "WorkerEvent",
]
