"""Base ORM hook implementation."""

from __future__ import annotations

from functools import cache
from typing import Any

from ..base import AsyncTypeHook

# =============================================================================
# Model Class Import Cache
# =============================================================================

# Global unbounded cache for imported model classes.
# Using functools.cache (unbounded) instead of lru_cache for two reasons:
# 1. Model classes are few and long-lived - LRU eviction doesn't help
# 2. cache is slightly faster than lru_cache (no size tracking overhead)
# The cache key is (class_path, class_file) - both are hashable strings or None.

# Cached FunctionResolver instance - created lazily to avoid import overhead
_cached_resolver: Any = None


def _get_resolver() -> Any:
    """Get or create cached FunctionResolver instance.

    Performance optimization: Reuses single resolver instance instead of
    creating new one per import call. FunctionResolver is stateless for our
    use case (module resolution).
    """
    global _cached_resolver
    if _cached_resolver is None:
        from asynctasq.tasks.services.function_resolver import FunctionResolver

        _cached_resolver = FunctionResolver()
    return _cached_resolver


@cache
def _cached_import_model_class(class_path: str, class_file: str | None = None) -> type:
    """Import and return model class from class path with unbounded cache.

    Uses functools.cache (unbounded) instead of lru_cache because:
    - Model classes are typically few (tens, not thousands)
    - Once imported, they stay for the worker's lifetime
    - cache has less overhead than lru_cache (no size tracking)

    Args:
        class_path: Full class path (e.g., "__main__.User")
        class_file: Optional file path for __main__ module resolution

    Returns:
        The imported model class
    """
    module_name, class_name = class_path.rsplit(".", 1)

    # Use cached resolver for module resolution
    resolver = _get_resolver()
    module = resolver.get_module(module_name, module_file=class_file)

    return getattr(module, class_name)


def clear_resolver_cache() -> None:
    """Clear the cached FunctionResolver instance.

    Useful for testing or when module resolution state needs to be reset.
    """
    global _cached_resolver
    _cached_resolver = None


# =============================================================================
# Base ORM Hook
# =============================================================================


class BaseOrmHook(AsyncTypeHook[Any]):
    """Base class for ORM-specific hooks.

    Provides common functionality for detecting and serializing ORM models.
    Subclasses implement ORM-specific detection, PK extraction, and fetching.

    Performance optimizations:
    - Model class imports are globally cached via LRU cache (256 entries)
    - Subclasses can override `_requires_executor_for_import` to skip
      run_in_executor overhead when not needed (e.g., non-Django ORMs)
    """

    # Subclasses must define these
    orm_name: str = ""
    _type_key: str = ""  # Will be set dynamically

    # Override in subclasses that need run_in_executor for imports
    # Django needs it due to SynchronousOnlyOperation when user modules
    # have sync database operations at module level
    _requires_executor_for_import: bool = False

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

        Uses global LRU cache to avoid redundant imports when deserializing
        multiple ORM models of the same type. This is a significant performance
        optimization for batch deserialization.

        Subclasses can override this to add ORM-specific configuration,
        but should call super() to benefit from caching.

        Args:
            class_path: Full class path (e.g., "__main__.User")
            class_file: Optional file path for __main__ module resolution

        Returns:
            The imported model class
        """
        return _cached_import_model_class(class_path, class_file)

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

        Performance optimization: Only uses run_in_executor for ORMs that
        require it (like Django with SynchronousOnlyOperation). Other ORMs
        (SQLAlchemy, Tortoise) import directly without executor overhead.
        """
        import asyncio

        pk = data.get(self.type_key)
        class_path = data.get("__orm_class__")
        class_file = data.get("__orm_class_file__")

        if pk is None or class_path is None:
            raise ValueError(f"Invalid ORM reference: {data}")

        # Only use executor for ORMs that need it (Django async safety)
        # Other ORMs can import directly without executor overhead
        if self._requires_executor_for_import:
            loop = asyncio.get_running_loop()
            model_class = await loop.run_in_executor(
                None, self._import_model_class, class_path, class_file
            )
        else:
            model_class = self._import_model_class(class_path, class_file)

        return await self._fetch_model(model_class, pk)
