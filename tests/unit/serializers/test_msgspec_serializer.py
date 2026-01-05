"""Comprehensive tests for MsgspecSerializer.

Tests all data types, custom type handling, ORM models, and edge cases.
"""

from datetime import UTC, date, datetime
from decimal import Decimal
from typing import Any
from uuid import UUID, uuid4

import pytest

from asynctasq.serializers.msgspec_serializer import MsgspecSerializer


class TestMsgspecSerializerBasicTypes:
    """Test serialization of basic Python types."""

    @pytest.fixture
    def serializer(self) -> MsgspecSerializer:
        return MsgspecSerializer()

    @pytest.mark.asyncio
    async def test_serialize_deserialize_string(self, serializer: MsgspecSerializer) -> None:
        """Test string serialization round-trip."""
        data = {"value": "hello world"}
        encoded = serializer.serialize(data)
        decoded = await serializer.deserialize(encoded)
        assert decoded == data

    @pytest.mark.asyncio
    async def test_serialize_deserialize_int(self, serializer: MsgspecSerializer) -> None:
        """Test integer serialization round-trip."""
        data = {"value": 42}
        encoded = serializer.serialize(data)
        decoded = await serializer.deserialize(encoded)
        assert decoded == data

    @pytest.mark.asyncio
    async def test_serialize_deserialize_float(self, serializer: MsgspecSerializer) -> None:
        """Test float serialization round-trip."""
        data = {"value": 3.14159}
        encoded = serializer.serialize(data)
        decoded = await serializer.deserialize(encoded)
        assert decoded["value"] == pytest.approx(data["value"])

    @pytest.mark.asyncio
    async def test_serialize_deserialize_bool(self, serializer: MsgspecSerializer) -> None:
        """Test boolean serialization round-trip."""
        for value in [True, False]:
            data = {"value": value}
            encoded = serializer.serialize(data)
            decoded = await serializer.deserialize(encoded)
            assert decoded == data

    @pytest.mark.asyncio
    async def test_serialize_deserialize_none(self, serializer: MsgspecSerializer) -> None:
        """Test None serialization round-trip."""
        data: dict[str, Any] = {"value": None}
        encoded = serializer.serialize(data)
        decoded = await serializer.deserialize(encoded)
        assert decoded["value"] is None

    @pytest.mark.asyncio
    async def test_serialize_deserialize_bytes(self, serializer: MsgspecSerializer) -> None:
        """Test bytes serialization round-trip."""
        data = {"value": b"binary data"}
        encoded = serializer.serialize(data)
        decoded = await serializer.deserialize(encoded)
        assert decoded == data


class TestMsgspecSerializerCollections:
    """Test serialization of collection types."""

    @pytest.fixture
    def serializer(self) -> MsgspecSerializer:
        return MsgspecSerializer()

    @pytest.mark.asyncio
    async def test_serialize_deserialize_list(self, serializer: MsgspecSerializer) -> None:
        """Test list serialization round-trip."""
        data: dict[str, Any] = {"value": [1, 2, 3, "four", 5.0]}
        encoded = serializer.serialize(data)
        decoded = await serializer.deserialize(encoded)
        assert decoded == data

    @pytest.mark.asyncio
    async def test_serialize_deserialize_dict(self, serializer: MsgspecSerializer) -> None:
        """Test dict serialization round-trip."""
        data: dict[str, Any] = {"value": {"a": 1, "b": "two", "c": 3.0}}
        encoded = serializer.serialize(data)
        decoded = await serializer.deserialize(encoded)
        assert decoded == data

    @pytest.mark.asyncio
    async def test_serialize_deserialize_nested_structures(
        self, serializer: MsgspecSerializer
    ) -> None:
        """Test nested dict/list serialization round-trip."""
        data: dict[str, Any] = {
            "users": [
                {"name": "Alice", "scores": [95, 87, 92]},
                {"name": "Bob", "scores": [88, 91, 85]},
            ],
            "metadata": {"version": 1, "tags": ["test", "example"]},
        }
        encoded = serializer.serialize(data)
        decoded = await serializer.deserialize(encoded)
        assert decoded == data

    @pytest.mark.asyncio
    async def test_serialize_deserialize_set(self, serializer: MsgspecSerializer) -> None:
        """Test set serialization round-trip (converted to list with marker)."""
        data: dict[str, Any] = {"params": {"tags": {1, 2, 3}}}
        encoded = serializer.serialize(data)
        decoded = await serializer.deserialize(encoded)
        # Sets should be restored from the special marker format
        assert decoded["params"]["tags"] == {1, 2, 3}

    @pytest.mark.asyncio
    async def test_serialize_deserialize_frozenset(self, serializer: MsgspecSerializer) -> None:
        """Test frozenset serialization round-trip (converted to list with marker)."""
        data: dict[str, Any] = {"params": {"immutable_tags": frozenset([4, 5, 6])}}
        encoded = serializer.serialize(data)
        decoded = await serializer.deserialize(encoded)
        # Frozensets should be restored from the special marker format
        assert decoded["params"]["immutable_tags"] == frozenset([4, 5, 6])

    @pytest.mark.asyncio
    async def test_serialize_deserialize_tuple(self, serializer: MsgspecSerializer) -> None:
        """Test tuple serialization (note: tuples become lists in msgpack)."""
        data: dict[str, Any] = {"value": (1, 2, 3)}
        encoded = serializer.serialize(data)
        decoded = await serializer.deserialize(encoded)
        # Tuples become lists in msgpack
        assert decoded["value"] == list(data["value"])

    @pytest.mark.asyncio
    async def test_serialize_deserialize_empty_collections(
        self, serializer: MsgspecSerializer
    ) -> None:
        """Test empty collection serialization."""
        data: dict[str, Any] = {
            "empty_list": [],
            "empty_dict": {},
        }
        encoded = serializer.serialize(data)
        decoded = await serializer.deserialize(encoded)
        assert decoded == data


class TestMsgspecSerializerDatetimeTypes:
    """Test serialization of datetime types."""

    @pytest.fixture
    def serializer(self) -> MsgspecSerializer:
        return MsgspecSerializer()

    @pytest.mark.asyncio
    async def test_serialize_deserialize_datetime_utc(self, serializer: MsgspecSerializer) -> None:
        """Test UTC datetime serialization round-trip."""
        data: dict[str, dict[str, datetime]] = {"params": {"timestamp": datetime.now(UTC)}}
        encoded = serializer.serialize(data)
        decoded = await serializer.deserialize(encoded)
        assert decoded["params"]["timestamp"] == data["params"]["timestamp"]

    @pytest.mark.asyncio
    async def test_serialize_deserialize_datetime_naive(
        self, serializer: MsgspecSerializer
    ) -> None:
        """Test naive datetime serialization round-trip."""
        ts = datetime(2024, 1, 15, 10, 30, 45, 123456)
        data: dict[str, dict[str, datetime]] = {"params": {"timestamp": ts}}
        encoded = serializer.serialize(data)
        decoded = await serializer.deserialize(encoded)
        assert decoded["params"]["timestamp"] == ts

    @pytest.mark.asyncio
    async def test_serialize_deserialize_date(self, serializer: MsgspecSerializer) -> None:
        """Test date serialization round-trip."""
        d = date(2024, 6, 15)
        data: dict[str, dict[str, date]] = {"params": {"date": d}}
        encoded = serializer.serialize(data)
        decoded = await serializer.deserialize(encoded)
        assert decoded["params"]["date"] == d


class TestMsgspecSerializerSpecialTypes:
    """Test serialization of special types like UUID and Decimal."""

    @pytest.fixture
    def serializer(self) -> MsgspecSerializer:
        return MsgspecSerializer()

    @pytest.mark.asyncio
    async def test_serialize_deserialize_uuid(self, serializer: MsgspecSerializer) -> None:
        """Test UUID serialization round-trip."""
        uid = uuid4()
        data: dict[str, dict[str, UUID]] = {"params": {"id": uid}}
        encoded = serializer.serialize(data)
        decoded = await serializer.deserialize(encoded)
        assert decoded["params"]["id"] == uid

    @pytest.mark.asyncio
    async def test_serialize_deserialize_decimal(self, serializer: MsgspecSerializer) -> None:
        """Test Decimal serialization round-trip."""
        d = Decimal("123.456789")
        data: dict[str, dict[str, Decimal]] = {"params": {"price": d}}
        encoded = serializer.serialize(data)
        decoded = await serializer.deserialize(encoded)
        assert decoded["params"]["price"] == d

    @pytest.mark.asyncio
    async def test_serialize_deserialize_decimal_large(self, serializer: MsgspecSerializer) -> None:
        """Test large Decimal serialization round-trip."""
        d = Decimal("999999999999999999.999999999999")
        data: dict[str, dict[str, Decimal]] = {"params": {"big_number": d}}
        encoded = serializer.serialize(data)
        decoded = await serializer.deserialize(encoded)
        assert decoded["params"]["big_number"] == d


class TestMsgspecSerializerComplexPayloads:
    """Test serialization of complex real-world payloads."""

    @pytest.fixture
    def serializer(self) -> MsgspecSerializer:
        return MsgspecSerializer()

    @pytest.mark.asyncio
    async def test_serialize_task_payload(self, serializer: MsgspecSerializer) -> None:
        """Test task-like payload serialization."""
        task_id = uuid4()
        created_at = datetime.now(UTC)

        payload: dict[str, Any] = {
            "task_id": str(task_id),
            "task_name": "process_order",
            "params": {
                "args": [1, 2, 3],
                "kwargs": {"user_id": 42, "amount": Decimal("99.99")},
                "metadata": {
                    "created_at": created_at,
                    "priority": 1,
                    "tags": {"urgent", "billing"},
                },
            },
        }

        encoded = serializer.serialize(payload)
        decoded = await serializer.deserialize(encoded)

        assert decoded["task_id"] == str(task_id)
        assert decoded["task_name"] == "process_order"
        assert decoded["params"]["args"] == [1, 2, 3]
        assert decoded["params"]["kwargs"]["user_id"] == 42
        assert decoded["params"]["kwargs"]["amount"] == Decimal("99.99")
        assert decoded["params"]["metadata"]["created_at"] == created_at
        assert decoded["params"]["metadata"]["tags"] == {"urgent", "billing"}

    @pytest.mark.asyncio
    async def test_serialize_deeply_nested_structure(self, serializer: MsgspecSerializer) -> None:
        """Test deeply nested structure serialization."""
        d = Decimal("1.23")
        ts = datetime.now(UTC)
        uid = uuid4()

        data: dict[str, Any] = {
            "params": {
                "level1": {
                    "level2": {
                        "level3": {
                            "level4": {
                                "value": d,
                                "timestamp": ts,
                                "id": uid,
                            }
                        }
                    }
                }
            }
        }

        encoded = serializer.serialize(data)
        decoded = await serializer.deserialize(encoded)

        level4 = decoded["params"]["level1"]["level2"]["level3"]["level4"]
        assert level4["value"] == d
        assert level4["timestamp"] == ts
        assert level4["id"] == uid

    @pytest.mark.asyncio
    async def test_serialize_large_list(self, serializer: MsgspecSerializer) -> None:
        """Test serialization of large lists."""
        base_ts = datetime.now(UTC)
        data: dict[str, list[dict[str, Any]]] = {
            "params": [{"id": i, "value": f"item_{i}", "timestamp": base_ts} for i in range(100)]
        }

        encoded = serializer.serialize(data)
        decoded = await serializer.deserialize(encoded)

        assert len(decoded["params"]) == 100
        for i, item in enumerate(decoded["params"]):
            assert item["id"] == i
            assert item["value"] == f"item_{i}"


class TestMsgspecSerializerAsyncDecode:
    """Test async decoding functionality."""

    @pytest.fixture
    def serializer(self) -> MsgspecSerializer:
        return MsgspecSerializer()

    @pytest.mark.asyncio
    async def test_decode_async_simple_types(self, serializer: MsgspecSerializer) -> None:
        """Test async decode with simple types (no ORM)."""
        data: dict[str, Any] = {
            "string": "hello",
            "int": 42,
            "list": [1, 2, 3],
            "nested": {"a": 1, "b": 2},
        }

        encoded = serializer.serialize(data)
        decoded = await serializer.deserialize(encoded)

        assert decoded == data

    @pytest.mark.asyncio
    async def test_decode_async_with_custom_types(self, serializer: MsgspecSerializer) -> None:
        """Test async decode with custom types."""
        task_id = uuid4()
        created_at = datetime.now(UTC)

        data: dict[str, Any] = {
            "params": {
                "id": task_id,
                "created_at": created_at,
                "amount": Decimal("99.99"),
                "tags": {"a", "b", "c"},
            }
        }

        encoded = serializer.serialize(data)
        decoded = await serializer.deserialize(encoded)

        assert decoded["params"]["id"] == task_id
        assert decoded["params"]["created_at"] == created_at
        assert decoded["params"]["amount"] == Decimal("99.99")
        assert decoded["params"]["tags"] == {"a", "b", "c"}


class TestMsgspecSerializerEdgeCases:
    """Test edge cases and error handling."""

    @pytest.fixture
    def serializer(self) -> MsgspecSerializer:
        return MsgspecSerializer()

    @pytest.mark.asyncio
    async def test_serialize_empty_dict(self, serializer: MsgspecSerializer) -> None:
        """Test empty dict serialization."""
        data: dict[str, Any] = {}
        encoded = serializer.serialize(data)
        decoded = await serializer.deserialize(encoded)
        assert decoded == {}

    @pytest.mark.asyncio
    async def test_serialize_unicode_strings(self, serializer: MsgspecSerializer) -> None:
        """Test Unicode string serialization."""
        data: dict[str, str] = {
            "emoji": "🚀🎉✨",
            "chinese": "你好世界",
            "arabic": "مرحبا بالعالم",
            "mixed": "Hello 世界 🌍",
        }
        encoded = serializer.serialize(data)
        decoded = await serializer.deserialize(encoded)
        assert decoded == data

    @pytest.mark.asyncio
    async def test_serialize_large_integers(self, serializer: MsgspecSerializer) -> None:
        """Test large integer serialization."""
        data: dict[str, int] = {
            "large_positive": 10**18,
            "large_negative": -(10**18),
        }
        encoded = serializer.serialize(data)
        decoded = await serializer.deserialize(encoded)
        assert decoded == data

    @pytest.mark.asyncio
    async def test_serialize_special_floats(self, serializer: MsgspecSerializer) -> None:
        """Test special float values."""
        data: dict[str, float] = {
            "zero": 0.0,
            "negative_zero": -0.0,
            "small": 1e-308,
            "large": 1e308,
        }
        encoded = serializer.serialize(data)
        decoded = await serializer.deserialize(encoded)
        assert decoded["zero"] == 0.0
        assert decoded["small"] == pytest.approx(1e-308)
        assert decoded["large"] == pytest.approx(1e308)

    def test_decode_invalid_data(self, serializer: MsgspecSerializer) -> None:
        """Test decoding invalid msgpack data raises exception."""
        import msgspec

        with pytest.raises(msgspec.DecodeError):
            # Just test the internal decoder directly
            serializer._decoder.decode(b"invalid msgpack data")

    @pytest.mark.asyncio
    async def test_serialize_mixed_type_list(self, serializer: MsgspecSerializer) -> None:
        """Test list with mixed types."""
        data: dict[str, list[Any]] = {
            "values": [
                1,
                "string",
                3.14,
                None,
                True,
                {"nested": "dict"},
                [1, 2, 3],
            ]
        }
        encoded = serializer.serialize(data)
        decoded = await serializer.deserialize(encoded)
        assert decoded == data


class TestMsgspecSerializerHookIntegration:
    """Test integration with hook system."""

    @pytest.fixture
    def serializer(self) -> MsgspecSerializer:
        return MsgspecSerializer()

    def test_serializer_has_hook_registry(self, serializer: MsgspecSerializer) -> None:
        """Test that serializer has a hook registry."""
        assert serializer.hook_registry is not None

    @pytest.mark.asyncio
    async def test_serializer_type_markers_preserved(self, serializer: MsgspecSerializer) -> None:
        """Test that type markers are preserved through serialization."""
        data: dict[str, Any] = {
            "params": {
                "uuid_field": uuid4(),
                "decimal_field": Decimal("123.45"),
                "datetime_field": datetime.now(UTC),
                "set_field": {1, 2, 3},
            }
        }

        encoded = serializer.serialize(data)
        decoded = await serializer.deserialize(encoded)

        # After full decoding, types should be restored
        assert isinstance(decoded["params"]["uuid_field"], UUID)
        assert isinstance(decoded["params"]["decimal_field"], Decimal)
        assert isinstance(decoded["params"]["datetime_field"], datetime)
        assert isinstance(decoded["params"]["set_field"], set)


class TestMsgspecSerializerPerformance:
    """Test performance characteristics (basic sanity checks)."""

    @pytest.fixture
    def serializer(self) -> MsgspecSerializer:
        return MsgspecSerializer()

    @pytest.mark.asyncio
    async def test_serialize_many_small_objects(self, serializer: MsgspecSerializer) -> None:
        """Test serializing many small objects is fast."""
        import time

        data: dict[str, Any] = {"id": 1, "name": "test", "value": 42.0}

        start = time.perf_counter()
        for _ in range(10000):
            encoded = serializer.serialize(data)
            _ = await serializer.deserialize(encoded)
        elapsed = time.perf_counter() - start

        # Should complete 10000 iterations in under 5 seconds
        # (this is a very conservative bound)
        assert elapsed < 5.0, f"10000 iterations took {elapsed:.2f}s"

    @pytest.mark.asyncio
    async def test_serialize_large_payload(self, serializer: MsgspecSerializer) -> None:
        """Test serializing large payload."""
        data: dict[str, list[dict[str, Any]]] = {
            "items": [{"id": i, "name": f"user_{i}", "data": "x" * 100} for i in range(1000)]
        }

        encoded = serializer.serialize(data)
        decoded = await serializer.deserialize(encoded)

        assert len(decoded["items"]) == 1000


class TestMsgspecSerializerRealWorldScenarios:
    """Test real-world task queue scenarios."""

    @pytest.fixture
    def serializer(self) -> MsgspecSerializer:
        return MsgspecSerializer()

    @pytest.mark.asyncio
    async def test_task_with_metadata(self, serializer: MsgspecSerializer) -> None:
        """Test typical task payload with metadata."""
        data: dict[str, Any] = {
            "task_id": uuid4(),
            "task_name": "send_email",
            "args": ["user@example.com", "Welcome!"],
            "kwargs": {"priority": "high", "retry_count": 0},
            "created_at": datetime.now(UTC),
            "scheduled_for": datetime.now(UTC),
            "metadata": {"user_id": uuid4(), "request_id": uuid4()},
        }
        decoded = await serializer.deserialize(serializer.serialize(data))
        assert decoded == data

    @pytest.mark.asyncio
    async def test_payment_task(self, serializer: MsgspecSerializer) -> None:
        """Test payment processing task with Decimal precision."""
        data: dict[str, Any] = {
            "task_id": uuid4(),
            "task_name": "process_payment",
            "amount": Decimal("199.99"),
            "currency": "USD",
            "user_id": uuid4(),
            "transaction_id": uuid4(),
            "timestamp": datetime.now(UTC),
            "metadata": {"card_last4": "4242", "network": "visa"},
        }
        deserialized = await serializer.deserialize(serializer.serialize(data))
        assert deserialized["amount"] == Decimal("199.99")
        assert isinstance(deserialized["amount"], Decimal)

    @pytest.mark.asyncio
    async def test_batch_processing_task(self, serializer: MsgspecSerializer) -> None:
        """Test batch processing with multiple items."""
        data: dict[str, Any] = {
            "task_id": uuid4(),
            "task_name": "batch_process",
            "batch_size": 100,
            "items": [
                {"id": uuid4(), "value": Decimal("10.00"), "date": date.today()} for _ in range(10)
            ],
            "created_at": datetime.now(UTC),
        }
        deserialized = await serializer.deserialize(serializer.serialize(data))
        assert len(deserialized["items"]) == 10
        assert all(isinstance(item["id"], UUID) for item in deserialized["items"])
        assert all(isinstance(item["value"], Decimal) for item in deserialized["items"])

    @pytest.mark.asyncio
    async def test_file_upload_task(self, serializer: MsgspecSerializer) -> None:
        """Test task with binary data (e.g., file upload)."""
        pdf_header_bytes = b"\x25\x50\x44\x46"
        data: dict[str, Any] = {
            "task_id": uuid4(),
            "task_name": "process_upload",
            "filename": "document.pdf",
            "content": pdf_header_bytes,
            "size": 1024,
            "uploaded_at": datetime.now(UTC),
            "user_id": uuid4(),
        }
        deserialized = await serializer.deserialize(serializer.serialize(data))
        assert deserialized["content"] == pdf_header_bytes

    @pytest.mark.asyncio
    async def test_scheduled_task_complex(self, serializer: MsgspecSerializer) -> None:
        """Test scheduled task with complex scheduling data."""
        data: dict[str, Any] = {
            "task_id": uuid4(),
            "task_name": "generate_report",
            "schedule": {
                "start_date": date(2023, 1, 1),
                "end_date": date(2023, 12, 31),
                "execution_times": [
                    datetime(2023, 1, 1, 9, 0, 0),
                    datetime(2023, 1, 2, 9, 0, 0),
                    datetime(2023, 1, 3, 9, 0, 0),
                ],
            },
            "parameters": {
                "format": "pdf",
                "recipients": {"admin@example.com", "manager@example.com"},
            },
        }
        deserialized = await serializer.deserialize(serializer.serialize(data))
        assert isinstance(deserialized["schedule"]["start_date"], date)
        assert isinstance(deserialized["parameters"]["recipients"], set)


class TestMsgspecConfiguration:
    """Test msgspec configuration follows best practices."""

    @pytest.fixture
    def serializer(self) -> MsgspecSerializer:
        return MsgspecSerializer()

    @pytest.mark.asyncio
    async def test_bin_type_handling(self, serializer: MsgspecSerializer) -> None:
        """Test that msgspec distinguishes str from bytes."""
        data: dict[str, Any] = {"binary": b"test", "text": "test"}
        deserialized = await serializer.deserialize(serializer.serialize(data))

        assert isinstance(deserialized["binary"], bytes)
        assert isinstance(deserialized["text"], str)
        assert deserialized["binary"] != deserialized["text"]

    @pytest.mark.asyncio
    async def test_utf8_string_handling(self, serializer: MsgspecSerializer) -> None:
        """Test UTF-8 encoding/decoding."""
        data: dict[str, str] = {"utf8": "Hello 世界 🌍"}
        deserialized = await serializer.deserialize(serializer.serialize(data))

        assert deserialized["utf8"] == data["utf8"]
        assert isinstance(deserialized["utf8"], str)

    def test_encoder_reuse(self, serializer: MsgspecSerializer) -> None:
        """Test that encoder is reused (best practice for performance)."""
        # Verify encoder instance is created once and reused
        encoder1 = serializer._encoder
        _ = serializer.serialize({"a": 1})
        encoder2 = serializer._encoder
        assert encoder1 is encoder2

    def test_decoder_reuse(self, serializer: MsgspecSerializer) -> None:
        """Test that decoder is reused (best practice for performance)."""
        # Verify decoder instance is created once and reused
        decoder1 = serializer._decoder
        decoder2 = serializer._decoder
        assert decoder1 is decoder2


class TestMsgspecSerializerConsistency:
    """Test consistency, idempotency, and round-trip correctness."""

    @pytest.fixture
    def serializer(self) -> MsgspecSerializer:
        return MsgspecSerializer()

    def test_serialize_is_deterministic(self, serializer: MsgspecSerializer) -> None:
        """Test that serializing the same data produces identical bytes."""
        data: dict[str, Any] = {"string": "test", "number": 42, "list": [1, 2, 3]}
        serialized1 = serializer.serialize(data)
        serialized2 = serializer.serialize(data)
        assert serialized1 == serialized2
        assert len(serialized1) > 0

    @pytest.mark.asyncio
    async def test_round_trip_preserves_data_and_types(self, serializer: MsgspecSerializer) -> None:
        """Test that round-trip preserves both data and types for all custom types."""
        original: dict[str, Any] = {
            "datetime": datetime(2023, 10, 15, 14, 30, 45),
            "date": date(2023, 10, 15),
            "decimal": Decimal("123.45"),
            "uuid": uuid4(),
            "bytes": b"test",
            "set": {1, 2, 3},
        }

        deserialized = await serializer.deserialize(serializer.serialize(original))

        # Data equality
        assert deserialized == original

        # Type preservation
        assert isinstance(deserialized["datetime"], datetime)
        assert isinstance(deserialized["date"], date)
        assert isinstance(deserialized["decimal"], Decimal)
        assert isinstance(deserialized["uuid"], UUID)
        assert isinstance(deserialized["bytes"], bytes)
        assert isinstance(deserialized["set"], set)

        # Multiple round trips (idempotency)
        result2 = await serializer.deserialize(serializer.serialize(deserialized))
        result3 = await serializer.deserialize(serializer.serialize(result2))
        assert deserialized == result2 == result3 == original

    @pytest.mark.asyncio
    async def test_object_identity_not_preserved(self, serializer: MsgspecSerializer) -> None:
        """Test that object identity is not preserved (expected serialization behavior)."""
        shared_uuid = uuid4()
        shared_date = datetime.now(UTC)
        data: dict[str, Any] = {
            "id1": shared_uuid,
            "id2": shared_uuid,
            "timestamp1": shared_date,
            "timestamp2": shared_date,
        }
        deserialized = await serializer.deserialize(serializer.serialize(data))
        # Values are equal but not identical (expected)
        assert deserialized["id1"] == deserialized["id2"]
        assert deserialized["timestamp1"] == deserialized["timestamp2"]
        assert deserialized["id1"] is not deserialized["id2"]


class TestMsgspecSerializerErrors:
    """Test error handling."""

    @pytest.fixture
    def serializer(self) -> MsgspecSerializer:
        return MsgspecSerializer()

    def test_unsupported_type_raises_error(self, serializer: MsgspecSerializer) -> None:
        """Test that unsupported types raise NotImplementedError."""

        class CustomClass:
            pass

        with pytest.raises(NotImplementedError, match="not serializable"):
            serializer.serialize({"custom": CustomClass()})

    def test_unsupported_type_nested(self, serializer: MsgspecSerializer) -> None:
        """Test unsupported type detection in nested structures."""

        class CustomClass:
            pass

        with pytest.raises(NotImplementedError):
            serializer.serialize({"items": [1, 2, CustomClass()]})

        with pytest.raises(NotImplementedError):
            serializer.serialize({"outer": {"inner": CustomClass()}})


class TestMsgspecSerializerOptimizations:
    """Test performance optimizations are working correctly."""

    @pytest.fixture
    def serializer(self) -> MsgspecSerializer:
        return MsgspecSerializer()

    def test_buffer_reuse(self, serializer: MsgspecSerializer) -> None:
        """Test that internal buffer is reused across serialize calls."""
        # Get buffer id before serialization
        buffer_id = id(serializer._buffer)

        # Serialize multiple times
        for i in range(10):
            serializer.serialize({"value": i})

        # Buffer should be the same object (reused)
        assert id(serializer._buffer) == buffer_id

    def test_buffer_grows_for_large_payloads(self, serializer: MsgspecSerializer) -> None:
        """Test that buffer grows for large payloads."""
        # Start with small buffer
        initial_capacity = len(serializer._buffer)

        # Serialize a large payload
        large_data = {"items": list(range(10000))}
        serializer.serialize(large_data)

        # Buffer should have grown
        assert len(serializer._buffer) > initial_capacity

    def test_async_markers_cached(self, serializer: MsgspecSerializer) -> None:
        """Test that async hook markers are pre-cached."""
        # Should have async markers from ORM hooks
        assert isinstance(serializer._async_markers, frozenset)

    def test_encoder_decoder_reuse(self, serializer: MsgspecSerializer) -> None:
        """Test that encoder and decoder instances are reused."""
        encoder_id = id(serializer._encoder)
        decoder_id = id(serializer._decoder)

        # Multiple operations
        for i in range(10):
            data = {"value": i}
            encoded = serializer.serialize(data)
            _ = serializer._decoder.decode(encoded)

        # Same instances should be used
        assert id(serializer._encoder) == encoder_id
        assert id(serializer._decoder) == decoder_id

    @pytest.mark.asyncio
    async def test_fast_path_skips_async_for_simple_data(
        self, serializer: MsgspecSerializer
    ) -> None:
        """Test that simple data without ORM doesn't trigger async overhead."""
        # Simple data with no ORM markers
        data: dict[str, Any] = {
            "params": {
                "string": "test",
                "number": 42,
                "list": [1, 2, 3],
                "nested": {"a": 1, "b": 2},
            }
        }

        encoded = serializer.serialize(data)

        # Should not need async processing
        assert not serializer._needs_async_processing(data["params"])

        # But should still deserialize correctly
        decoded = await serializer.deserialize(encoded)
        assert decoded == data

    def test_needs_async_returns_false_when_no_async_hooks(self) -> None:
        """Test _needs_async_processing returns False when no async markers."""
        from asynctasq.serializers.hooks import HookRegistry

        # Create serializer with empty registry (no async hooks)
        registry = HookRegistry()
        serializer = MsgspecSerializer(registry=registry)

        data = {"some": "data"}
        assert not serializer._needs_async_processing(data)


class TestMsgspecSerializerHookManagement:
    """Test hook registration and management."""

    @pytest.fixture
    def serializer(self) -> MsgspecSerializer:
        return MsgspecSerializer()

    def test_register_custom_hook(self, serializer: MsgspecSerializer) -> None:
        """Test registering a custom type hook."""
        from asynctasq.serializers.hooks import TypeHook

        class CustomType:
            def __init__(self, value: str):
                self.value = value

        class CustomHook(TypeHook[CustomType]):
            type_key = "__custom_test__"
            priority = 50

            def can_encode(self, obj: Any) -> bool:
                return isinstance(obj, CustomType)

            def encode(self, obj: CustomType) -> dict[str, Any]:
                return {self.type_key: obj.value}

            def decode(self, data: dict[str, Any]) -> CustomType:
                return CustomType(data[self.type_key])

        # Register hook
        serializer.register_hook(CustomHook())

        # Should be in registry
        assert "__custom_test__" in serializer.registry._decoder_cache

    def test_unregister_hook(self, serializer: MsgspecSerializer) -> None:
        """Test unregistering a hook."""
        from asynctasq.serializers.hooks import TypeHook

        class TempHook(TypeHook[str]):
            type_key = "__temp_hook__"
            priority = 10

            def can_encode(self, obj: Any) -> bool:
                return False

            def encode(self, obj: str) -> dict[str, Any]:
                return {self.type_key: obj}

            def decode(self, data: dict[str, Any]) -> str:
                return data[self.type_key]

        # Register then unregister
        serializer.register_hook(TempHook())
        assert "__temp_hook__" in serializer.registry._decoder_cache

        removed = serializer.unregister_hook("__temp_hook__")
        assert removed is not None
        assert "__temp_hook__" not in serializer.registry._decoder_cache

    def test_unregister_nonexistent_hook(self, serializer: MsgspecSerializer) -> None:
        """Test unregistering a hook that doesn't exist."""
        result = serializer.unregister_hook("__nonexistent__")
        assert result is None

    def test_async_markers_updated_on_register(self, serializer: MsgspecSerializer) -> None:
        """Test async markers are updated when hook is registered."""
        from asynctasq.serializers.hooks import AsyncTypeHook

        initial_markers = serializer._async_markers.copy()

        class AsyncTestHook(AsyncTypeHook[str]):
            type_key = "__async_test_hook__"
            priority = 10

            def can_encode(self, obj: Any) -> bool:
                return False

            def encode(self, obj: str) -> dict[str, Any]:
                return {self.type_key: obj}

            async def decode_async(self, data: dict[str, Any]) -> str:
                return data[self.type_key]

        serializer.register_hook(AsyncTestHook())

        # Async markers should now include the new hook
        assert "__async_test_hook__" in serializer._async_markers
        assert len(serializer._async_markers) > len(initial_markers)


class TestMsgspecSerializerPipeline:
    """Test serialization pipeline integration."""

    @pytest.fixture
    def serializer(self) -> MsgspecSerializer:
        return MsgspecSerializer()

    def test_pipeline_property(self, serializer: MsgspecSerializer) -> None:
        """Test that pipeline property returns a SerializationPipeline."""
        from asynctasq.serializers.hooks import SerializationPipeline

        pipeline = serializer.pipeline
        assert isinstance(pipeline, SerializationPipeline)

    def test_pipeline_uses_same_registry(self, serializer: MsgspecSerializer) -> None:
        """Test that pipeline uses the same registry as the serializer."""
        pipeline = serializer.pipeline
        assert pipeline.registry is serializer.registry


class TestMsgspecEncHookCoverage:
    """Test enc_hook function coverage for all type branches."""

    @pytest.fixture
    def serializer(self) -> MsgspecSerializer:
        return MsgspecSerializer()

    def test_enc_hook_datetime(self, serializer: MsgspecSerializer) -> None:
        """Test enc_hook handles datetime via _encode_types."""
        ts = datetime.now(UTC)
        data = {"timestamp": ts}
        encoded = serializer.serialize(data)
        # Should serialize without error
        assert isinstance(encoded, bytes)

    def test_enc_hook_uuid(self, serializer: MsgspecSerializer) -> None:
        """Test enc_hook handles UUID via _encode_types."""
        uid = uuid4()
        data = {"id": uid}
        encoded = serializer.serialize(data)
        assert isinstance(encoded, bytes)

    def test_enc_hook_decimal(self, serializer: MsgspecSerializer) -> None:
        """Test enc_hook handles Decimal via _encode_types."""
        d = Decimal("123.456")
        data = {"amount": d}
        encoded = serializer.serialize(data)
        assert isinstance(encoded, bytes)

    def test_enc_hook_date_only(self, serializer: MsgspecSerializer) -> None:
        """Test enc_hook handles date via _encode_types."""
        d = date(2024, 1, 15)
        data = {"day": d}
        encoded = serializer.serialize(data)
        assert isinstance(encoded, bytes)

    def test_enc_hook_set(self, serializer: MsgspecSerializer) -> None:
        """Test enc_hook handles set via _encode_types."""
        s = {1, 2, 3}
        data = {"tags": s}
        encoded = serializer.serialize(data)
        assert isinstance(encoded, bytes)

    def test_enc_hook_frozenset(self, serializer: MsgspecSerializer) -> None:
        """Test enc_hook handles frozenset via _encode_types."""
        fs = frozenset([4, 5, 6])
        data = {"immutable": fs}
        encoded = serializer.serialize(data)
        assert isinstance(encoded, bytes)


class TestMsgspecAsyncProcessingBranches:
    """Test _needs_async_impl and _decode_async_types branches."""

    @pytest.fixture
    def serializer(self) -> MsgspecSerializer:
        return MsgspecSerializer()

    def test_needs_async_with_nested_list(self, serializer: MsgspecSerializer) -> None:
        """Test _needs_async_impl with nested list structure."""
        # Create data with nested list containing dict - should recurse into list
        data = [[{"key": "value"}], {"other": 1}]
        # Should return False since no async markers present
        assert not serializer._needs_async_impl(data)

    def test_needs_async_with_nested_tuple(self, serializer: MsgspecSerializer) -> None:
        """Test _needs_async_impl with nested tuple structure."""
        data = ({"key": "value"}, ({"nested": "dict"},))
        assert not serializer._needs_async_impl(data)

    def test_needs_async_with_nested_dict_in_list(self, serializer: MsgspecSerializer) -> None:
        """Test _needs_async_impl with deeply nested dict in list."""
        data = [[[{"deep": {"nested": "value"}}]]]
        assert not serializer._needs_async_impl(data)

    def test_needs_async_with_dict_values_as_containers(
        self, serializer: MsgspecSerializer
    ) -> None:
        """Test _needs_async_impl checks dict values that are containers."""
        data = {"outer": {"inner": [{"deep": "value"}]}}
        assert not serializer._needs_async_impl(data)

    def test_needs_async_returns_false_for_primitive(self, serializer: MsgspecSerializer) -> None:
        """Test _needs_async_impl returns False for primitive values."""
        assert not serializer._needs_async_impl("string")
        assert not serializer._needs_async_impl(42)
        assert not serializer._needs_async_impl(3.14)
        assert not serializer._needs_async_impl(True)
        assert not serializer._needs_async_impl(None)

    @pytest.mark.asyncio
    async def test_decode_async_with_empty_dict(self, serializer: MsgspecSerializer) -> None:
        """Test _decode_async_types with empty dict."""
        result = await serializer._decode_async_types({})
        assert result == {}

    @pytest.mark.asyncio
    async def test_decode_async_with_empty_list(self, serializer: MsgspecSerializer) -> None:
        """Test _decode_async_types with empty list."""
        result = await serializer._decode_async_types([])
        assert result == []

    @pytest.mark.asyncio
    async def test_decode_async_with_empty_tuple(self, serializer: MsgspecSerializer) -> None:
        """Test _decode_async_types with empty tuple."""
        result = await serializer._decode_async_types(())
        assert result == ()

    @pytest.mark.asyncio
    async def test_decode_async_with_primitives(self, serializer: MsgspecSerializer) -> None:
        """Test _decode_async_types returns primitives unchanged."""
        assert await serializer._decode_async_types("string") == "string"
        assert await serializer._decode_async_types(42) == 42
        assert await serializer._decode_async_types(3.14) == 3.14
        assert await serializer._decode_async_types(True) is True
        assert await serializer._decode_async_types(None) is None
        assert await serializer._decode_async_types(b"bytes") == b"bytes"

    @pytest.mark.asyncio
    async def test_decode_async_with_nested_list(self, serializer: MsgspecSerializer) -> None:
        """Test _decode_async_types with nested list."""
        data: list[Any] = [1, [2, 3], {"nested": "dict"}]
        result = await serializer._decode_async_types(data)
        assert result == data

    @pytest.mark.asyncio
    async def test_decode_async_with_nested_tuple(self, serializer: MsgspecSerializer) -> None:
        """Test _decode_async_types with nested tuple."""
        data = (1, 2, (3, 4))
        result = await serializer._decode_async_types(data)
        assert result == data

    @pytest.mark.asyncio
    async def test_decode_async_with_nested_dict(self, serializer: MsgspecSerializer) -> None:
        """Test _decode_async_types with nested dict."""
        data = {"outer": {"middle": {"inner": "value"}}}
        result = await serializer._decode_async_types(data)
        assert result == data


class TestMsgspecSyncDecodeBranches:
    """Test deserialization branch coverage for sync types."""

    @pytest.fixture
    def serializer(self) -> MsgspecSerializer:
        return MsgspecSerializer()

    @pytest.mark.asyncio
    async def test_decode_sync_tuple_in_params(self, serializer: MsgspecSerializer) -> None:
        """Test deserialization handles tuple correctly."""
        # Tuples become lists in msgpack, but we want to ensure tuple branch is tested
        data: dict[str, Any] = {"values": (1, 2, 3)}
        encoded = serializer.serialize(data)
        decoded = await serializer.deserialize(encoded)
        # Tuples become lists after serialization
        assert decoded["values"] == [1, 2, 3]

    @pytest.mark.asyncio
    async def test_decode_sync_list_of_dicts(self, serializer: MsgspecSerializer) -> None:
        """Test deserialization handles list of dicts."""
        data: dict[str, Any] = {
            "items": [
                {"id": uuid4()},
                {"id": uuid4()},
            ]
        }
        encoded = serializer.serialize(data)
        decoded = await serializer.deserialize(encoded)
        assert all(isinstance(item["id"], UUID) for item in decoded["items"])

    @pytest.mark.asyncio
    async def test_decode_sync_nested_sets(self, serializer: MsgspecSerializer) -> None:
        """Test deserialization handles nested structures with sets."""
        data: dict[str, Any] = {
            "params": {
                "tags": {"a", "b"},
                "nested": {
                    "more_tags": {"c", "d"},
                },
            }
        }
        encoded = serializer.serialize(data)
        decoded = await serializer.deserialize(encoded)
        assert decoded["params"]["tags"] == {"a", "b"}
        assert decoded["params"]["nested"]["more_tags"] == {"c", "d"}

    @pytest.mark.asyncio
    async def test_decode_primitives_roundtrip(self, serializer: MsgspecSerializer) -> None:
        """Test primitives survive roundtrip correctly."""
        data = {"str": "string", "int": 42, "float": 3.14, "bool": True, "none": None}
        encoded = serializer.serialize(data)
        decoded = await serializer.deserialize(encoded)
        assert decoded["str"] == "string"
        assert decoded["int"] == 42
        assert decoded["float"] == 3.14
        assert decoded["bool"] is True
        assert decoded["none"] is None

    @pytest.mark.asyncio
    async def test_decode_list_with_primitives(self, serializer: MsgspecSerializer) -> None:
        """Test deserialization handles list with primitives."""
        data: dict[str, Any] = {"items": [1, "two", 3.0, None, True]}
        encoded = serializer.serialize(data)
        decoded = await serializer.deserialize(encoded)
        assert decoded["items"] == [1, "two", 3.0, None, True]


class TestMsgspecAsyncHookIntegration:
    """Test async hook integration for full branch coverage."""

    @pytest.fixture
    def serializer(self) -> MsgspecSerializer:
        return MsgspecSerializer()

    @pytest.mark.asyncio
    async def test_async_processing_with_registered_async_hook(
        self, serializer: MsgspecSerializer
    ) -> None:
        """Test that async hooks are properly invoked during deserialization."""
        from asynctasq.serializers.hooks import AsyncTypeHook

        class TestAsyncType:
            def __init__(self, value: str):
                self.value = value

        class TestAsyncHook(AsyncTypeHook[TestAsyncType]):
            type_key = "__test_async__"
            priority = 100

            def can_encode(self, obj: Any) -> bool:
                return isinstance(obj, TestAsyncType)

            def encode(self, obj: TestAsyncType) -> dict[str, Any]:
                return {self.type_key: obj.value}

            async def decode_async(self, data: dict[str, Any]) -> TestAsyncType:
                return TestAsyncType(data[self.type_key])

        # Register the async hook
        serializer.register_hook(TestAsyncHook())

        # Create serialized data with the marker directly
        encoded = serializer.serialize(
            {"params": {"custom": {TestAsyncHook.type_key: "test_value"}}}
        )

        # Deserialize should trigger async processing
        decoded = await serializer.deserialize(encoded)

        # The async hook should have been called
        assert isinstance(decoded["params"]["custom"], TestAsyncType)
        assert decoded["params"]["custom"].value == "test_value"

    @pytest.mark.asyncio
    async def test_needs_async_detects_async_markers(self, serializer: MsgspecSerializer) -> None:
        """Test _needs_async_processing detects async type markers."""
        from asynctasq.serializers.hooks import AsyncTypeHook

        class DummyAsyncHook(AsyncTypeHook[str]):
            type_key = "__async_dummy__"
            priority = 10

            def can_encode(self, obj: Any) -> bool:
                return False

            def encode(self, obj: str) -> dict[str, Any]:
                return {self.type_key: obj}

            async def decode_async(self, data: dict[str, Any]) -> str:
                return data[self.type_key]

        serializer.register_hook(DummyAsyncHook())

        # Data with the async marker should be detected
        data = {"__async_dummy__": "value"}
        assert serializer._needs_async_processing(data)

        # Nested data with async marker should also be detected
        nested_data = {"outer": {"__async_dummy__": "value"}}
        assert serializer._needs_async_processing(nested_data)

        # Data in list with async marker
        list_data = [{"__async_dummy__": "value"}]
        assert serializer._needs_async_processing(list_data)


class TestMsgspecSyncHookBranch:
    """Test sync hook decode branch in _decode_sync_types."""

    @pytest.fixture
    def serializer(self) -> MsgspecSerializer:
        return MsgspecSerializer()

    @pytest.mark.asyncio
    async def test_sync_hook_decoding(self, serializer: MsgspecSerializer) -> None:
        """Test that sync hooks are invoked in _decode_sync_types."""
        from asynctasq.serializers.hooks import TypeHook

        class CustomValue:
            def __init__(self, value: int):
                self.value = value

            def __eq__(self, other: Any) -> bool:
                return isinstance(other, CustomValue) and self.value == other.value

        class CustomSyncHook(TypeHook[CustomValue]):
            type_key = "__custom_sync__"
            priority = 100

            def can_encode(self, obj: Any) -> bool:
                return isinstance(obj, CustomValue)

            def encode(self, obj: CustomValue) -> dict[str, Any]:
                return {self.type_key: obj.value}

            def decode(self, data: dict[str, Any]) -> CustomValue:
                return CustomValue(data[self.type_key])

        serializer.register_hook(CustomSyncHook())

        # Serialize with the custom marker
        data: dict[str, Any] = {"params": {"custom": {"__custom_sync__": 42}}}
        encoded = serializer.serialize(data)
        decoded = await serializer.deserialize(encoded)

        # The sync hook should have decoded the custom type
        assert isinstance(decoded["params"]["custom"], CustomValue)
        assert decoded["params"]["custom"].value == 42


class TestMsgspecEncHookNotImplemented:
    """Test enc_hook raises NotImplementedError for unsupported types."""

    @pytest.fixture
    def serializer(self) -> MsgspecSerializer:
        return MsgspecSerializer()

    def test_enc_hook_raises_for_unsupported_type(self, serializer: MsgspecSerializer) -> None:
        """Test that enc_hook raises NotImplementedError for unknown types."""
        from asynctasq.serializers.msgspec_serializer import _create_enc_hook

        enc_hook = _create_enc_hook(serializer.registry)

        # A type that's not in the registry
        class UnsupportedType:
            pass

        with pytest.raises(NotImplementedError, match="Object of type .* is not serializable"):
            enc_hook(UnsupportedType())


class TestMsgspecExtHookUnknownCode:
    """Test ext_hook raises NotImplementedError for unknown extension codes."""

    @pytest.fixture
    def serializer(self) -> MsgspecSerializer:
        return MsgspecSerializer()

    def test_ext_hook_raises_for_unknown_code(self, serializer: MsgspecSerializer) -> None:
        """Test that ext_hook raises NotImplementedError for unknown ext codes."""
        from asynctasq.serializers.msgspec_serializer import _create_ext_hook

        ext_hook = _create_ext_hook(serializer.registry)

        # Use an unknown extension code (99)
        with pytest.raises(NotImplementedError, match="Extension type code 99 is not supported"):
            ext_hook(99, memoryview(b"test"))


class TestMsgspecListEncodingChanges:
    """Test list encoding with first-change detection."""

    @pytest.fixture
    def serializer(self) -> MsgspecSerializer:
        return MsgspecSerializer()

    @pytest.mark.asyncio
    async def test_list_with_first_item_changed(self, serializer: MsgspecSerializer) -> None:
        """Test list processing when first item needs encoding."""
        ts = datetime.now(UTC)
        data: dict[str, list[Any]] = {"items": [ts, "plain", 123]}
        encoded = serializer.serialize(data)
        decoded = await serializer.deserialize(encoded)
        assert decoded["items"][0] == ts
        assert decoded["items"][1] == "plain"
        assert decoded["items"][2] == 123

    @pytest.mark.asyncio
    async def test_list_with_middle_item_changed(self, serializer: MsgspecSerializer) -> None:
        """Test list processing when middle item needs encoding."""
        ts = datetime.now(UTC)
        data: dict[str, list[Any]] = {"items": ["first", ts, "last"]}
        encoded = serializer.serialize(data)
        decoded = await serializer.deserialize(encoded)
        assert decoded["items"][0] == "first"
        assert decoded["items"][1] == ts
        assert decoded["items"][2] == "last"

    @pytest.mark.asyncio
    async def test_list_with_multiple_items_changed(self, serializer: MsgspecSerializer) -> None:
        """Test list processing when multiple items need encoding."""
        ts1 = datetime(2025, 1, 1, 12, 0, 0)
        ts2 = datetime(2025, 6, 15, 18, 30, 0)
        data: dict[str, list[Any]] = {"items": [ts1, "middle", ts2]}
        encoded = serializer.serialize(data)
        decoded = await serializer.deserialize(encoded)
        assert decoded["items"][0] == ts1
        assert decoded["items"][1] == "middle"
        assert decoded["items"][2] == ts2

    @pytest.mark.asyncio
    async def test_list_unchanged_returns_original(self, serializer: MsgspecSerializer) -> None:
        """Test list returns original when no items need encoding."""
        data: dict[str, list[Any]] = {"items": ["a", "b", "c", 1, 2, 3]}
        encoded = serializer.serialize(data)
        decoded = await serializer.deserialize(encoded)
        assert decoded["items"] == ["a", "b", "c", 1, 2, 3]


class TestMsgspecAsyncTypeDetection:
    """Test async type detection paths."""

    @pytest.fixture
    def serializer(self) -> MsgspecSerializer:
        return MsgspecSerializer()

    def test_needs_async_with_nested_dict_in_list(self, serializer: MsgspecSerializer) -> None:
        """Test async detection with dict inside list."""
        from asynctasq.serializers.hooks import AsyncTypeHook

        class DummyAsyncHook(AsyncTypeHook[str]):
            type_key = "__async_test__"
            priority = 10

            def can_encode(self, obj: Any) -> bool:
                return False

            def encode(self, obj: str) -> dict[str, Any]:
                return {self.type_key: obj}

            async def decode_async(self, data: dict[str, Any]) -> str:
                return data[self.type_key]

        serializer.register_hook(DummyAsyncHook())

        # Dict with async marker inside list
        data = [{"__async_test__": "value"}]
        assert serializer._needs_async_processing(data)

    def test_needs_async_with_nested_list_in_list(self, serializer: MsgspecSerializer) -> None:
        """Test async detection with nested list containing dict."""
        from asynctasq.serializers.hooks import AsyncTypeHook

        class DummyAsyncHook(AsyncTypeHook[str]):
            type_key = "__async_nested__"
            priority = 10

            def can_encode(self, obj: Any) -> bool:
                return False

            def encode(self, obj: str) -> dict[str, Any]:
                return {self.type_key: obj}

            async def decode_async(self, data: dict[str, Any]) -> str:
                return data[self.type_key]

        serializer.register_hook(DummyAsyncHook())

        # Nested list with async marker
        data = [[{"__async_nested__": "value"}]]
        assert serializer._needs_async_processing(data)

    def test_needs_async_with_nested_tuple_in_dict_values(
        self, serializer: MsgspecSerializer
    ) -> None:
        """Test async detection with tuple in dict values."""
        from asynctasq.serializers.hooks import AsyncTypeHook

        class DummyAsyncHook(AsyncTypeHook[str]):
            type_key = "__async_tuple__"
            priority = 10

            def can_encode(self, obj: Any) -> bool:
                return False

            def encode(self, obj: str) -> dict[str, Any]:
                return {self.type_key: obj}

            async def decode_async(self, data: dict[str, Any]) -> str:
                return data[self.type_key]

        serializer.register_hook(DummyAsyncHook())

        # Tuple with async marker inside dict
        data = {"outer": ({"__async_tuple__": "value"},)}
        assert serializer._needs_async_processing(data)

    def test_needs_async_empty_markers_fast_path(self, serializer: MsgspecSerializer) -> None:
        """Test _needs_async_processing returns False when no async markers."""
        # Default serializer has ORM hooks registered
        # Create new one without async hooks
        from asynctasq.serializers.hooks import HookRegistry

        empty_registry = HookRegistry()
        new_serializer = MsgspecSerializer(empty_registry)

        data = {"key": {"nested": "value"}}
        assert new_serializer._needs_async_processing(data) is False


class TestMsgspecDecodeAsyncPaths:
    """Test async decode implementation paths."""

    @pytest.fixture
    def serializer(self) -> MsgspecSerializer:
        return MsgspecSerializer()

    @pytest.mark.asyncio
    async def test_decode_async_with_single_task(self, serializer: MsgspecSerializer) -> None:
        """Test decode_async with exactly one async task (avoids gather overhead)."""
        from asynctasq.serializers.hooks import AsyncTypeHook

        class SingleAsyncHook(AsyncTypeHook[str]):
            type_key = "__single_async__"
            priority = 100

            def can_encode(self, obj: Any) -> bool:
                return False

            def encode(self, obj: str) -> dict[str, Any]:
                return {self.type_key: obj}

            async def decode_async(self, data: dict[str, Any]) -> str:
                return f"decoded: {data[self.type_key]}"

        serializer.register_hook(SingleAsyncHook())

        # Must use 'params' key - deserialize only does async processing on params
        data: dict[str, Any] = {"params": {"item": {"__single_async__": "value"}}}
        encoded = serializer.serialize(data)
        decoded = await serializer.deserialize(encoded)

        assert decoded["params"]["item"] == "decoded: value"

    @pytest.mark.asyncio
    async def test_decode_async_with_multiple_tasks(self, serializer: MsgspecSerializer) -> None:
        """Test decode_async with multiple async tasks (uses gather)."""
        from asynctasq.serializers.hooks import AsyncTypeHook

        class MultiAsyncHook(AsyncTypeHook[str]):
            type_key = "__multi_async__"
            priority = 100

            def can_encode(self, obj: Any) -> bool:
                return False

            def encode(self, obj: str) -> dict[str, Any]:
                return {self.type_key: obj}

            async def decode_async(self, data: dict[str, Any]) -> str:
                return f"decoded: {data[self.type_key]}"

        serializer.register_hook(MultiAsyncHook())

        # Must use 'params' key - deserialize only does async processing on params
        data: dict[str, Any] = {
            "params": {
                "item1": {"__multi_async__": "first"},
                "item2": {"__multi_async__": "second"},
                "item3": {"__multi_async__": "third"},
            }
        }
        encoded = serializer.serialize(data)
        decoded = await serializer.deserialize(encoded)

        assert decoded["params"]["item1"] == "decoded: first"
        assert decoded["params"]["item2"] == "decoded: second"
        assert decoded["params"]["item3"] == "decoded: third"

    @pytest.mark.asyncio
    async def test_decode_async_tuple_handling(self, serializer: MsgspecSerializer) -> None:
        """Test decode_async handles tuples properly."""
        from asynctasq.serializers.hooks import AsyncTypeHook

        class TupleAsyncHook(AsyncTypeHook[str]):
            type_key = "__tuple_async__"
            priority = 100

            def can_encode(self, obj: Any) -> bool:
                return False

            def encode(self, obj: str) -> dict[str, Any]:
                return {self.type_key: obj}

            async def decode_async(self, data: dict[str, Any]) -> str:
                return f"decoded: {data[self.type_key]}"

        serializer.register_hook(TupleAsyncHook())

        # Must use 'params' key - deserialize only does async processing on params
        # Use list (tuples get converted to lists in msgpack)
        data: dict[str, Any] = {"params": {"items": [{"__tuple_async__": "value"}, "plain"]}}
        encoded = serializer.serialize(data)
        decoded = await serializer.deserialize(encoded)

        assert decoded["params"]["items"][0] == "decoded: value"
        assert decoded["params"]["items"][1] == "plain"


class TestMsgspecDecodeSyncTypesPaths:
    """Test _decode_sync_types edge cases."""

    @pytest.fixture
    def serializer(self) -> MsgspecSerializer:
        return MsgspecSerializer()

    @pytest.mark.asyncio
    async def test_decode_sync_types_tuple_handling(self, serializer: MsgspecSerializer) -> None:
        """Test _decode_sync_types handles tuples."""
        # Note: tuples become lists in msgpack, so we test tuple-like structures
        ts = datetime.now(UTC)
        data: dict[str, list[Any]] = {"items": [ts, "label"]}
        encoded = serializer.serialize(data)
        decoded = await serializer.deserialize(encoded)
        assert decoded["items"][0] == ts
        assert decoded["items"][1] == "label"

    @pytest.mark.asyncio
    async def test_decode_sync_types_dict_first_key_change(
        self, serializer: MsgspecSerializer
    ) -> None:
        """Test dict processing where first key value changes."""
        ts = datetime.now(UTC)
        data: dict[str, Any] = {"first": ts, "second": "unchanged", "third": 123}
        encoded = serializer.serialize(data)
        decoded = await serializer.deserialize(encoded)
        assert decoded["first"] == ts
        assert decoded["second"] == "unchanged"
        assert decoded["third"] == 123

    @pytest.mark.asyncio
    async def test_decode_sync_types_dict_middle_key_change(
        self, serializer: MsgspecSerializer
    ) -> None:
        """Test dict processing where middle key value changes."""
        ts = datetime.now(UTC)
        data: dict[str, Any] = {"first": "unchanged", "second": ts, "third": 123}
        encoded = serializer.serialize(data)
        decoded = await serializer.deserialize(encoded)
        assert decoded["first"] == "unchanged"
        assert decoded["second"] == ts
        assert decoded["third"] == 123
