"""AsyncTasQ - Modern async-first task queue for Python."""

import importlib.metadata

try:
    __version__ = importlib.metadata.version("asynctasq")
except importlib.metadata.PackageNotFoundError:
    __version__ = "0.0.0"

from asynctasq.config import Config, ConfigOverrides
from asynctasq.monitoring import EventEmitter, EventRegistry


def init(
    config_overrides: ConfigOverrides | None = None,
    event_emitters: list[EventEmitter] | None = None,
) -> None:
    """Initialize AsyncTasQ with configuration and event emitters.

    This function must be called before using any AsyncTasQ functionality.
    It is recommended to call it as early as possible in your main script.

    Args:
        config_overrides: Optional configuration overrides to customize
            AsyncTasQ behavior (driver settings, timeouts, etc.)
        event_emitters: Optional list of additional event emitters to register
            for monitoring and logging task/worker events

    Example:
        >>> import asynctasq
        >>>
        >>> # Initialize with Redis driver
        >>> asynctasq.init({
        ...     'driver': 'redis',
        ...     'redis_url': 'redis://localhost:6379',
        ... })
        >>>
        >>> # Initialize with custom event emitters
        >>> from asynctasq.monitoring import LoggingEventEmitter
        >>> custom_emitter = LoggingEventEmitter()
        >>> asynctasq.init(
        ...     config_overrides={'driver': 'redis'},
        ...     event_emitters=[custom_emitter]
        ... )
    """
    # Apply configuration overrides
    if config_overrides:
        Config.set(**config_overrides)
    else:
        # Ensure config is initialized even without overrides
        Config.get()

    # Initialize default event emitters based on config
    EventRegistry.init()

    # Add any additional event emitters
    if event_emitters:
        for emitter in event_emitters:
            EventRegistry.add(emitter)
