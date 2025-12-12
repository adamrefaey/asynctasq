"""ORM model hooks for serialization/deserialization.

This module provides async hooks for ORM model serialization,
integrating with the hook system for SQLAlchemy, Django, and Tortoise ORM.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from .base import BaseOrmHook
from .django import DJANGO_AVAILABLE, DjangoOrmHook
from .sqlalchemy import (
    SQLALCHEMY_AVAILABLE,
    SqlalchemyOrmHook,
    check_pool_health,
    create_worker_session_factory,
    detect_forked_process,
    emit_fork_safety_warning,
    validate_session_factory,
)
from .tortoise import TORTOISE_AVAILABLE, TortoiseOrmHook

if TYPE_CHECKING:
    pass

__all__ = [
    "BaseOrmHook",
    "SqlalchemyOrmHook",
    "DjangoOrmHook",
    "TortoiseOrmHook",
    "register_orm_hooks",
    "SQLALCHEMY_AVAILABLE",
    "DJANGO_AVAILABLE",
    "TORTOISE_AVAILABLE",
    # SQLAlchemy utilities
    "create_worker_session_factory",
    "validate_session_factory",
    "detect_forked_process",
    "check_pool_health",
    "emit_fork_safety_warning",
]


# =============================================================================
# Registry Helper
# =============================================================================


def register_orm_hooks(registry: Any) -> None:
    """Register all available ORM hooks with a registry.

    Only registers hooks for ORMs that are actually installed.

    Args:
        registry: HookRegistry to register hooks with
    """
    if SQLALCHEMY_AVAILABLE:
        registry.register(SqlalchemyOrmHook())

    if DJANGO_AVAILABLE:
        registry.register(DjangoOrmHook())

    if TORTOISE_AVAILABLE:
        registry.register(TortoiseOrmHook())
