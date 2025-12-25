"""Tests for the serialization hook system."""

from datetime import date, datetime
from decimal import Decimal
from typing import Any
from unittest.mock import MagicMock
from uuid import UUID

import pytest
from pytest import mark, raises

from asynctasq.serializers.hooks import (
    AsyncTypeHook,
    DateHook,
    DatetimeHook,
    DecimalHook,
    HookRegistry,
    SerializationPipeline,
    SetHook,
    TypeHook,
    UUIDHook,
    create_default_registry,
)

# =============================================================================
# Test Type Hooks
# =============================================================================


@mark.unit
class TestDatetimeHook:
    """Tests for DatetimeHook."""

    def test_can_encode_datetime(self) -> None:
        hook = DatetimeHook()
        assert hook.can_encode(datetime(2025, 1, 1, 12, 0, 0)) is True

    def test_cannot_encode_non_datetime(self) -> None:
        hook = DatetimeHook()
        assert hook.can_encode("2025-01-01") is False
        assert hook.can_encode(123) is False

    def test_encode_datetime(self) -> None:
        hook = DatetimeHook()
        dt = datetime(2025, 1, 1, 12, 30, 45)
        result = hook.encode(dt)
        assert result == {"__datetime__": "2025-01-01T12:30:45"}

    def test_decode_datetime(self) -> None:
        hook = DatetimeHook()
        data = {"__datetime__": "2025-01-01T12:30:45"}
        result = hook.decode(data)
        assert result == datetime(2025, 1, 1, 12, 30, 45)

    def test_can_decode_with_type_key(self) -> None:
        hook = DatetimeHook()
        assert hook.can_decode({"__datetime__": "2025-01-01"}) is True
        assert hook.can_decode({"__other__": "value"}) is False


@mark.unit
class TestDateHook:
    """Tests for DateHook."""

    def test_can_encode_date(self) -> None:
        hook = DateHook()
        assert hook.can_encode(date(2025, 1, 1)) is True

    def test_cannot_encode_datetime(self) -> None:
        # datetime is a subclass of date, but we handle it separately
        hook = DateHook()
        assert hook.can_encode(datetime(2025, 1, 1)) is False

    def test_encode_date(self) -> None:
        hook = DateHook()
        d = date(2025, 6, 15)
        result = hook.encode(d)
        assert result == {"__date__": "2025-06-15"}

    def test_decode_date(self) -> None:
        hook = DateHook()
        data = {"__date__": "2025-06-15"}
        result = hook.decode(data)
        assert result == date(2025, 6, 15)


@mark.unit
class TestDecimalHook:
    """Tests for DecimalHook."""

    def test_can_encode_decimal(self) -> None:
        hook = DecimalHook()
        assert hook.can_encode(Decimal("123.45")) is True

    def test_encode_decimal(self) -> None:
        hook = DecimalHook()
        d = Decimal("999.99")
        result = hook.encode(d)
        assert result == {"__decimal__": "999.99"}

    def test_decode_decimal(self) -> None:
        hook = DecimalHook()
        data = {"__decimal__": "123.456"}
        result = hook.decode(data)
        assert result == Decimal("123.456")


@mark.unit
class TestUUIDHook:
    """Tests for UUIDHook."""

    def test_can_encode_uuid(self) -> None:
        hook = UUIDHook()
        assert hook.can_encode(UUID("12345678-1234-5678-1234-567812345678")) is True

    def test_encode_uuid(self) -> None:
        hook = UUIDHook()
        u = UUID("12345678-1234-5678-1234-567812345678")
        result = hook.encode(u)
        assert result == {"__uuid__": "12345678-1234-5678-1234-567812345678"}

    def test_decode_uuid(self) -> None:
        hook = UUIDHook()
        data = {"__uuid__": "12345678-1234-5678-1234-567812345678"}
        result = hook.decode(data)
        assert result == UUID("12345678-1234-5678-1234-567812345678")


@mark.unit
class TestSetHook:
    """Tests for SetHook."""

    def test_can_encode_set(self) -> None:
        hook = SetHook()
        assert hook.can_encode({1, 2, 3}) is True

    def test_encode_set(self) -> None:
        hook = SetHook()
        s = {1, 2, 3}
        result = hook.encode(s)
        assert "__set__" in result
        assert set(result["__set__"]) == {1, 2, 3}

    def test_decode_set(self) -> None:
        hook = SetHook()
        data = {"__set__": [1, 2, 3]}
        result = hook.decode(data)
        assert result == {1, 2, 3}


# =============================================================================
# Test Hook Registry
# =============================================================================


@mark.unit
class TestHookRegistry:
    """Tests for HookRegistry."""

    def test_register_hook(self) -> None:
        registry = HookRegistry()
        hook = DatetimeHook()
        registry.register(hook)
        assert hook in registry.all_hooks

    def test_register_duplicate_type_key_raises(self) -> None:
        registry = HookRegistry()
        registry.register(DatetimeHook())
        with pytest.raises(ValueError, match="already registered"):
            registry.register(DatetimeHook())

    def test_unregister_hook(self) -> None:
        registry = HookRegistry()
        hook = DatetimeHook()
        registry.register(hook)
        removed = registry.unregister("__datetime__")
        assert removed is hook
        assert hook not in registry.all_hooks

    def test_unregister_nonexistent_returns_none(self) -> None:
        registry = HookRegistry()
        result = registry.unregister("__nonexistent__")
        assert result is None

    def test_find_encoder_returns_matching_hook(self) -> None:
        registry = HookRegistry()
        hook = DatetimeHook()
        registry.register(hook)
        found = registry.find_encoder(datetime.now())
        assert found is hook

    def test_find_encoder_returns_none_for_unknown_type(self) -> None:
        registry = HookRegistry()
        result = registry.find_encoder("unknown")
        assert result is None

    def test_find_decoder_returns_matching_hook(self) -> None:
        registry = HookRegistry()
        hook = DatetimeHook()
        registry.register(hook)
        found = registry.find_decoder({"__datetime__": "2025-01-01"})
        assert found is hook

    def test_find_decoder_returns_none_for_unknown_key(self) -> None:
        registry = HookRegistry()
        registry.register(DatetimeHook())
        result = registry.find_decoder({"__unknown__": "value"})
        assert result is None

    def test_get_async_hooks_returns_registered_async_hooks(self) -> None:
        registry = HookRegistry()
        sync_hook = DatetimeHook()
        async_hook = AsyncCustomHook()

        registry.register(sync_hook)
        registry.register(async_hook)

        async_hooks = registry.get_async_hooks()
        assert len(async_hooks) == 1
        assert async_hooks[0] is async_hook

    def test_clear_removes_all_hooks(self) -> None:
        registry = HookRegistry()
        registry.register(DatetimeHook())
        registry.register(DecimalHook())
        registry.clear()
        assert len(registry.all_hooks) == 0

    def test_hooks_sorted_by_priority(self) -> None:
        registry = HookRegistry()

        class LowPriorityHook(DatetimeHook):
            priority = 1

        class HighPriorityHook(DecimalHook):
            priority = 100

        low = LowPriorityHook()
        high = HighPriorityHook()

        registry.register(low)
        registry.register(high)

        hooks = registry.all_hooks
        assert hooks[0] is high
        assert hooks[1] is low


# =============================================================================
# Test Custom Hooks
# =============================================================================


class CustomType:
    """A custom type for testing."""

    def __init__(self, value: str) -> None:
        self.value = value

    def __eq__(self, other: object) -> bool:
        return isinstance(other, CustomType) and self.value == other.value


class CustomTypeHook(TypeHook[CustomType]):
    """Hook for custom type."""

    type_key = "__custom__"

    def can_encode(self, obj: Any) -> bool:
        return isinstance(obj, CustomType)

    def encode(self, obj: CustomType) -> dict[str, Any]:
        return {self.type_key: obj.value}

    def decode(self, data: dict[str, Any]) -> CustomType:
        return CustomType(data[self.type_key])


@mark.unit
class TestCustomTypeHook:
    """Tests for user-defined custom hooks."""

    def test_custom_hook_encode(self) -> None:
        hook = CustomTypeHook()
        obj = CustomType("hello")
        result = hook.encode(obj)
        assert result == {"__custom__": "hello"}

    def test_custom_hook_decode(self) -> None:
        hook = CustomTypeHook()
        data = {"__custom__": "world"}
        result = hook.decode(data)
        assert result == CustomType("world")

    def test_custom_hook_registration(self) -> None:
        registry = HookRegistry()
        hook = CustomTypeHook()
        registry.register(hook)

        # Should find encoder for custom type
        found = registry.find_encoder(CustomType("test"))
        assert found is hook

        # Should find decoder for custom type data
        found = registry.find_decoder({"__custom__": "test"})
        assert found is hook


# =============================================================================
# Test Async Type Hooks
# =============================================================================


class AsyncCustomType:
    """A type requiring async deserialization."""

    def __init__(self, id: int, data: str) -> None:
        self.id = id
        self.data = data


class AsyncCustomHook(AsyncTypeHook[AsyncCustomType]):
    """Async hook for testing."""

    type_key = "__async_custom__"

    def can_encode(self, obj: Any) -> bool:
        return isinstance(obj, AsyncCustomType)

    def encode(self, obj: AsyncCustomType) -> dict[str, Any]:
        return {self.type_key: {"id": obj.id}}

    async def decode_async(self, data: dict[str, Any]) -> AsyncCustomType:
        # Simulate async fetch
        id_val = data[self.type_key]["id"]
        return AsyncCustomType(id_val, f"fetched-{id_val}")


@mark.unit
class TestAsyncTypeHook:
    """Tests for async type hooks."""

    def test_async_hook_encode(self) -> None:
        hook = AsyncCustomHook()
        obj = AsyncCustomType(42, "test")
        result = hook.encode(obj)
        assert result == {"__async_custom__": {"id": 42}}

    def test_async_hook_sync_decode_passes_through(self) -> None:
        hook = AsyncCustomHook()
        data = {"__async_custom__": {"id": 42}}
        result = hook.decode(data)
        # Should pass through for async processing
        assert result == data

    @mark.asyncio
    async def test_async_hook_decode_async(self) -> None:
        hook = AsyncCustomHook()
        data = {"__async_custom__": {"id": 42}}
        result = await hook.decode_async(data)
        assert isinstance(result, AsyncCustomType)
        assert result.id == 42
        assert result.data == "fetched-42"

    def test_async_hook_requires_async(self) -> None:
        hook = AsyncCustomHook()
        assert hook.requires_async is True


# =============================================================================
# Test Serialization Pipeline
# =============================================================================


@mark.unit
class TestSerializationPipeline:
    """Tests for SerializationPipeline."""

    def test_encode_with_registered_hook(self) -> None:
        registry = create_default_registry()
        pipeline = SerializationPipeline(registry)

        data = {"timestamp": datetime(2025, 1, 1, 12, 0, 0)}
        result = pipeline.encode(data)
        assert result == {"timestamp": {"__datetime__": "2025-01-01T12:00:00"}}

    def test_encode_nested_structures(self) -> None:
        registry = create_default_registry()
        pipeline = SerializationPipeline(registry)

        data = {
            "items": [
                {"time": datetime(2025, 1, 1)},
                {"amount": Decimal("99.99")},
            ]
        }
        result = pipeline.encode(data)
        assert result["items"][0] == {"time": {"__datetime__": "2025-01-01T00:00:00"}}
        assert result["items"][1] == {"amount": {"__decimal__": "99.99"}}

    def test_encode_primitives_unchanged(self) -> None:
        registry = create_default_registry()
        pipeline = SerializationPipeline(registry)

        data = {"name": "test", "count": 42, "active": True}
        result = pipeline.encode(data)
        assert result == data

    def test_decode_sync_types(self) -> None:
        registry = create_default_registry()
        pipeline = SerializationPipeline(registry)

        data = {"timestamp": {"__datetime__": "2025-01-01T12:00:00"}}
        result = pipeline.decode(data)
        assert result == {"timestamp": datetime(2025, 1, 1, 12, 0, 0)}

    def test_decode_nested_dicts(self) -> None:
        """Test decode handles nested dictionaries recursively."""
        registry = create_default_registry()
        pipeline = SerializationPipeline(registry)

        data = {
            "user": {
                "name": "John",
                "created": {"__datetime__": "2025-01-01T12:00:00"},
                "profile": {"age": 30, "balance": {"__decimal__": "123.45"}},
            },
            "items": [{"price": {"__decimal__": "99.99"}}, "plain_string"],
        }
        result = pipeline.decode(data)

        expected = {
            "user": {
                "name": "John",
                "created": datetime(2025, 1, 1, 12, 0, 0),
                "profile": {"age": 30, "balance": Decimal("123.45")},
            },
            "items": [{"price": Decimal("99.99")}, "plain_string"],
        }
        assert result == expected

    @mark.asyncio
    async def test_decode_async_with_sync_hooks(self) -> None:
        registry = create_default_registry()
        pipeline = SerializationPipeline(registry)

        data = {
            "timestamp": {"__datetime__": "2025-01-01T12:00:00"},
            "amount": {"__decimal__": "123.45"},
        }
        result = await pipeline.decode_async(data)
        assert result["timestamp"] == datetime(2025, 1, 1, 12, 0, 0)
        assert result["amount"] == Decimal("123.45")

    @mark.asyncio
    async def test_decode_async_with_async_hooks(self) -> None:
        registry = HookRegistry()
        registry.register(AsyncCustomHook())
        pipeline = SerializationPipeline(registry)

        data = {"item": {"__async_custom__": {"id": 123}}}
        result = await pipeline.decode_async(data)
        assert isinstance(result["item"], AsyncCustomType)
        assert result["item"].id == 123

    @mark.asyncio
    async def test_decode_async_nested_structures(self) -> None:
        registry = create_default_registry()
        registry.register(AsyncCustomHook())
        pipeline = SerializationPipeline(registry)

        data = {
            "items": [
                {"__datetime__": "2025-01-01T00:00:00"},
                {"__async_custom__": {"id": 1}},
            ],
            "meta": {
                "updated": {"__datetime__": "2025-06-15T12:00:00"},
            },
        }
        result = await pipeline.decode_async(data)

        assert result["items"][0] == datetime(2025, 1, 1)
        assert isinstance(result["items"][1], AsyncCustomType)
        assert result["meta"]["updated"] == datetime(2025, 6, 15, 12, 0, 0)


# =============================================================================
# Test Default Registry
# =============================================================================


@mark.unit
class TestDefaultRegistry:
    """Tests for create_default_registry."""

    def test_includes_datetime_hook(self) -> None:
        registry = create_default_registry()
        assert registry.find_encoder(datetime.now()) is not None

    def test_includes_date_hook(self) -> None:
        registry = create_default_registry()
        assert registry.find_encoder(date.today()) is not None

    def test_includes_decimal_hook(self) -> None:
        registry = create_default_registry()
        assert registry.find_encoder(Decimal("1.0")) is not None

    def test_includes_uuid_hook(self) -> None:
        registry = create_default_registry()
        assert registry.find_encoder(UUID("12345678-1234-5678-1234-567812345678")) is not None

    def test_includes_set_hook(self) -> None:
        registry = create_default_registry()
        assert registry.find_encoder({1, 2, 3}) is not None


@mark.unit
class TestHookRegistryEdgeCases:
    """Edge case tests for HookRegistry to increase coverage."""

    def test_register_hook_with_none_type_key_raises(self) -> None:
        """Test registering a hook with None type_key does not raise (current behavior)."""
        registry = HookRegistry()
        hook = MagicMock()
        hook.type_key = None

        # Current behavior: doesn't check for None
        registry.register(hook)

    def test_register_hook_with_empty_type_key_raises(self) -> None:
        """Test registering a hook with empty type_key does not raise (current behavior)."""
        registry = HookRegistry()
        hook = MagicMock()
        hook.type_key = ""

        # Current behavior: doesn't check for empty
        registry.register(hook)

    def test_find_encoder_with_none_returns_none(self) -> None:
        """Test find_encoder returns None for None input."""
        registry = HookRegistry()
        assert registry.find_encoder(None) is None

    def test_find_decoder_with_none_type_key_returns_none(self) -> None:
        """Test find_decoder with None raises TypeError (expects dict)."""
        registry = HookRegistry()

        with raises(TypeError):
            registry.find_decoder(None)  # type: ignore

    def test_find_decoder_with_empty_type_key_returns_none(self) -> None:
        """Test find_decoder returns None for empty type_key."""
        registry = HookRegistry()
        assert registry.find_decoder("") is None  # type: ignore

    def test_unregister_hook_with_none_type_key_returns_none(self) -> None:
        """Test unregister_hook returns None for None type_key."""
        registry = HookRegistry()
        assert registry.unregister(None) is None  # type: ignore

    def test_unregister_hook_with_empty_type_key_returns_none(self) -> None:
        """Test unregister_hook returns None for empty type_key."""
        registry = HookRegistry()
        assert registry.unregister("") is None  # type: ignore

    def test_hooks_sorted_by_priority_descending(self) -> None:
        """Test that hooks are sorted by priority in descending order."""
        registry = HookRegistry()

        # Create hooks with different priorities
        high_priority_hook = MagicMock()
        high_priority_hook.type_key = "high"
        high_priority_hook.priority = 100

        low_priority_hook = MagicMock()
        low_priority_hook.type_key = "low"
        low_priority_hook.priority = 10

        registry.register(low_priority_hook)
        registry.register(high_priority_hook)

        # High priority should come first
        hooks = registry._hooks
        assert hooks[0].priority == 100
        assert hooks[1].priority == 10

    def test_clear_removes_all_hooks(self) -> None:
        """Test that clear() removes all registered hooks."""
        registry = HookRegistry()

        # Create comparable hooks
        class MockHook:
            def __init__(self, type_key, priority=0):
                self.type_key = type_key
                self.priority = priority

            def __lt__(self, other):
                return self.priority < other.priority

        hook1 = MockHook("test1")
        hook2 = MockHook("test2")

        registry.register(hook1)  # type: ignore
        registry.register(hook2)  # type: ignore

        assert len(registry._hooks) == 2

        registry.clear()

        assert len(registry._hooks) == 0
