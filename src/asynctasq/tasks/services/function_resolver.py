"""Function reference resolution for FunctionTask deserialization.

Performance-optimized for high-throughput task execution.
"""

from __future__ import annotations

from collections.abc import Callable
import importlib.util
import logging
from pathlib import Path
import sys
from typing import Any, Final

logger = logging.getLogger(__name__)

# Pre-compute constant for fast module name generation
_MODULE_PREFIX: Final[str] = "__asynctasq_main_"
_MODULE_SUFFIX: Final[str] = "__"

# Fast counter for unique module names (no hashing needed)
_module_counter: int = 0


class FunctionResolver:
    """Resolves function references from module paths for FunctionTask deserialization.

    Caches loaded modules to avoid re-executing module-level code on repeated imports.

    Performance optimizations:
    - Fast counter-based module naming instead of SHA256 hashing
    - Cache key normalization done once per lookup
    - Minimized Path operations
    - Reduced logging overhead
    """

    __slots__ = ()

    # Cache for loaded modules: {absolute_file_path: module}
    _module_cache: dict[str, Any] = {}
    # Reverse cache: {absolute_file_path: internal_module_name} for sys.modules lookup
    _name_cache: dict[str, str] = {}

    @classmethod
    def get_module(cls, module_name: str, module_file: str | None = None) -> Any:
        """Get module reference, handling __main__ modules specially.

        Args:
            module_name: Module name (e.g., "myapp.tasks" or "__main__")
            module_file: Optional file path for __main__ resolution

        Returns:
            Module reference

        Raises:
            ImportError: If module cannot be loaded
            FileNotFoundError: If __main__ file doesn't exist
        """
        # Fast path: non-__main__ modules (most common case)
        if module_name != "__main__":
            return cls._get_regular_module(module_name, module_file)

        # __main__ module handling
        if not module_file:
            raise ImportError("Cannot import from __main__ (missing module_file)")

        # Normalize path once and use as cache key
        cache_key = str(Path(module_file).resolve())

        # Fast cache check
        cached = cls._module_cache.get(cache_key)
        if cached is not None:
            return cached

        # Check if we already have a module name for this file
        internal_module_name = cls._name_cache.get(cache_key)
        if internal_module_name is not None:
            # Check sys.modules (handles edge case of external loading)
            existing = sys.modules.get(internal_module_name)
            if existing is not None:
                cls._module_cache[cache_key] = existing
                return existing

        # Generate new unique module name using fast counter
        global _module_counter
        _module_counter += 1
        internal_module_name = f"{_MODULE_PREFIX}{_module_counter}{_MODULE_SUFFIX}"
        cls._name_cache[cache_key] = internal_module_name

        # Load module from file
        main_file = Path(module_file)
        if not main_file.exists():
            raise FileNotFoundError(f"Cannot import from __main__ ({main_file} does not exist)")

        return cls._load_module_from_file(main_file, internal_module_name, cache_key, is_main=True)

    @classmethod
    def _get_regular_module(cls, module_name: str, module_file: str | None) -> Any:
        """Get non-__main__ module (optimized hot path)."""
        # Try standard import first (most common case)
        try:
            return __import__(module_name, fromlist=["__name__"])
        except ModuleNotFoundError:
            pass

        # Module not in path - try loading from file if available
        if not module_file:
            raise ModuleNotFoundError(f"No module named '{module_name}'")

        module_path = Path(module_file)
        if not module_path.exists():
            raise FileNotFoundError(
                f"Cannot import module {module_name} ({module_path} does not exist)"
            )

        # Use absolute path as cache key
        cache_key = str(module_path.resolve())

        # Fast cache check
        cached = cls._module_cache.get(cache_key)
        if cached is not None:
            return cached

        # Check sys.modules
        existing = sys.modules.get(module_name)
        if existing is not None:
            cls._module_cache[cache_key] = existing
            return existing

        return cls._load_module_from_file(module_path, module_name, cache_key, is_main=False)

    @classmethod
    def _load_module_from_file(
        cls,
        file_path: Path,
        module_name: str,
        cache_key: str,
        *,
        is_main: bool,
    ) -> Any:
        """Load module from file path (shared logic for main and regular modules)."""
        spec = importlib.util.spec_from_file_location(module_name, file_path)
        if spec is None or spec.loader is None:
            raise ImportError(f"Failed to load spec for {file_path}")

        func_module = importlib.util.module_from_spec(spec)

        # Add to sys.modules before exec to support relative imports
        sys.modules[module_name] = func_module

        # Django patching for __main__ modules only
        django_state = None
        if is_main:
            django_state = cls._patch_django_if_needed(file_path)

        try:
            spec.loader.exec_module(func_module)
            cls._module_cache[cache_key] = func_module
            return func_module
        except RuntimeError as e:
            sys.modules.pop(module_name, None)
            error_msg = str(e)
            if "cannot be called from a running event loop" in error_msg:
                logger.error(
                    f"Module {file_path} contains asyncio.run() at module level. "
                    f"Ensure asyncio.run() is inside 'if __name__ == \"__main__\":' block."
                )
            raise
        except ModuleNotFoundError as e:
            sys.modules.pop(module_name, None)
            raise ImportError(
                f"Module {module_name} loaded from {file_path} has missing "
                f"dependencies: {e.name}. Ensure all required packages are installed."
            ) from e
        except Exception:
            sys.modules.pop(module_name, None)
            raise
        finally:
            if django_state is not None:
                cls._restore_django(django_state)

    @classmethod
    def _patch_django_if_needed(cls, file_path: Path) -> tuple[Any, Any] | None:
        """Patch Django settings.configure if Django is loaded."""
        if "django.conf" not in sys.modules:
            return None

        try:
            import django.conf

            LazySettings = type(django.conf.settings)
            original_configure = LazySettings.configure

            def patched_configure(self: Any, *args: Any, **kwargs: Any) -> None:
                try:
                    original_configure(self, *args, **kwargs)
                except RuntimeError as e:
                    if "Settings already configured" not in str(e):
                        raise

            LazySettings.configure = patched_configure  # type: ignore[method-assign]
            return (LazySettings, original_configure)
        except (ImportError, AttributeError):
            return None

    @classmethod
    def _restore_django(cls, state: tuple[Any, Any]) -> None:
        """Restore original Django settings.configure."""
        try:
            LazySettings, original_configure = state
            LazySettings.configure = original_configure  # type: ignore[method-assign]
        except (ImportError, AttributeError):
            pass

    @classmethod
    def get_function_reference(
        cls, func_module_name: str, func_name: str, func_file: str | None = None
    ) -> Callable[..., Any]:
        """Get function reference from module (handles __main__ module).

        Args:
            func_module_name: Module name (e.g., "myapp.tasks")
            func_name: Function name (e.g., "process_data")
            func_file: Optional file path for __main__ resolution

        Returns:
            Function reference (unwrapped if it's a TaskFunctionWrapper)

        Raises:
            ImportError: If module/function cannot be loaded
            FileNotFoundError: If __main__ file doesn't exist
        """
        func_module = cls.get_module(func_module_name, func_file)
        func_attr = getattr(func_module, func_name)

        # Unwrap TaskFunctionWrapper if present (faster than hasattr + getattr)
        wrapped = getattr(func_attr, "__wrapped__", None)
        return wrapped if wrapped is not None else func_attr

    @classmethod
    def clear_cache(cls) -> None:
        """Clear the module cache."""
        cls._module_cache.clear()
        cls._name_cache.clear()
