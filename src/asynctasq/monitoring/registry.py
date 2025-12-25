"""Event emitter registry for managing multiple event emitters."""

import logging

from asynctasq.config import Config

from .emitters import EventEmitter, LoggingEventEmitter, RedisEventEmitter
from .types import TaskEvent, WorkerEvent

logger = logging.getLogger(__name__)


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
        """Initialize the registry with emitters using config only."""
        EventRegistry._emitters.clear()
        config = Config.get()

        # Always include logging emitter as first emitter
        EventRegistry._emitters.add(LoggingEventEmitter())

        # Add Redis emitter only if enabled in config
        if config.events.enable_event_emitter_redis:
            EventRegistry._emitters.add(RedisEventEmitter())
