"""Base ORM hook implementation."""

from __future__ import annotations

from typing import Any

from ..base import AsyncTypeHook


class BaseOrmHook(AsyncTypeHook[Any]):
    """Base class for ORM-specific hooks.

    Provides common functionality for detecting and serializing ORM models.
    Subclasses implement ORM-specific detection, PK extraction, and fetching.
    """

    # Subclasses must define these
    orm_name: str = ""
    _type_key: str = ""  # Will be set dynamically

    @property
    def type_key(self) -> str:  # type: ignore[override]
        """Generate type key from ORM name."""
        return f"__orm:{self.orm_name}__"

    def _get_model_class_path(self, obj: Any) -> str:
        """Get the full class path for the model."""
        return f"{obj.__class__.__module__}.{obj.__class__.__name__}"

    def _get_model_class_file(self, obj: Any) -> str | None:
        """Get the file path for the model class (needed for __main__ modules)."""
        import inspect

        try:
            class_file = inspect.getfile(obj.__class__)
            # Only store if it's a real file (not built-in or C extension)
            if class_file and class_file.startswith("<"):
                return None
            return class_file
        except (TypeError, OSError):
            return None

    def _import_model_class(self, class_path: str, class_file: str | None = None) -> type:
        """Import and return model class from class path.

        Uses FunctionResolver to handle __main__ modules correctly.
        This ensures ORM models from user scripts can be properly imported
        in worker processes.

        Args:
            class_path: Full class path (e.g., "__main__.User")
            class_file: Optional file path for __main__ module resolution
        """
        from asynctasq.tasks.services.function_resolver import FunctionResolver

        module_name, class_name = class_path.rsplit(".", 1)

        # Use FunctionResolver for __main__ modules (handles file path resolution)
        # For regular modules, it falls back to standard import
        resolver = FunctionResolver()
        module = resolver.get_module(module_name, module_file=class_file)

        return getattr(module, class_name)

    def can_decode(self, data: dict[str, Any]) -> bool:
        """Check if this is an ORM reference we can decode."""
        return self.type_key in data and "__orm_class__" in data

    def encode(self, obj: Any) -> dict[str, Any]:
        """Encode ORM model to reference dictionary.

        Includes class file path for __main__ modules to enable proper
        deserialization in worker processes.
        """
        pk = self._get_model_pk(obj)
        class_path = self._get_model_class_path(obj)
        class_file = self._get_model_class_file(obj)

        result = {
            self.type_key: pk,
            "__orm_class__": class_path,
        }

        # Include class file for __main__ modules
        if class_file is not None:
            result["__orm_class_file__"] = class_file

        return result

    def _get_model_pk(self, obj: Any) -> Any:
        """Extract primary key from model. Override in subclasses."""
        raise NotImplementedError

    async def _fetch_model(self, model_class: type, pk: Any) -> Any:
        """Fetch model from database. Override in subclasses."""
        raise NotImplementedError

    async def decode_async(self, data: dict[str, Any]) -> Any:
        """Fetch ORM model from database using reference.

        Uses class file path if available to handle __main__ modules correctly.
        """
        pk = data.get(self.type_key)
        class_path = data.get("__orm_class__")
        class_file = data.get("__orm_class_file__")

        if pk is None or class_path is None:
            raise ValueError(f"Invalid ORM reference: {data}")

        model_class = self._import_model_class(class_path, class_file)
        return await self._fetch_model(model_class, pk)
