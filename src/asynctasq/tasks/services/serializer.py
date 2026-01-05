"""Task serialization and deserialization (bytes ↔ BaseTask).

Performance-optimized for high-throughput task processing.
"""

from __future__ import annotations

from datetime import datetime
import inspect
from typing import TYPE_CHECKING, Any

from asynctasq.serializers.base_serializer import BaseSerializer
from asynctasq.serializers.msgspec_serializer import MsgspecSerializer
from asynctasq.tasks.services.function_resolver import FunctionResolver
from asynctasq.tasks.services.task_info_converter import TaskInfoConverter
from asynctasq.tasks.utils.type_guards import is_function_task_class, is_function_task_instance

if TYPE_CHECKING:
    from asynctasq.core.models import TaskInfo
    from asynctasq.tasks.core.base_task import BaseTask


class TaskSerializer:
    """Task serializer (BaseTask ↔ bytes).

    Performance optimizations:
    - Uses centralized type guards from type_guards module
    - Minimized dict operations
    - Reduced attribute access overhead
    - Optimized deserialization path

    Note: Does not use __slots__ to allow instance attribute patching in tests.
    Memory overhead is negligible as TaskSerializer is typically instantiated once per worker.
    """

    def __init__(self, serializer: BaseSerializer | None = None) -> None:
        """Initialize with optional custom serializer (defaults to MsgspecSerializer)."""
        self.serializer = serializer or MsgspecSerializer()
        self._task_info_converter = TaskInfoConverter(self.serializer)
        self._function_resolver = FunctionResolver()

    def serialize(self, task: BaseTask) -> bytes:
        """Serialize task to bytes.

        Returns:
            Serialized task data
        """
        task_dict = task.__dict__
        config = task.config

        # Build params dict - filter private attributes and non-serializable items
        params: dict[str, Any] = {}
        for key, value in task_dict.items():
            if key[0] != "_" and not callable(value) and key != "config":
                params[key] = value

        # FunctionTask-specific handling
        func_module: str | None = None
        func_name: str | None = None
        func_file: str | None = None
        is_function_task = is_function_task_instance(task)

        if is_function_task:
            func = task.func  # type: ignore[attr-defined]
            func_module = func.__module__
            func_name = func.__name__

            # Get func_file if available
            code = getattr(func, "__code__", None)
            if code is not None:
                func_file = code.co_filename

            # Remove duplicated kwargs from params
            task_kwargs = task.kwargs  # type: ignore[attr-defined]
            for kwarg_key in task_kwargs:
                params.pop(kwarg_key, None)

            # Add args/kwargs, remove non-serializable items
            params["args"] = task.args  # type: ignore[attr-defined]
            params["kwargs"] = task_kwargs
            params.pop("func", None)
            params.pop("_use_process", None)

        # Build metadata dict
        dispatched_at = task._dispatched_at
        metadata: dict[str, Any] = {
            "task_id": task._task_id,
            "current_attempt": task._current_attempt,
            "dispatched_at": dispatched_at.isoformat() if dispatched_at else None,
            "queue": config.get("queue"),
            "max_attempts": config.get("max_attempts"),
            "retry_delay": config.get("retry_delay"),
            "timeout": config.get("timeout"),
            "visibility_timeout": config.get("visibility_timeout"),
        }

        # Add FunctionTask metadata
        if is_function_task:
            metadata["func_module"] = func_module
            metadata["func_name"] = func_name
            if func_file:
                metadata["func_file"] = func_file

        # Normalize module name for __main__ modules
        module_name = task.__class__.__module__
        if module_name.startswith("__asynctasq_main_"):
            module_name = "__main__"

        # Build final task dict
        task_data: dict[str, Any] = {
            "class": f"{module_name}.{task.__class__.__name__}",
            "params": params,
            "metadata": metadata,
        }

        # Add class file for reliable deserialization
        original_file = getattr(task, "_original_class_file", None)
        if original_file:
            task_data["class_file"] = original_file
        else:
            try:
                class_file = inspect.getfile(task.__class__)
                if class_file and class_file[0] != "<":
                    task_data["class_file"] = class_file
            except (TypeError, OSError):
                pass

        return self.serializer.serialize(task_data)

    async def deserialize(self, task_data: bytes) -> BaseTask:
        """Deserialize bytes to task instance.

        Returns:
            Task ready for execution

        Raises:
            ValueError: If FunctionTask metadata missing
            ImportError: If task class/function cannot be imported
        """
        # Deserialize bytes to dict
        task_dict = await self.serializer.deserialize(task_data)

        # Extract components (single dict access)
        class_path: str = task_dict["class"]
        params: dict[str, Any] = task_dict["params"]
        metadata: dict[str, Any] = task_dict["metadata"]
        class_file: str | None = task_dict.get("class_file")

        # Parse class path - validate format first
        last_dot = class_path.rfind(".")
        if last_dot <= 0:  # No dot found (-1) or dot at start (0) is invalid
            raise ValueError(
                f"Invalid class path format: '{class_path}' (must be 'module.ClassName')"
            )
        module_name = class_path[:last_dot]
        class_name = class_path[last_dot + 1 :]

        # Load module and get class
        module = self._function_resolver.get_module(module_name, class_file)
        task_class = getattr(module, class_name)

        # Create task instance
        if is_function_task_class(task_class):
            # Get func metadata
            func_module_name = metadata.get("func_module")
            func_name = metadata.get("func_name")

            if not func_module_name or not func_name:
                raise ValueError("FunctionTask missing func_module or func_name in metadata")

            # Restore func reference
            func = self._function_resolver.get_function_reference(
                func_module_name, func_name, metadata.get("func_file")
            )

            # Create FunctionTask
            task = task_class(func, *params.get("args", ()), **params.get("kwargs", {}))
        else:
            task = task_class(**params)

        # Restore metadata (direct attribute assignment is faster)
        task._task_id = metadata["task_id"]
        task._current_attempt = metadata["current_attempt"]

        # Parse dispatched_at
        dispatched_at_str = metadata.get("dispatched_at")
        if dispatched_at_str:
            try:
                task._dispatched_at = datetime.fromisoformat(dispatched_at_str)
            except (ValueError, TypeError):
                task._dispatched_at = None
        else:
            task._dispatched_at = None

        # Restore config (inline dict construction is faster than TaskConfig factory)
        task.config = {  # type: ignore[assignment]
            "queue": metadata["queue"],
            "max_attempts": metadata.get("max_attempts"),
            "retry_delay": metadata["retry_delay"],
            "timeout": metadata["timeout"],
            "visibility_timeout": metadata.get("visibility_timeout"),
        }

        # Store class_file for re-serialization
        if class_file:
            task._original_class_file = class_file  # type: ignore[attr-defined]

        return task

    async def to_task_info(
        self, raw_bytes: bytes, queue_name: str | None, status: str | None
    ) -> TaskInfo:
        """Convert raw bytes to TaskInfo (delegates to TaskInfoConverter).

        Returns:
            TaskInfo model with extracted metadata
        """
        return await self._task_info_converter.convert(raw_bytes, queue_name, status)
