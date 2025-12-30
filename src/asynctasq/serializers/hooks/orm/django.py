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
        """Import Django model class with settings configuration.

        Ensures Django settings are configured before importing model classes
        to prevent "settings are not configured" errors during deserialization.

        Args:
            class_path: Full class path (e.g., "__main__.Article")
            class_file: Optional file path for __main__ module resolution
        """
        import logging
        import os
        import sys

        logger = logging.getLogger(__name__)

        # Ensure Django settings are configured before importing model classes
        # This prevents "settings are not configured" errors during deserialization
        if DJANGO_AVAILABLE:
            try:
                if "django" in sys.modules and "django.conf" in sys.modules:
                    from django.conf import settings as django_settings

                    # Check if settings are already configured
                    if not django_settings.configured:
                        # Settings not configured - configure with minimal settings
                        # Check if DJANGO_SETTINGS_MODULE is set
                        if "DJANGO_SETTINGS_MODULE" in os.environ:
                            # Use django.setup() to configure from settings module
                            import django

                            django.setup()
                            logger.debug(
                                f"Configured Django using DJANGO_SETTINGS_MODULE="
                                f"{os.environ['DJANGO_SETTINGS_MODULE']}"
                            )
                        else:
                            # No settings module - configure with minimal defaults
                            # This allows model imports to work without full Django setup
                            django_settings.configure(
                                INSTALLED_APPS=[],
                                DATABASES={
                                    "default": {
                                        "ENGINE": "django.db.backends.sqlite3",
                                        "NAME": ":memory:",
                                    }
                                },
                                SECRET_KEY="asynctasq-worker-temporary-key",
                                USE_TZ=True,
                            )
                            logger.debug(
                                "Configured Django with minimal settings for ORM model deserialization"
                            )
            except (ImportError, AttributeError) as e:
                # Django not available or couldn't configure - continue without configuring
                logger.debug(f"Could not configure Django settings: {e}")
            except RuntimeError as e:
                # Settings already configured by another thread/process
                if "Settings already configured" not in str(e):
                    raise

        # Call parent implementation to do the actual import
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
