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
        """Fetch Tortoise model from database."""
        if not TORTOISE_AVAILABLE:
            raise ImportError("Tortoise ORM is not installed")

        return await model_class.get(pk=pk)
