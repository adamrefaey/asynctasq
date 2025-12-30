"""Function reference resolution for FunctionTask deserialization."""

from __future__ import annotations

from collections.abc import Callable
import hashlib
import importlib.util
import logging
from pathlib import Path
import sys
from typing import Any

logger = logging.getLogger(__name__)


class FunctionResolver:
    """Resolves function references from module paths for FunctionTask deserialization.

    Caches loaded modules to avoid re-executing module-level code on repeated imports.
    """

    # Cache for loaded __main__ modules: {file_path: module}
    _module_cache: dict[str, Any] = {}

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
        if module_name == "__main__":
            if not module_file:
                raise ImportError("Cannot import from __main__ (missing module_file)")

            main_file = Path(module_file)
            if not main_file.exists():
                raise FileNotFoundError(f"Cannot import from __main__ ({main_file} does not exist)")

            # Use absolute path as cache key for consistency
            cache_key = str(main_file.resolve())

            # Check cache first to avoid re-executing module
            if cache_key in cls._module_cache:
                return cls._module_cache[cache_key]

            # Generate stable, unique module name using file path hash
            # This prevents if __name__ == "__main__" blocks from executing
            path_hash = hashlib.sha256(cache_key.encode()).hexdigest()[:16]
            internal_module_name = f"__asynctasq_main_{path_hash}__"

            # Check if module was already loaded in a previous run (edge case)
            if internal_module_name in sys.modules:
                func_module = sys.modules[internal_module_name]
                cls._module_cache[cache_key] = func_module
                logger.debug(f"Found existing module {internal_module_name} in sys.modules")
                return func_module

            spec = importlib.util.spec_from_file_location(internal_module_name, main_file)
            if spec is None or spec.loader is None:
                raise ImportError(f"Failed to load spec for {main_file}")

            func_module = importlib.util.module_from_spec(spec)

            # Add to sys.modules before exec to support relative imports
            sys.modules[internal_module_name] = func_module

            # Temporarily patch Django settings to suppress "already configured" errors
            # This allows user modules to load even if they call settings.configure()
            # when settings are already configured
            django_patched = False
            original_configure = None

            try:
                # Check if Django is imported and patch the LazySettings class directly
                if "django" in sys.modules and "django.conf" in sys.modules:
                    import django.conf

                    # Get the LazySettings class (not an instance)
                    LazySettings = type(django.conf.settings)

                    # Save original configure method
                    original_configure = LazySettings.configure

                    def patched_configure(self: Any, *args: Any, **kwargs: Any) -> None:
                        """Patched configure that silently ignores 'already configured' errors."""
                        try:
                            original_configure(self, *args, **kwargs)
                        except RuntimeError as e:
                            if "Settings already configured" in str(e):
                                # Silently ignore - settings are already configured
                                logger.debug(
                                    f"Suppressed 'Settings already configured' error while loading {main_file}"
                                )
                                return
                            else:
                                raise

                    # Patch the class method, not the instance method
                    LazySettings.configure = patched_configure  # type: ignore[method-assign]
                    django_patched = True
                    logger.debug(f"Patched Django LazySettings.configure for loading {main_file}")
            except (ImportError, AttributeError) as e:
                # Django not available or couldn't patch - continue without patching
                logger.debug(f"Could not patch Django settings: {e}")
                pass

            try:
                spec.loader.exec_module(func_module)
                # Cache successfully loaded module
                cls._module_cache[cache_key] = func_module
                logger.debug(f"Loaded and cached module {internal_module_name} from {main_file}")
                return func_module
            except RuntimeError as e:
                error_msg = str(e)

                # Handle asyncio.run() at module level - this is fatal
                if "cannot be called from a running event loop" in error_msg:
                    sys.modules.pop(internal_module_name, None)
                    logger.error(
                        f"Module {main_file} contains asyncio.run() at module level. "
                        f"This conflicts with the worker's event loop. "
                        f"Ensure asyncio.run() is inside 'if __name__ == \"__main__\":' block."
                    )
                    raise

                # Unknown RuntimeError - clean up and re-raise
                sys.modules.pop(internal_module_name, None)
                raise
            except Exception as e:
                # Clean up on failure
                sys.modules.pop(internal_module_name, None)
                logger.exception(f"Failed to execute module {main_file}: {e}")
                raise
            finally:
                # Restore original Django settings.configure if it was patched
                if django_patched and original_configure is not None:
                    try:
                        import django.conf

                        LazySettings = type(django.conf.settings)
                        LazySettings.configure = original_configure  # type: ignore[method-assign]
                        logger.debug(
                            f"Restored original Django LazySettings.configure after loading {main_file}"
                        )
                    except (ImportError, AttributeError) as e:
                        logger.debug(f"Could not restore Django settings: {e}")
                        pass
        else:
            # For non-__main__ modules, first try standard import
            # If that fails and we have a module_file, load from file
            try:
                return __import__(module_name, fromlist=["__name__"])
            except ModuleNotFoundError:
                if module_file:
                    # Module not in path, but we have a file - load it directly
                    logger.debug(
                        f"Module {module_name} not in Python path, loading from {module_file}"
                    )
                    module_path = Path(module_file)
                    if not module_path.exists():
                        raise FileNotFoundError(
                            f"Cannot import module {module_name} ({module_path} does not exist)"
                        ) from None

                    # Use absolute path as cache key
                    cache_key = str(module_path.resolve())
                    if cache_key in cls._module_cache:
                        return cls._module_cache[cache_key]

                    # Load module from file with its original module name
                    # Check if already loaded
                    if module_name in sys.modules:
                        loaded_module = sys.modules[module_name]
                        cls._module_cache[cache_key] = loaded_module
                        return loaded_module

                    spec = importlib.util.spec_from_file_location(module_name, module_path)
                    if spec is None or spec.loader is None:
                        raise ImportError(f"Failed to load spec for {module_path}") from None

                    loaded_module = importlib.util.module_from_spec(spec)
                    sys.modules[module_name] = loaded_module

                    try:
                        spec.loader.exec_module(loaded_module)
                        cls._module_cache[cache_key] = loaded_module
                        logger.debug(f"Loaded module {module_name} from {module_path}")
                        return loaded_module
                    except ModuleNotFoundError as e:
                        # Module file exists but has missing dependencies
                        sys.modules.pop(module_name, None)
                        raise ImportError(
                            f"Module {module_name} loaded from {module_path} has missing "
                            f"dependencies: {e.name}. Ensure all required packages are installed "
                            f"in the worker environment."
                        ) from e
                    except Exception as e:
                        sys.modules.pop(module_name, None)
                        logger.exception(f"Failed to execute module {module_path}: {e}")
                        raise
                else:
                    # No file path provided, re-raise the original error
                    raise

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

        # If it's a TaskFunctionWrapper, unwrap it to get the actual function
        # This happens when deserializing a @task decorated function
        if hasattr(func_attr, "__wrapped__"):
            return func_attr.__wrapped__

        return func_attr

    @classmethod
    def clear_cache(cls) -> None:
        """Clear the module cache.

        Useful for testing or when module files have been modified.
        Note: This only clears the internal cache, not sys.modules.
        """
        cls._module_cache.clear()
        logger.debug("Cleared function resolver module cache")
