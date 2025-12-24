"""Structured logging helpers for task context."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from asynctasq.tasks.core.base_task import BaseTask


def get_task_context(task: BaseTask) -> dict[str, Any]:
    """Extract logging context from task (task_id, class, queue, current_attempt, max_attempts, correlation_id)."""
    context = {
        "task_id": task._task_id,
        "task_class": task.__class__.__name__,
        "queue": task.config.get("queue"),
        "current_attempt": task._current_attempt,
        "max_attempts": task.config.get("max_attempts"),
    }
    # Add correlation_id if present for distributed tracing
    if task.config.get("correlation_id") is not None:
        context["correlation_id"] = task.config.get("correlation_id")
    return context


def log_task_info(task: BaseTask, message: str, **extra: Any) -> None:
    """Log info with task context."""
    logger = logging.getLogger(task.__class__.__module__)
    context = get_task_context(task)
    context.update(extra)
    logger.info(message, extra=context)


def log_task_debug(task: BaseTask, message: str, **extra: Any) -> None:
    """Log debug with task context."""
    logger = logging.getLogger(task.__class__.__module__)
    context = get_task_context(task)
    context.update(extra)
    logger.debug(message, extra=context)


def log_task_warning(task: BaseTask, message: str, **extra: Any) -> None:
    """Log warning with task context."""
    logger = logging.getLogger(task.__class__.__module__)
    context = get_task_context(task)
    context.update(extra)
    logger.warning(message, extra=context)


def log_task_error(task: BaseTask, message: str, exc_info: bool = True, **extra: Any) -> None:
    """Log error with task context."""
    logger = logging.getLogger(task.__class__.__module__)
    context = get_task_context(task)
    context.update(extra)
    logger.error(message, extra=context, exc_info=exc_info)
