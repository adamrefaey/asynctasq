"""Tortoise ORM hook implementation."""

from __future__ import annotations

from typing import Any

from .base import BaseOrmHook

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
    """Hook for Tortoise ORM model serialization.

    Tortoise is async-native, so no special handling needed.
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
        """Fetch Tortoise model from database.

        Note: Tortoise ORM must be initialized before models can be fetched.
        Ensure your application calls `Tortoise.init()` at startup or in your
        task function before accessing models.
        """
        if not TORTOISE_AVAILABLE:
            raise ImportError("Tortoise ORM is not installed")

        # Proactively check if Tortoise is initialized before attempting fetch
        # This follows the pattern from Django ORM integration: detect issues early
        from tortoise import Tortoise

        if not Tortoise._inited:
            model_name = getattr(model_class, "__name__", str(model_class))
            raise RuntimeError(
                f"Tortoise ORM is not initialized. Cannot fetch {model_name} instance.\n\n"
                f"To fix this, initialize Tortoise in your task function before accessing models:\n\n"
                f"@task\n"
                f"async def my_task(product: Product):\n"
                f"    from tortoise import Tortoise\n"
                f"    if not Tortoise._inited:\n"
                f"        await Tortoise.init(\n"
                f"            db_url='postgres://user:pass@localhost/db',\n"
                f"            modules={{'models': ['__main__']}}\n"
                f"        )\n"
                f"    # Now you can use the model\n"
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
