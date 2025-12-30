"""Django ORM hook implementation."""

from __future__ import annotations

import asyncio
from typing import Any

from .base import BaseOrmHook

# =============================================================================
# Django Availability Detection
# =============================================================================

try:
    import django.db.models

    DJANGO_AVAILABLE = True
except ImportError:
    DJANGO_AVAILABLE = False
    django = None  # type: ignore[assignment]


# =============================================================================
# Django Hook
# =============================================================================


class DjangoOrmHook(BaseOrmHook):
    """Hook for Django model serialization.

    Automatically uses Django's async ORM methods when available (Django 3.1+).
    Falls back to sync-in-executor for older versions.
    """

    orm_name = "django"
    priority = 100

    def can_encode(self, obj: Any) -> bool:
        """Check if object is a Django model."""
        if not DJANGO_AVAILABLE or django is None:
            return False
        try:
            return isinstance(obj, django.db.models.Model)
        except Exception:
            return False

    def _get_model_pk(self, obj: Any) -> Any:
        """Extract primary key from Django model."""
        return obj.pk

    def _import_model_class(self, class_path: str, class_file: str | None = None) -> type:
        """Import Django model class.

        Relies on the user's script or DJANGO_SETTINGS_MODULE to configure Django.
        The FunctionResolver will handle patching settings.configure() to prevent
        "Settings already configured" errors when loading user modules.

        Args:
            class_path: Full class path (e.g., "__main__.Article")
            class_file: Optional file path for __main__ module resolution
        """
        # Call parent implementation - FunctionResolver handles Django settings patching
        return super()._import_model_class(class_path, class_file)

    async def _fetch_model(self, model_class: type, pk: Any) -> Any:
        """Fetch Django model from database."""
        if not DJANGO_AVAILABLE:
            raise ImportError("Django is not installed")

        # Try async method (Django 3.1+)
        try:
            return await model_class.objects.aget(pk=pk)
        except AttributeError:
            # Fallback to sync
            loop = asyncio.get_running_loop()
            return await loop.run_in_executor(None, lambda: model_class.objects.get(pk=pk))
