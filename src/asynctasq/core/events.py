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

from abc import ABC, abstractmethod
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from enum import Enum
import logging
from typing import TYPE_CHECKING, Any

import msgpack

from asynctasq.config import Config

if TYPE_CHECKING:
    from redis.asyncio import Redis

logger = logging.getLogger(__name__)


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


class EventEmitter(ABC):
    """Abstract base class for event emitters.

    Concrete implementations must implement an emit method and
    a close method. Provides static helpers to build emitter instances and
    to compose them into a single emitter.
    """

    @abstractmethod
    async def emit(self, event: TaskEvent | WorkerEvent) -> None:
        """Emit a task or worker lifecycle event."""

    @abstractmethod
    async def close(self) -> None:
        """Close any connections held by the emitter."""


class LoggingEventEmitter(EventEmitter):
    """Simple event emitter that logs events (default, no dependencies).

    This is the default emitter when Redis is not configured. Useful for
    development, debugging, or when monitoring is not required.
    """

    async def emit(self, event: TaskEvent | WorkerEvent) -> None:
        """Log a task or worker event at INFO level."""
        if isinstance(event, TaskEvent):
            logger.info(
                "TaskEvent: %s task=%s queue=%s worker=%s",
                event.event_type.value,
                event.task_id,
                event.queue,
                event.worker_id,
            )
        else:
            logger.info(
                "WorkerEvent: %s worker=%s active=%d processed=%d",
                event.event_type.value,
                event.worker_id,
                event.active,
                event.processed,
            )

    async def close(self) -> None:
        """No-op for logging emitter."""


class RedisEventEmitter(EventEmitter):
    """Publishes events to Redis Pub/Sub for monitor consumption.

    Uses msgpack for efficient serialization (matches existing serializers).
    Lazy initialization prevents import-time side effects.

    Configuration:
        The Redis URL for events is read from global config in this order:
        1. events_redis_url if explicitly set
        2. Falls back to redis_url

        The Pub/Sub channel is configured via events_channel in global config
        (default: asynctasq:events).

        This allows using a different Redis instance for events/monitoring
        than the one used for the queue driver.

    Requirements:
        - Redis server running and accessible
        - redis[hiredis] package installed (included with asynctasq[monitor])

    The monitor package subscribes to the events channel and broadcasts
    received events to WebSocket clients for real-time updates.
    """

    def __init__(
        self,
        redis_url: str | None = None,
        channel: str | None = None,
    ) -> None:
        """Initialize the Redis event emitter.

        Args:
            redis_url: Redis connection URL (default from config's events_redis_url or redis_url)
            channel: Pub/Sub channel name (default from config's events_channel)
        """
        config = Config.get()
        # Use events_redis_url if set, otherwise fall back to redis_url
        self.redis_url = redis_url or config.events_redis_url or config.redis_url
        self.channel = channel or config.events_channel
        self._client: Redis | None = None

    async def _ensure_connected(self) -> None:
        """Lazily initialize Redis connection on first use."""
        if self._client is None:
            from redis.asyncio import Redis

            self._client = Redis.from_url(self.redis_url, decode_responses=False)

    def _serialize_event(self, event: TaskEvent | WorkerEvent) -> bytes:
        """Serialize an event to msgpack bytes.

        Converts the frozen dataclass to a dict with JSON-serializable values:
        - EventType enum → string value
        - datetime → ISO 8601 string
        - tuple → list (msgpack doesn't support tuples)
        """
        event_dict = asdict(event)
        event_dict["event_type"] = event.event_type.value
        event_dict["timestamp"] = event.timestamp.isoformat()

        # Convert tuple to list for msgpack compatibility
        if "queues" in event_dict and isinstance(event_dict["queues"], tuple):
            event_dict["queues"] = list(event_dict["queues"])

        result = msgpack.packb(event_dict, use_bin_type=True)
        if result is None:
            raise ValueError("msgpack.packb returned None")
        return result

    async def emit(self, event: TaskEvent | WorkerEvent) -> None:
        """Publish an event to Redis Pub/Sub."""
        await self._ensure_connected()
        assert self._client is not None

        try:
            message = self._serialize_event(event)
            await self._client.publish(self.channel, message)
        except Exception as e:
            event_type = "task" if isinstance(event, TaskEvent) else "worker"
            logger.warning("Failed to publish %s event to Redis: %s", event_type, e)

    async def close(self) -> None:
        """Close the Redis connection."""
        if self._client:
            await self._client.aclose()
            self._client = None


class EventRegistry:
    """Static registry for `EventEmitter` instances."""

    _emitters: set[EventEmitter] = set()

    @staticmethod
    def add(emitter: EventEmitter) -> None:
        """Register an EventEmitter in the registry (idempotent)."""
        EventRegistry._emitters.add(emitter)

    @staticmethod
    def get_all() -> set[EventEmitter]:
        """Return a shallow copy of registered emitters."""
        return set(EventRegistry._emitters)

    @staticmethod
    async def emit(event: TaskEvent | WorkerEvent) -> None:
        """Emit the event to all registered emitters.

        Exceptions from individual emitters are logged and do not prevent
        other emitters from receiving the event.
        """
        for emitter in EventRegistry.get_all():
            try:
                await emitter.emit(event)
            except Exception as e:
                logger.warning("Global emit failed for %s: %s", type(emitter).__name__, e)

    @staticmethod
    async def close_all() -> None:
        """Close all registered emitters, ignoring exceptions."""
        for emitter in EventRegistry.get_all():
            try:
                await emitter.close()
            except Exception as e:
                logger.warning("Failed to close emitter %s: %s", type(emitter).__name__, e)

    @staticmethod
    def init() -> None:
        """Initialize the registry with emitters using config only.

        Initialization rules:
        - Always include a `LoggingEventEmitter` (first) unless disabled in config.
        - If `Config.enable_event_emitter_redis` is True, add `RedisEventEmitter`.
        """
        EventRegistry._emitters.clear()
        config = Config.get()

        # Always include logging emitter as first emitter unless explicitly disabled
        EventRegistry._emitters.add(LoggingEventEmitter())

        # Add Redis emitter only if enabled in config
        if config.enable_event_emitter_redis:
            from redis.asyncio import Redis as _  # noqa: F401

            EventRegistry._emitters.add(RedisEventEmitter())
