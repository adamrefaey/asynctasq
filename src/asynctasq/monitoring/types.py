"""Event types and data structures for task queue monitoring."""

from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import Enum
from typing import Any


class EventType(str, Enum):
    """Event types for task and worker lifecycle tracking.

    Each event type corresponds to a specific state change in the
    task queue lifecycle, enabling real-time monitoring and metrics.
    """

    # Task lifecycle events
    TASK_ENQUEUED = "task_enqueued"
    TASK_STARTED = "task_started"
    TASK_COMPLETED = "task_completed"
    TASK_FAILED = "task_failed"
    TASK_REENQUEUED = "task_reenqueued"
    TASK_CANCELLED = "task_cancelled"

    # Worker lifecycle events
    WORKER_ONLINE = "worker_online"
    WORKER_HEARTBEAT = "worker_heartbeat"
    WORKER_OFFLINE = "worker_offline"


@dataclass(frozen=True)
class TaskEvent:
    """Immutable event emitted during task lifecycle.

    Attributes:
        event_type: The type of task event
        task_id: Unique task identifier (UUID)
        task_name: Name of the task class/function
        queue: Queue the task was dispatched to
        worker_id: Worker processing the task (if applicable)
        timestamp: When the event occurred (UTC)
        attempt: Current retry attempt number (1-based)
        duration_ms: Execution duration in milliseconds (for completed/failed)
        result: Task result (for completed events, optional)
        error: Error message (for failed/retrying events)
        traceback: Full traceback string (for failed events)
    """

    event_type: EventType
    task_id: str
    task_name: str
    queue: str
    worker_id: str
    timestamp: datetime = field(default_factory=lambda: datetime.now(UTC))
    attempt: int = 1
    duration_ms: int | None = None
    result: Any = None
    error: str | None = None
    traceback: str | None = None


@dataclass(frozen=True)
class WorkerEvent:
    """Immutable event emitted during worker lifecycle.

    Worker events track the state of worker processes, enabling:
    - Health monitoring via heartbeats
    - Load balancing decisions based on active task counts
    - Metrics aggregation across the worker pool

    Attributes:
        event_type: The type of worker event (online/heartbeat/offline)
        worker_id: Unique worker identifier (e.g., "worker-a1b2c3d4")
        hostname: System hostname where worker runs
        timestamp: When the event occurred (UTC)
        freq: Heartbeat frequency in seconds (default 60)
        active: Number of currently executing tasks
        processed: Total tasks processed by this worker
        queues: Queue names the worker consumes from
        sw_ident: Software identifier ("asynctasq")
        sw_ver: Software version string
        uptime_seconds: How long the worker has been running
    """

    event_type: EventType
    worker_id: str
    hostname: str
    timestamp: datetime = field(default_factory=lambda: datetime.now(UTC))
    freq: float = 60.0  # Heartbeat frequency in seconds
    active: int = 0  # Currently executing tasks
    processed: int = 0  # Total tasks processed
    queues: tuple[str, ...] = ()  # Use tuple for immutability
    sw_ident: str = "asynctasq"
    sw_ver: str = "1.0.0"
    uptime_seconds: int | None = None
