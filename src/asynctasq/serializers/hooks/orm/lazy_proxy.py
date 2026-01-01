"""Lazy loading proxy for ORM models.

Enables deferred loading of ORM models when the ORM is not initialized
during task deserialization. The actual model is fetched when accessed.

This allows users to pass ORM model instances as task parameters without
requiring ORM initialization before worker startup. Models are automatically
fetched when tasks execute.
"""

from __future__ import annotations

import asyncio
from typing import Any


class LazyOrmProxy:
    """Proxy that defers ORM model loading until first access.

    This allows task parameters to reference ORM models even when the ORM
    is not initialized during deserialization. The actual model is fetched
    when the task accesses the parameter.

    Attributes:
        _model_class: The ORM model class to fetch
        _pk: The primary key value
        _fetch_callback: Async callback to fetch the model
        _resolved: Cached resolved model instance
    """

    __slots__ = ("_model_class", "_pk", "_fetch_callback", "_resolved")

    def __init__(
        self,
        model_class: type,
        pk: Any,
        fetch_callback: Any,  # Callable awaitable
    ) -> None:
        """Initialize lazy proxy.

        Args:
            model_class: The ORM model class
            pk: The primary key value
            fetch_callback: Async callable that fetches the model
        """
        object.__setattr__(self, "_model_class", model_class)
        object.__setattr__(self, "_pk", pk)
        object.__setattr__(self, "_fetch_callback", fetch_callback)
        object.__setattr__(self, "_resolved", None)

    async def _resolve(self) -> Any:
        """Resolve the proxy by fetching the actual model.

        Returns:
            The resolved ORM model instance

        Raises:
            RuntimeError: If ORM is still not initialized
        """
        resolved = object.__getattribute__(self, "_resolved")
        if resolved is not None:
            return resolved

        # Check if we need to initialize Tortoise ORM first
        try:
            from asynctasq.config import Config

            config = Config.get()
            if config.tortoise_orm is not None:
                # Auto-initialize Tortoise if config is available
                try:
                    from tortoise import Tortoise

                    if not Tortoise._inited:
                        await Tortoise.init(**config.tortoise_orm)
                        # Generate schemas to ensure tables exist
                        await Tortoise.generate_schemas(safe=True)
                except ImportError:
                    pass  # Tortoise not installed, fetch_callback will handle error
                except Exception as e:
                    # Log the error but don't crash - let fetch_callback handle it
                    import logging

                    logger = logging.getLogger(__name__)
                    logger.warning(
                        f"Failed to auto-initialize Tortoise ORM: {e}\n"
                        f"Make sure the modules specified in tortoise_config are importable.\n"
                        f"If running a script directly, you may need to set PYTHONPATH or use proper module paths."
                    )
        except Exception as e:
            # Log config access errors
            import logging

            logger = logging.getLogger(__name__)
            logger.warning(f"Failed to access Tortoise config: {e}")

        fetch_callback = object.__getattribute__(self, "_fetch_callback")
        model_class = object.__getattribute__(self, "_model_class")
        pk = object.__getattribute__(self, "_pk")

        resolved = await fetch_callback(model_class, pk)
        object.__setattr__(self, "_resolved", resolved)
        return resolved

    def __getattribute__(self, name: str) -> Any:
        """Intercept attribute access to trigger lazy loading.

        This is synchronous and will raise an error if the model hasn't
        been resolved yet. The proxy will auto-resolve when awaited.
        """
        # Allow access to special methods and private attributes
        if name.startswith("_") or name in (
            "__class__",
            "__dict__",
            "__slots__",
            "await_resolve",
        ):
            return object.__getattribute__(self, name)

        # Check if already resolved
        resolved = object.__getattribute__(self, "_resolved")
        if resolved is not None:
            return getattr(resolved, name)

        # Not resolved - provide helpful error message
        model_class = object.__getattribute__(self, "_model_class")
        raise RuntimeError(
            f"LazyOrmProxy for {model_class.__name__} has not been resolved yet.\n\n"
            f"The ORM model is lazy-loaded because the ORM was not initialized during deserialization.\n"
            f"To fix this, pass your Tortoise configuration to asynctasq.init():\n\n"
            f"    from asynctasq import init\n\n"
            f"    init(\n"
            f"        {{'driver': 'redis', 'redis': RedisConfig(url='redis://localhost')}},\n"
            f"        tortoise_config={{\n"
            f"            'db_url': 'postgres://user:pass@localhost/db',\n"
            f"            'modules': {{'models': ['myapp.models']}}\n"
            f"        }}\n"
            f"    )\n\n"
            f"This will auto-initialize Tortoise when the worker deserializes tasks.\n"
        )

    def __setattr__(self, name: str, value: Any) -> None:
        """Set attribute on resolved model."""
        resolved = object.__getattribute__(self, "_resolved")
        if resolved is not None:
            setattr(resolved, name, value)
        else:
            model_class = object.__getattribute__(self, "_model_class")
            raise RuntimeError(
                f"Cannot set attribute on unresolved LazyOrmProxy for {model_class.__name__}"
            )

    async def await_resolve(self) -> Any:
        """Public method to explicitly resolve the proxy.

        Returns:
            The resolved ORM model instance
        """
        return await self._resolve()

    def __await__(self):
        """Make the proxy awaitable.

        This allows users to resolve proxies by awaiting them:
            product = await product  # Resolves the proxy

        Returns:
            Generator that resolves to the ORM model instance
        """
        return self._resolve().__await__()

    def __repr__(self) -> str:
        """Return string representation."""
        model_class = object.__getattribute__(self, "_model_class")
        pk = object.__getattribute__(self, "_pk")
        resolved = object.__getattribute__(self, "_resolved")
        status = "resolved" if resolved is not None else "unresolved"
        return f"<LazyOrmProxy({model_class.__name__}, pk={pk}, {status})>"


def is_lazy_proxy(obj: Any) -> bool:
    """Check if an object is a LazyOrmProxy.

    Args:
        obj: Object to check

    Returns:
        True if obj is a LazyOrmProxy
    """
    return isinstance(obj, LazyOrmProxy)


async def resolve_lazy_proxies(obj: Any) -> Any:
    """Recursively resolve all LazyOrmProxy instances in a data structure.

    Resolves proxies in parallel when possible for better performance.

    Args:
        obj: Object that may contain lazy proxies (dict, list, tuple, or single value)

    Returns:
        The same structure with all lazy proxies resolved
    """
    if is_lazy_proxy(obj):
        return await obj.await_resolve()

    if isinstance(obj, dict):
        # Resolve all values in parallel
        keys = list(obj.keys())
        values = await asyncio.gather(*[resolve_lazy_proxies(v) for v in obj.values()])
        return dict(zip(keys, values, strict=False))

    if isinstance(obj, (list, tuple)):
        # Resolve all items in parallel
        resolved_items = await asyncio.gather(*[resolve_lazy_proxies(item) for item in obj])
        return type(obj)(resolved_items)

    return obj
