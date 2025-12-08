"""Unit tests for BaseSerializer hook registration and pipeline access."""

from typing import Any
from unittest.mock import MagicMock

from pytest import mark

from asynctasq.serializers.base_serializer import BaseSerializer


@mark.unit
class TestBaseSerializerHookManagement:
    """Test BaseSerializer hook registration and unregistration."""

    def test_register_hook(self) -> None:
        """Test registering a hook through public API."""

        # Create a minimal serializer subclass for testing
        class TestSerializer(BaseSerializer):
            def __init__(self) -> None:
                self._registry: Any = MagicMock()
                self._pipeline: Any = MagicMock()

            def serialize(self, obj: dict[str, Any]) -> bytes:
                return b""

            async def deserialize(self, data: bytes) -> dict[str, Any]:
                return {}

        serializer = TestSerializer()
        hook = MagicMock()

        # Act
        serializer.register_hook(hook)

        # Assert
        assert serializer._registry.register.called

    def test_unregister_hook(self) -> None:
        """Test unregistering a hook by type_key."""

        class TestSerializer(BaseSerializer):
            def __init__(self) -> None:
                self._registry: Any = MagicMock()
                self._pipeline: Any = MagicMock()

            def serialize(self, obj: dict[str, Any]) -> bytes:
                return b""

            async def deserialize(self, data: bytes) -> dict[str, Any]:
                return {}

        serializer = TestSerializer()
        removed_hook = MagicMock()
        serializer._registry.unregister.return_value = removed_hook  # type: ignore[union-attr]

        # Act
        result = serializer.unregister_hook("test_type_key")

        # Assert
        assert serializer._registry.unregister.called  # type: ignore[union-attr]
        assert result is removed_hook

    def test_registry_property_access(self) -> None:
        """Test accessing registry through property."""

        class TestSerializer(BaseSerializer):
            def __init__(self) -> None:
                mock_registry = MagicMock()
                self._registry: Any = mock_registry
                self._pipeline: Any = MagicMock()

            def serialize(self, obj: dict[str, Any]) -> bytes:
                return b""

            async def deserialize(self, data: bytes) -> dict[str, Any]:
                return {}

        serializer = TestSerializer()

        # Act
        registry = serializer.registry

        # Assert
        assert registry is serializer._registry

    def test_pipeline_property_access(self) -> None:
        """Test accessing pipeline through property."""

        class TestSerializer(BaseSerializer):
            def __init__(self) -> None:
                self._registry: Any = MagicMock()
                mock_pipeline = MagicMock()
                self._pipeline: Any = mock_pipeline

            def serialize(self, obj: dict[str, Any]) -> bytes:
                return b""

            async def deserialize(self, data: bytes) -> dict[str, Any]:
                return {}

        serializer = TestSerializer()

        # Act
        pipeline = serializer.pipeline

        # Assert
        assert pipeline is serializer._pipeline

    def test_unregister_hook_not_found_returns_none(self) -> None:
        """Test unregistering a non-existent hook returns None."""

        class TestSerializer(BaseSerializer):
            def __init__(self) -> None:
                self._registry: Any = MagicMock()
                self._pipeline: Any = MagicMock()

            def serialize(self, obj: dict[str, Any]) -> bytes:
                return b""

            async def deserialize(self, data: bytes) -> dict[str, Any]:
                return {}

        serializer = TestSerializer()
        serializer._registry.unregister.return_value = None  # type: ignore[union-attr]

        # Act
        result = serializer.unregister_hook("nonexistent_key")

        # Assert
        assert result is None
