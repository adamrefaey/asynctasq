from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from .hooks import HookRegistry, SerializationPipeline, TypeHook


class BaseSerializer(ABC):
    """Abstract base class for serializers with hook support.

    Provides:
    - Abstract serialize/deserialize methods
    - Hook registration infrastructure
    - Pipeline access for custom type handling
    """

    _registry: "HookRegistry"
    _pipeline: "SerializationPipeline"

    @abstractmethod
    def serialize(self, obj: dict[str, Any]) -> bytes:
        """Serialize task data dictionary to bytes."""
        ...

    @abstractmethod
    async def deserialize(self, data: bytes) -> dict[str, Any]:
        """Deserialize bytes to task data dictionary."""
        ...

    @property
    def registry(self) -> "HookRegistry":
        """Access the hook registry for registration/inspection."""
        return self._registry

    @property
    def pipeline(self) -> "SerializationPipeline":
        """Access the serialization pipeline."""
        return self._pipeline

    def register_hook(self, hook: "TypeHook[Any]") -> None:
        """Register a custom type hook.

        Args:
            hook: TypeHook instance to register

        Raises:
            ValueError: If hook with same type_key already exists
        """
        self._registry.register(hook)

    def unregister_hook(self, type_key: str) -> "TypeHook[Any] | None":
        """Unregister a hook by its type_key.

        Args:
            type_key: The type_key of the hook to remove

        Returns:
            The removed hook, or None if not found
        """
        return self._registry.unregister(type_key)
