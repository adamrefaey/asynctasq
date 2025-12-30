"""Event emitter implementations for task queue monitoring."""

from abc import ABC, abstractmethod
from dataclasses import asdict
import logging
from typing import TYPE_CHECKING

import msgpack
from rich.console import Console

from asynctasq.config import Config

from .types import TaskEvent, WorkerEvent

if TYPE_CHECKING:
    from redis.asyncio import Redis

logger = logging.getLogger(__name__)
console = Console()


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
    """Beautiful event emitter that logs events with Rich formatting.

    This is the default emitter when Redis is not configured. Useful for
    development, debugging, or when monitoring is not required.

    Uses Rich for colorized, styled console output with icons and visual hierarchy.
    """

    def _format_task_event(self, event: TaskEvent) -> str:
        """Format a task event with colors and icons."""
        # Event type to emoji/icon mapping
        event_icons = {
            "task_started": "🚀",
            "task_completed": "✅",
            "task_failed": "❌",
            "task_retrying": "🔄",
        }

        icon = event_icons.get(event.event_type.value, "📋")
        event_name = event.event_type.value.replace("_", " ").title()

        return (
            f"{icon} [bold cyan]{event_name}[/bold cyan] "
            f"[dim]task=[/dim][yellow]{event.task_id[:8]}[/yellow] "
            f"[dim]queue=[/dim][magenta]{event.queue}[/magenta] "
            f"[dim]worker=[/dim][blue]{event.worker_id}[/blue]"
        )

    def _format_worker_event(self, event: WorkerEvent) -> str:
        """Format a worker event with colors and icons."""
        # Event type to emoji/icon mapping
        event_icons = {
            "worker_online": "🟢",
            "worker_offline": "🔴",
            "worker_heartbeat": "💓",
        }

        icon = event_icons.get(event.event_type.value, "⚙️")
        event_name = event.event_type.value.replace("_", " ").title()

        return (
            f"{icon} [bold green]{event_name}[/bold green] "
            f"[dim]worker=[/dim][blue]{event.worker_id}[/blue] "
            f"[dim]active=[/dim][cyan]{event.active}[/cyan] "
            f"[dim]processed=[/dim][green]{event.processed}[/green]"
        )

    async def emit(self, event: TaskEvent | WorkerEvent) -> None:
        """Log a task or worker event with beautiful Rich formatting."""
        if isinstance(event, TaskEvent):
            message = self._format_task_event(event)
        else:
            message = self._format_worker_event(event)

        logger.info(message)

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
        self.redis_url = redis_url or config.events.redis_url or config.redis.url
        self.channel = channel or config.events.channel
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
