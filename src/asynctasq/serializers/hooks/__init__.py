"""Hook system for serialization/deserialization.

This package provides a pluggable hook architecture for custom type serialization:
- Base hook classes (TypeHook, AsyncTypeHook)
- Hook registry and serialization pipeline
- Built-in type hooks (datetime, date, Decimal, UUID, set)
- ORM model hooks (SQLAlchemy, Django, Tortoise)

Example:
    >>> from asynctasq.serializers.hooks import TypeHook, HookRegistry
    >>>
    >>> class MoneyHook(TypeHook[Money]):
    ...     type_key = "__money__"
    ...     def can_encode(self, obj): return isinstance(obj, Money)
    ...     def encode(self, obj): return {self.type_key: str(obj.amount)}
    ...     def decode(self, data): return Money(Decimal(data[self.type_key]))
    >>>
    >>> registry = HookRegistry()
    >>> registry.register(MoneyHook())
"""

from .base import (
    AsyncTypeHook,
    HookRegistry,
    SerializationPipeline,
    TypeHook,
    create_default_registry,
)
from .builtin import (
    DateHook,
    DatetimeHook,
    DecimalHook,
    SetHook,
    UUIDHook,
)
from .orm import (
    DJANGO_AVAILABLE,
    SQLALCHEMY_AVAILABLE,
    TORTOISE_AVAILABLE,
    BaseOrmHook,
    DjangoOrmHook,
    SqlalchemyOrmHook,
    TortoiseOrmHook,
    check_pool_health,
    create_worker_session_factory,
    detect_forked_process,
    emit_fork_safety_warning,
    register_orm_hooks,
    validate_session_factory,
)

__all__ = [
    # Base classes
    "TypeHook",
    "AsyncTypeHook",
    # Registry and Pipeline
    "HookRegistry",
    "SerializationPipeline",
    "create_default_registry",
    # Built-in type hooks
    "DatetimeHook",
    "DateHook",
    "DecimalHook",
    "UUIDHook",
    "SetHook",
    # ORM hooks
    "BaseOrmHook",
    "SqlalchemyOrmHook",
    "DjangoOrmHook",
    "TortoiseOrmHook",
    "register_orm_hooks",
    # ORM availability flags
    "SQLALCHEMY_AVAILABLE",
    "DJANGO_AVAILABLE",
    "TORTOISE_AVAILABLE",
    # ORM utilities
    "create_worker_session_factory",
    "validate_session_factory",
    "check_pool_health",
    "detect_forked_process",
    "emit_fork_safety_warning",
]
