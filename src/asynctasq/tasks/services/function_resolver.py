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
    def get_function_reference(
        cls, func_module_name: str, func_name: str, func_file: str | None = None
    ) -> Callable[..., Any]:
        """Get function reference from module (handles __main__ module).

        Args:
            func_module_name: Module name (e.g., "myapp.tasks")
            func_name: Function name (e.g., "process_data")
            func_file: Optional file path for __main__ resolution

        Returns:
            Function reference

        Raises:
            ImportError: If module/function cannot be loaded
            FileNotFoundError: If __main__ file doesn't exist
        """
        # Handle __main__ module (running from script)
        if func_module_name == "__main__":
            if not func_file:
                raise ImportError(
                    f"Cannot import function {func_name} from __main__ "
                    f"(missing func_file in metadata)"
                )

            main_file = Path(func_file)
            if not main_file.exists():
                raise FileNotFoundError(
                    f"Cannot import function {func_name} from __main__ ({main_file} does not exist)"
                )

            # Use absolute path as cache key for consistency
            cache_key = str(main_file.resolve())

            # Check cache first to avoid re-executing module
            if cache_key in cls._module_cache:
                func_module = cls._module_cache[cache_key]
                logger.debug(f"Reusing cached module for {main_file}")
            else:
                # Generate stable, unique module name using file path hash
                # This prevents if __name__ == "__main__" blocks from executing
                path_hash = hashlib.sha256(cache_key.encode()).hexdigest()[:16]
                module_name = f"__asynctasq_main_{path_hash}__"

                # Check if module was already loaded in a previous run (edge case)
                if module_name in sys.modules:
                    func_module = sys.modules[module_name]
                    cls._module_cache[cache_key] = func_module
                    logger.debug(f"Found existing module {module_name} in sys.modules")
                else:
                    spec = importlib.util.spec_from_file_location(module_name, main_file)
                    if spec is None or spec.loader is None:
                        raise ImportError(f"Failed to load spec for {main_file}")

                    func_module = importlib.util.module_from_spec(spec)

                    # Add to sys.modules before exec to support relative imports
                    sys.modules[module_name] = func_module

                    try:
                        spec.loader.exec_module(func_module)
                        # Cache successfully loaded module
                        cls._module_cache[cache_key] = func_module
                        logger.debug(f"Loaded and cached module {module_name} from {main_file}")
                    except RuntimeError as e:
                        # Clean up on failure
                        sys.modules.pop(module_name, None)

                        if "cannot be called from a running event loop" in str(e):
                            logger.error(
                                f"Module {main_file} contains asyncio.run() at module level. "
                                f"This conflicts with the worker's event loop. "
                                f"Ensure asyncio.run() is inside 'if __name__ == \"__main__\":' block."
                            )
                        raise
                    except Exception as e:
                        # Clean up on failure
                        sys.modules.pop(module_name, None)
                        logger.exception(f"Failed to execute module {main_file}: {e}")
                        raise
        else:
            func_module = __import__(func_module_name, fromlist=[func_name])

        return getattr(func_module, func_name)

    @classmethod
    def clear_cache(cls) -> None:
        """Clear the module cache.

        Useful for testing or when module files have been modified.
        Note: This only clears the internal cache, not sys.modules.
        """
        cls._module_cache.clear()
        logger.debug("Cleared function resolver module cache")
