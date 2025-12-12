"""Type guards and type checking utilities for task types."""

from __future__ import annotations

from typing import TYPE_CHECKING, TypeGuard

if TYPE_CHECKING:
    from asynctasq.tasks.core.base_task import BaseTask
    from asynctasq.tasks.types.function_task import FunctionTask


def is_function_task_instance(task: BaseTask) -> TypeGuard[FunctionTask]:
    """Check if task is a FunctionTask instance.

    Args:
        task: Task instance to check

    Returns:
        True if task is FunctionTask instance
    """
    from asynctasq.tasks.types.function_task import FunctionTask

    return isinstance(task, FunctionTask)


def is_function_task_class(task_class: type) -> bool:
    """Check if class is FunctionTask or subclass thereof.

    Uses issubclass for proper class hierarchy checking, which is the
    standard approach for type guards that check class relationships.

    Args:
        task_class: Class to check

    Returns:
        True if class is FunctionTask or a subclass
    """
    from asynctasq.tasks.types.function_task import FunctionTask

    try:
        return issubclass(task_class, FunctionTask)
    except TypeError:
        # issubclass raises TypeError if task_class is not a class
        return False
