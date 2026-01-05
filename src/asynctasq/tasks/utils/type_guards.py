"""Type guards and type checking utilities for task types.

Performance-optimized with cached imports and fast type checking.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, TypeGuard

if TYPE_CHECKING:
    from asynctasq.tasks.core.base_task import BaseTask
    from asynctasq.tasks.types.function_task import FunctionTask

# Cache the FunctionTask class at module load time to avoid repeated imports
# This is safe because FunctionTask is a @final class that won't change at runtime
_FunctionTask: type | None = None


def _get_function_task_class() -> type:
    """Get FunctionTask class, caching on first access."""
    global _FunctionTask
    if _FunctionTask is None:
        from asynctasq.tasks.types.function_task import FunctionTask

        _FunctionTask = FunctionTask
    return _FunctionTask


def is_function_task_instance(task: BaseTask) -> TypeGuard[FunctionTask]:
    """Check if task is a FunctionTask instance.

    Args:
        task: Task instance to check

    Returns:
        True if task is FunctionTask instance
    """
    return isinstance(task, _get_function_task_class())


def is_function_task_class(task_class: type) -> bool:
    """Check if class is FunctionTask or subclass thereof.

    Uses issubclass for proper class hierarchy checking, which is the
    standard approach for type guards that check class relationships.

    Args:
        task_class: Class to check

    Returns:
        True if class is FunctionTask or a subclass
    """
    try:
        return issubclass(task_class, _get_function_task_class())
    except TypeError:
        # issubclass raises TypeError if task_class is not a class
        return False
