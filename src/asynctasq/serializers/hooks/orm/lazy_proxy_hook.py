"""Serialization hook for LazyOrmProxy objects.

This hook allows LazyOrmProxy objects to be serialized for retry attempts.
When a task fails and needs to be retried, the proxy is serialized back to
the ORM model reference format (class path + PK).
"""

from __future__ import annotations

from typing import Any

from ..base import TypeHook
from .lazy_proxy import LazyOrmProxy


class LazyOrmProxyHook(TypeHook):
    """Hook for serializing LazyOrmProxy objects.

    Serializes lazy proxies back to ORM model references for retry attempts.
    This ensures that tasks can be retried even if the ORM model hasn't been
    resolved yet.
    """

    type_key = "__lazy_orm_proxy__"
    priority = 150  # Higher priority than ORM hooks to catch proxies first

    def can_encode(self, obj: Any) -> bool:
        """Check if object is a LazyOrmProxy."""
        return isinstance(obj, LazyOrmProxy)

    def encode(self, obj: LazyOrmProxy) -> dict[str, Any]:
        """Encode LazyOrmProxy to dictionary.

        Returns the same format as ORM model references:
        {
            "__type__": "__lazy_orm_proxy__",
            "model_class": "path.to.Model",
            "pk": 123
        }
        """
        model_class = object.__getattribute__(obj, "_model_class")
        pk = object.__getattribute__(obj, "_pk")

        return {
            "__type__": self.type_key,
            "model_class": f"{model_class.__module__}.{model_class.__name__}",
            "pk": pk,
        }

    async def decode(self, data: dict[str, Any]) -> dict[str, Any]:
        """Decode lazy proxy reference.

        Returns the encoded data as-is since we want the ORM hook
        to handle the actual deserialization. We just need to change
        the type key so it's recognized by the appropriate ORM hook.
        """
        # Convert back to ORM reference format
        # Determine which ORM type based on the model class
        model_class_path = data["model_class"]

        # Check if it's a Tortoise model
        if self._is_tortoise_model(model_class_path):
            return {
                "__type__": "__tortoise_orm__",
                "model_class": model_class_path,
                "pk": data["pk"],
            }

        # Check if it's a Django model
        if self._is_django_model(model_class_path):
            return {
                "__type__": "__django_orm__",
                "model_class": model_class_path,
                "pk": data["pk"],
            }

        # Check if it's a SQLAlchemy model
        if self._is_sqlalchemy_model(model_class_path):
            return {
                "__type__": "__sqlalchemy_orm__",
                "model_class": model_class_path,
                "pk": data["pk"],
            }

        # Default: return as-is and let ORM hooks handle it
        return data

    def _is_tortoise_model(self, model_class_path: str) -> bool:
        """Check if model class is a Tortoise model."""
        try:
            parts = model_class_path.rsplit(".", 1)
            if len(parts) != 2:
                return False
            module_name, class_name = parts
            module = __import__(module_name, fromlist=[class_name])
            model_class = getattr(module, class_name)

            from tortoise.models import Model

            return issubclass(model_class, Model)
        except Exception:
            return False

    def _is_django_model(self, model_class_path: str) -> bool:
        """Check if model class is a Django model."""
        try:
            parts = model_class_path.rsplit(".", 1)
            if len(parts) != 2:
                return False
            module_name, class_name = parts
            module = __import__(module_name, fromlist=[class_name])
            model_class = getattr(module, class_name)

            from django.db.models import Model

            return issubclass(model_class, Model)
        except Exception:
            return False

    def _is_sqlalchemy_model(self, model_class_path: str) -> bool:
        """Check if model class is a SQLAlchemy model."""
        try:
            parts = model_class_path.rsplit(".", 1)
            if len(parts) != 2:
                return False
            module_name, class_name = parts
            module = __import__(module_name, fromlist=[class_name])
            model_class = getattr(module, class_name)

            from sqlalchemy.orm import DeclarativeBase

            return issubclass(model_class, DeclarativeBase)
        except Exception:
            return False
