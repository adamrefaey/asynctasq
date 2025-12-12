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

    def _import_model_class(self, class_path: str) -> type:
        """Import and return model class from class path."""
        module_name, class_name = class_path.rsplit(".", 1)
        module = __import__(module_name, fromlist=[class_name])
        return getattr(module, class_name)

    def can_decode(self, data: dict[str, Any]) -> bool:
        """Check if this is an ORM reference we can decode."""
        return self.type_key in data and "__orm_class__" in data

    def encode(self, obj: Any) -> dict[str, Any]:
        """Encode ORM model to reference dictionary."""
        pk = self._get_model_pk(obj)
        class_path = self._get_model_class_path(obj)
        return {
            self.type_key: pk,
            "__orm_class__": class_path,
        }

    def _get_model_pk(self, obj: Any) -> Any:
        """Extract primary key from model. Override in subclasses."""
        raise NotImplementedError

    async def _fetch_model(self, model_class: type, pk: Any) -> Any:
        """Fetch model from database. Override in subclasses."""
        raise NotImplementedError

    async def decode_async(self, data: dict[str, Any]) -> Any:
        """Fetch ORM model from database using reference."""
        pk = data.get(self.type_key)
        class_path = data.get("__orm_class__")

        if pk is None or class_path is None:
            raise ValueError(f"Invalid ORM reference: {data}")

        model_class = self._import_model_class(class_path)
        return await self._fetch_model(model_class, pk)
