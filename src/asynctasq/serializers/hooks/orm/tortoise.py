"""Tortoise ORM hook implementation.

Provides automatic serialization and lazy loading for Tortoise ORM models.
Models can be passed as task parameters and are automatically fetched when needed.

Key Features:
- Lazy loading when Tortoise is not initialized during deserialization
- Automatic model fetching before task execution
- Clear error messages for initialization issues
"""

from __future__ import annotations

from typing import Any

from .base import BaseOrmHook
from .lazy_proxy import LazyOrmProxy

# =============================================================================
# Tortoise Availability Detection
# =============================================================================

try:
    from tortoise.models import Model as TortoiseModel

    TORTOISE_AVAILABLE = True
except ImportError:
    TORTOISE_AVAILABLE = False
    TortoiseModel = None  # type: ignore[assignment, misc]


# =============================================================================
# Tortoise ORM Hook
# =============================================================================


class TortoiseOrmHook(BaseOrmHook):
    """Hook for Tortoise ORM model serialization with lazy loading support.

    Serializes Tortoise models to reference dictionaries (class path + PK)
    and deserializes them back to model instances. If Tortoise is not
    initialized during deserialization, returns a LazyOrmProxy that fetches
    the model when accessed.

    This enables passing Tortoise models as task parameters without requiring
    Tortoise initialization before worker startup.
    """

    orm_name = "tortoise"
    priority = 100

    def can_encode(self, obj: Any) -> bool:
        """Check if object is a Tortoise model."""
        if not TORTOISE_AVAILABLE or TortoiseModel is None:
            return False
        try:
            return isinstance(obj, TortoiseModel)
        except Exception:
            return False

    def _get_model_pk(self, obj: Any) -> Any:
        """Extract primary key from Tortoise model."""
        return obj.pk

    async def _fetch_model(self, model_class: type, pk: Any) -> Any:
        """Fetch Tortoise model from database or return lazy proxy.

        Behavior depends on Tortoise initialization state:
        - If initialized: Fetches model immediately from database
        - If not initialized: Returns LazyOrmProxy for deferred loading

        This allows tasks to initialize Tortoise themselves rather than
        requiring it before worker startup.

        Args:
            model_class: The Tortoise model class
            pk: The primary key value

        Returns:
            Either the fetched model instance or a LazyOrmProxy

        Raises:
            ImportError: If Tortoise ORM is not installed
        """
        if not TORTOISE_AVAILABLE:
            raise ImportError("Tortoise ORM is not installed")

        from tortoise import Tortoise

        if not Tortoise._inited:
            # Return lazy proxy - model will be fetched before task runs
            return LazyOrmProxy(
                model_class=model_class,
                pk=pk,
                fetch_callback=self._fetch_model_immediate,
            )

        # Tortoise is ready - fetch immediately
        return await self._fetch_model_immediate(model_class, pk)

    async def _fetch_model_immediate(self, model_class: type, pk: Any) -> Any:
        """Immediately fetch a Tortoise model from the database.

        This is called either:
        1. During deserialization if Tortoise is already initialized
        2. By LazyOrmProxy when the model is first accessed in the task

        Args:
            model_class: The Tortoise model class
            pk: The primary key value

        Returns:
            The fetched model instance

        Raises:
            RuntimeError: If Tortoise is still not initialized when trying to fetch
        """
        from tortoise import Tortoise

        if not Tortoise._inited:
            model_name = getattr(model_class, "__name__", str(model_class))
            raise RuntimeError(
                f"Tortoise ORM is not initialized. Cannot fetch {model_name} instance.\n\n"
                f"To use Tortoise models in tasks, initialize Tortoise in your task function:\n\n"
                f"@task\n"
                f"async def my_task(product: Product):\n"
                f"    from tortoise import Tortoise\n"
                f"    if not Tortoise._inited:\n"
                f"        await Tortoise.init(\n"
                f"            db_url='postgres://user:pass@localhost/db',\n"
                f"            modules={{'models': ['__main__', 'myapp.models']}}\n"
                f"        )\n"
                f"    # Now you can use the product parameter\n"
                f"    product.price = new_price\n"
                f"    await product.save()\n"
            )

        try:
            return await model_class.get(pk=pk)
        except Exception as e:
            # Check if this is a Tortoise connection error despite being initialized
            error_msg = str(e)
            if "default_connection" in error_msg and "cannot be None" in error_msg:
                raise RuntimeError(
                    f"Tortoise ORM initialization error while fetching {model_class.__name__}.\n"
                    f"Tortoise._inited is True, but connection is not available.\n"
                    f"This may indicate a configuration issue.\n\n"
                    f"Original error: {error_msg}"
                ) from e
            # Re-raise other errors
            raise
