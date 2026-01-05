"""Task serialization and deserialization (bytes ↔ BaseTask)."""

from __future__ import annotations

from datetime import datetime
import inspect
from typing import TYPE_CHECKING

from asynctasq.serializers.base_serializer import BaseSerializer
from asynctasq.serializers.msgspec_serializer import MsgspecSerializer
from asynctasq.tasks.core.task_config import TaskConfig
from asynctasq.tasks.services.function_resolver import FunctionResolver
from asynctasq.tasks.services.task_info_converter import TaskInfoConverter
from asynctasq.tasks.utils.type_guards import is_function_task_class, is_function_task_instance

if TYPE_CHECKING:
    from asynctasq.core.models import TaskInfo
    from asynctasq.tasks.core.base_task import BaseTask


class TaskSerializer:
    """Task serializer (BaseTask ↔ bytes).

    Delegates TaskInfo conversion to TaskInfoConverter and function resolution to FunctionResolver.
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
        # Filter out private/internal attributes (those starting with _)
        # Also filter callables and config since they're handled separately
        params = {
            key: value
            for key, value in task.__dict__.items()
            if not key.startswith("_") and not callable(value) and key != "config"
        }

        # For FunctionTask, store func reference in params for now
        # They'll be moved to metadata below
        func_module = None
        func_name = None
        func_file = None
        if is_function_task_instance(task):
            func = task.func  # type: ignore[attr-defined]
            func_module = func.__module__
            func_name = func.__name__
            # Always store func_file to support modules not in Python path
            # This allows workers to load the module from file if import fails
            try:
                func_file = func.__code__.co_filename
            except AttributeError:
                # Built-in or C extension functions don't have __code__
                pass

            # IMPORTANT: For FunctionTask, individual kwargs are stored as instance attributes
            # (e.g., self.user = user_value) but they're also in self.kwargs.
            # We only want them serialized ONCE in kwargs, not duplicated as top-level params.
            # Remove individual kwargs from params to avoid duplication during deserialization.
            task_kwargs = task.kwargs  # type: ignore[attr-defined]
            for kwarg_key in task_kwargs.keys():
                params.pop(kwarg_key, None)

            # Now add args and kwargs explicitly
            params["args"] = task.args  # type: ignore[attr-defined]
            params["kwargs"] = task_kwargs

            # Remove func and use_process from params since we can't/don't need to serialize them
            params.pop("func", None)
            params.pop("_use_process", None)

        # Build metadata
        metadata = {
            "task_id": task._task_id,
            "current_attempt": task._current_attempt,
            "dispatched_at": task._dispatched_at.isoformat() if task._dispatched_at else None,
            "queue": task.config.get("queue"),
            "max_attempts": task.config.get("max_attempts"),
            "retry_delay": task.config.get("retry_delay"),
            "timeout": task.config.get("timeout"),
            "visibility_timeout": task.config.get("visibility_timeout"),
        }

        # Add FunctionTask-specific metadata
        if is_function_task_instance(task):
            metadata["func_module"] = func_module
            metadata["func_name"] = func_name
            if func_file:
                metadata["func_file"] = func_file

        # Determine class path for serialization
        # For __main__ modules (including dynamically loaded ones), normalize to __main__
        module_name = task.__class__.__module__
        if module_name.startswith("__asynctasq_main_"):
            # This was loaded from a __main__ file, use __main__ for serialization
            module_name = "__main__"

        # Build serialization dict
        task_dict = {
            "class": f"{module_name}.{task.__class__.__name__}",
            "params": params,
            "metadata": metadata,
        }

        # Store the class file path for reliable deserialization
        # This helps when modules aren't in the worker's Python path
        # First try to use the stored original class file (for re-serialization)
        original_file = getattr(task, "_original_class_file", None)
        if original_file:
            task_dict["class_file"] = original_file
        else:
            # Otherwise try to get it from inspect
            try:
                class_file = inspect.getfile(task.__class__)
                # Only store if it's a real file (not built-in or C extension)
                if class_file and not class_file.startswith("<"):
                    task_dict["class_file"] = class_file
            except (TypeError, OSError):
                # If we can't get the file, that's okay for standard library/installed packages
                pass

        # Serialize to bytes
        return self.serializer.serialize(task_dict)

    async def deserialize(self, task_data: bytes) -> BaseTask:
        """Deserialize bytes to task instance.

        NOTE: This method is async because it calls self.serializer.deserialize() which
        handles async operations (e.g., ORM model fetching via async hooks). While the
        task reconstruction itself is synchronous (class import, instantiation, metadata
        restoration), the underlying serializer may perform async I/O operations.

        Returns:
            Task ready for execution

        Raises:
            ValueError: If FunctionTask metadata missing
            ImportError: If task class/function cannot be imported
        """
        # Deserialize bytes to dict
        task_dict = await self.serializer.deserialize(task_data)

        # Extract components
        class_path = task_dict["class"]
        params = task_dict["params"]
        metadata = task_dict["metadata"]
        class_file = task_dict.get("class_file")

        # Import and instantiate task class
        module_name, class_name = class_path.rsplit(".", 1)

        # Use FunctionResolver to load the module (handles __main__ consistently)
        module = self._function_resolver.get_module(module_name, class_file)
        task_class = getattr(module, class_name)

        # Special handling for FunctionTask: need to restore func first, then create instance
        if is_function_task_class(task_class):
            # For FunctionTask, we need func before instantiating
            # Get func from metadata first
            func_module_name = metadata.get("func_module")
            func_name = metadata.get("func_name")

            if not func_module_name or not func_name:
                raise ValueError("FunctionTask missing func_module or func_name in metadata")

            # Restore func reference using FunctionResolver
            func = self._function_resolver.get_function_reference(
                func_module_name, func_name, metadata.get("func_file")
            )

            # Create FunctionTask with func and params
            task = task_class(func, *params.get("args", ()), **params.get("kwargs", {}))
        else:
            # Create task instance with params
            task = task_class(**params)

        # Restore metadata
        task._task_id = metadata["task_id"]
        task._current_attempt = metadata["current_attempt"]
        dispatched_at_str = metadata.get("dispatched_at")
        if dispatched_at_str:
            try:
                task._dispatched_at = datetime.fromisoformat(dispatched_at_str)
            except (ValueError, TypeError):
                # Invalid datetime format or wrong type
                task._dispatched_at = None

        # Restore config (use TaskConfig factory to handle driver resolution)
        task.config = TaskConfig(
            queue=metadata["queue"],
            max_attempts=metadata.get("max_attempts", metadata.get("max_attempts")),
            retry_delay=metadata["retry_delay"],
            timeout=metadata["timeout"],
        )

        # Store the original class_file for re-serialization if it was a __main__ module
        if class_file:
            task._original_class_file = class_file

        return task

    async def to_task_info(
        self, raw_bytes: bytes, queue_name: str | None, status: str | None
    ) -> TaskInfo:
        """Convert raw bytes to TaskInfo (delegates to TaskInfoConverter).

        Returns:
            TaskInfo model with extracted metadata
        """
        return await self._task_info_converter.convert(raw_bytes, queue_name, status)
