"""Task configuration TypedDict.

This module provides a type-safe configuration structure for AsyncTasQ tasks
using TypedDict for flexible, dictionary-based configuration.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, NotRequired, TypedDict

if TYPE_CHECKING:
    from asynctasq.drivers import DriverType
    from asynctasq.drivers.base_driver import BaseDriver


class TaskConfig(TypedDict, total=False):
    """Type-safe task configuration dictionary.

    Use this for configuring task execution parameters in task classes.
    All fields are optional (NotRequired) with sensible defaults.

    Examples
    --------
    Define task defaults using class-level configuration:

    >>> class SendEmailTask(AsyncTask[str]):
    ...     config: TaskConfig = {
    ...         "queue": "emails",
    ...         "max_attempts": 5,
    ...         "timeout": 30,
    ...     }

    Override specific settings:

    >>> class ProcessData(AsyncProcessTask[dict]):
    ...     config: TaskConfig = {
    ...         "queue": "cpu_intensive",
    ...         "max_attempts": 3,
    ...         "retry_delay": 120,
    ...         "timeout": 600,
    ...         "correlation_id": "data-pipeline-v1",
    ...     }

    Attributes
    ----------
    queue : str, optional
        Queue name for task dispatch (default: "default")
    max_attempts : int, optional
        Maximum retry attempts including initial execution (default: 3)
    retry_delay : int, optional
        Seconds to wait between retry attempts (default: 60)
    timeout : int | None, optional
        Task execution timeout in seconds, None for no timeout (default: None)
    driver : DriverType | BaseDriver | None, optional
        Optional driver override for routing this task to a specific backend (default: None)
    correlation_id : str | None, optional
        Optional correlation ID for distributed tracing and request tracking (default: None)

    Notes
    -----
    - All configuration values can be overridden at runtime using method chaining
    - The configuration is merged with defaults during task initialization
    - driver allows routing specific tasks to different queue backends
    - correlation_id is useful for tracking related tasks across distributed systems
    """

    queue: NotRequired[str]
    max_attempts: NotRequired[int]
    retry_delay: NotRequired[int]
    timeout: NotRequired[int | None]
    driver: NotRequired[DriverType | BaseDriver | None]
    correlation_id: NotRequired[str | None]
