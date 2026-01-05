"""High-performance msgspec serializer.

This module provides a msgspec-based serializer optimized for maximum performance.

Key Optimizations (based on msgspec best practices):
1. Reusable Encoder/Decoder instances - avoids allocation overhead per call
2. encode_into with reusable buffer - minimizes memory allocations
3. MessagePack Extension Types - compact binary encoding with type codes
4. Single-walk encoding via enc_hook - no pre-processing overhead
5. ext_hook for binary-efficient decoding - direct type restoration
6. Pre-cached async markers - O(1) lookup for ORM type detection
7. Fast-path async detection - skip async overhead when no ORM models present
8. Parallel ORM fetches with asyncio.gather - concurrent database access

Type Round-trip Strategy:
We use MessagePack Extension Types (Ext) for built-in Python types. During
encoding, enc_hook converts datetime/UUID/Decimal/set/frozenset to Ext objects
with type codes. During decoding, ext_hook restores the original types directly
from the binary data. This eliminates dict marker overhead and enables single-walk
encoding.

Extension Type Codes (0-127 available):
- 1: datetime (ISO string bytes)
- 2: date (ISO string bytes)
- 3: UUID (16 bytes binary)
- 4: Decimal (string bytes)
- 5: set (nested msgpack array)
- 6: frozenset (nested msgpack array)
- 10+: Reserved for ORM hooks (use dict markers for routing)

Types handled:
- Primitives: int, float, str, bytes, bool, None (native msgpack)
- Collections: list, dict, tuple (native msgpack)
- datetime, date -> Ext type with ISO bytes
- UUID -> Ext type with 16-byte binary
- Decimal -> Ext type with string bytes
- set, frozenset -> Ext type with nested msgpack
- ORM models -> via hook system with dict markers (SQLAlchemy, Django, Tortoise)

References:
- https://jcristharif.com/msgspec/perf-tips.html
- https://jcristharif.com/msgspec/extending.html
"""

from __future__ import annotations

import asyncio
from datetime import date, datetime
from decimal import Decimal
from typing import TYPE_CHECKING, Any, Final, cast
from uuid import UUID

from msgspec import msgpack as msgspec_msgpack
from msgspec.msgpack import Ext

from .base_serializer import BaseSerializer
from .hooks import AsyncTypeHook, HookRegistry, create_default_registry, register_orm_hooks

if TYPE_CHECKING:
    from msgspec.msgpack import Decoder as MsgspecDecoder
    from msgspec.msgpack import Encoder as MsgspecEncoder

# MessagePack Extension Type Codes (0-127 available)
# Using extension types provides compact binary encoding and single-walk processing
_EXT_DATETIME: Final[int] = 1
_EXT_DATE: Final[int] = 2
_EXT_UUID: Final[int] = 3
_EXT_DECIMAL: Final[int] = 4
_EXT_SET: Final[int] = 5
_EXT_FROZENSET: Final[int] = 6

# Default buffer size for encode_into (64 bytes handles small messages without realloc)
_DEFAULT_BUFFER_SIZE: Final[int] = 64


# Type tuple for fast isinstance checks (single C-level check vs multiple)
_PRIMITIVES: Final[tuple[type, ...]] = (bool, int, float, str, bytes)


def _encode_types(obj: Any, enc_hook: Any) -> Any:
    """Pre-process data to convert special types to MessagePack Ext objects.

    msgspec handles datetime/UUID/Decimal/set/frozenset natively during encoding,
    converting them to strings/lists. On schemaless decode, this loses type info.
    This function converts them to Ext objects BEFORE msgspec encoding, ensuring
    they're preserved as extension types with binary-efficient encoding.

    Note: This pre-processing is necessary because msgspec's enc_hook is only
    called for types msgspec doesn't know how to handle natively. Since msgspec
    converts datetime/UUID/Decimal to strings automatically, enc_hook never sees them.

    Performance optimizations:
    - Fast path for None and primitives (most common case ~70%)
    - Type checks via tuple isinstance (single C-level check)
    - Containers only recreated when changes detected
    - Sentinel-based change detection avoids object comparisons

    Args:
        obj: The object to process
        enc_hook: The encoding hook for ORM models

    Returns:
        Processed object (original if no changes needed, new object otherwise)
    """
    # Fast path for None (very common)
    if obj is None:
        return obj

    # Fast path for primitives (most common case - ~70% of values)
    # Use tuple isinstance for single C-level type check
    if isinstance(obj, _PRIMITIVES):
        return obj

    # datetime -> Ext (check BEFORE date since datetime is a date subclass)
    if isinstance(obj, datetime):
        return Ext(_EXT_DATETIME, obj.isoformat().encode("utf-8"))

    # date -> Ext
    if isinstance(obj, date):
        return Ext(_EXT_DATE, obj.isoformat().encode("utf-8"))

    # UUID -> Ext (use 16-byte binary for compactness)
    if isinstance(obj, UUID):
        return Ext(_EXT_UUID, obj.bytes)

    # Decimal -> Ext
    if isinstance(obj, Decimal):
        return Ext(_EXT_DECIMAL, str(obj).encode("utf-8"))

    # set -> Ext with nested msgpack array
    if isinstance(obj, set):
        processed = [_encode_types(item, enc_hook) for item in obj]
        nested_data = msgspec_msgpack.encode(processed, enc_hook=enc_hook)
        return Ext(_EXT_SET, nested_data)

    # frozenset -> Ext with nested msgpack array
    if isinstance(obj, frozenset):
        processed = [_encode_types(item, enc_hook) for item in obj]
        nested_data = msgspec_msgpack.encode(processed, enc_hook=enc_hook)
        return Ext(_EXT_FROZENSET, nested_data)

    # dict -> recursively process values, only create new dict if changes
    if isinstance(obj, dict):
        new_dict: dict[Any, Any] | None = None
        for key, value in obj.items():
            new_value = _encode_types(value, enc_hook)
            if new_value is not value:
                if new_dict is None:
                    # First change detected - copy all prior items
                    new_dict = {}
                    for k, v in obj.items():
                        if k == key:
                            break
                        new_dict[k] = v
                new_dict[key] = new_value
            elif new_dict is not None:
                new_dict[key] = new_value
        return new_dict if new_dict is not None else obj

    # list -> recursively process items, only create new list if changes
    if isinstance(obj, list):
        new_list: list[Any] | None = None
        for i, item in enumerate(obj):
            new_item = _encode_types(item, enc_hook)
            if new_item is not item:
                if new_list is None:
                    # First change detected - copy all prior items
                    new_list = obj[:i]
                new_list.append(new_item)
            elif new_list is not None:
                new_list.append(new_item)
        return new_list if new_list is not None else obj

    # tuple -> convert to list for msgpack, process items
    if isinstance(obj, tuple):
        return [_encode_types(item, enc_hook) for item in obj]

    # Unknown type - return as-is, let enc_hook handle ORM models
    return obj


# Type tuple for ext_hook decoded types (avoid re-decoding)
_EXT_DECODED_TYPES: Final[tuple[type, ...]] = (datetime, date, UUID, Decimal, set, frozenset)


def _create_enc_hook(registry: HookRegistry) -> Any:
    """Create an encoding hook for ORM models and custom types.

    Note: datetime/UUID/Decimal/set/frozenset are pre-processed to Ext objects
    in _encode_types() before reaching msgspec, so they won't hit this hook.
    This hook handles ORM models and any types that somehow reach msgspec's
    encoder without being pre-processed.
    """
    find_encoder = registry.find_encoder

    def enc_hook(obj: Any) -> Any:
        # Try registry hooks for ORM models and custom types
        hook = find_encoder(obj)
        if hook is not None:
            return hook.encode(obj)

        raise NotImplementedError(f"Object of type {type(obj)} is not serializable")

    return enc_hook


def _create_ext_hook(registry: HookRegistry) -> Any:
    """Create an extension hook for decoding Ext types back to Python objects.

    This hook is called by msgspec for MessagePack extension types.
    It restores datetime/UUID/Decimal/set/frozenset from binary Ext data.
    """

    def ext_hook(code: int, data: memoryview) -> Any:
        if code == _EXT_DATETIME:
            return datetime.fromisoformat(bytes(data).decode("utf-8"))

        if code == _EXT_DATE:
            return date.fromisoformat(bytes(data).decode("utf-8"))

        if code == _EXT_UUID:
            return UUID(bytes=bytes(data))

        if code == _EXT_DECIMAL:
            return Decimal(bytes(data).decode("utf-8"))

        if code == _EXT_SET:
            # Decode nested msgpack array, recursively handling Ext types
            items = msgspec_msgpack.decode(bytes(data), ext_hook=ext_hook)
            return set(items)

        if code == _EXT_FROZENSET:
            items = msgspec_msgpack.decode(bytes(data), ext_hook=ext_hook)
            return frozenset(items)

        raise NotImplementedError(f"Extension type code {code} is not supported")

    return ext_hook


class MsgspecSerializer(BaseSerializer):
    """High-performance msgspec-based serializer.

    This serializer uses msgspec's MessagePack encoding with Extension Types
    for round-trip fidelity in schemaless serialization scenarios.

    Performance optimizations:
    - Reusable Encoder/Decoder instances (avoids allocation overhead)
    - encode_into with reusable buffer (minimizes memory allocations)
    - MessagePack Extension Types (compact binary encoding, single-walk)
    - ext_hook for binary-efficient decoding (direct type restoration)
    - Pre-cached async markers (O(1) lookup for ORM detection)
    - Fast-path async detection (skip overhead when no ORM models)
    - Parallel ORM fetches with asyncio.gather

    Supported types:
    - All Python primitives (int, float, str, bytes, bool, None)
    - Collections (list, dict, tuple, set, frozenset)
    - datetime.datetime, datetime.date
    - uuid.UUID
    - decimal.Decimal
    - ORM models (SQLAlchemy, Django, Tortoise) via lazy loading

    Example:
        >>> from asynctasq.serializers import MsgspecSerializer
        >>> from datetime import datetime
        >>> from decimal import Decimal
        >>> from uuid import uuid4
        >>>
        >>> serializer = MsgspecSerializer()
        >>> data = {
        ...     "params": {
        ...         "timestamp": datetime.now(),
        ...         "id": uuid4(),
        ...         "amount": Decimal("99.99"),
        ...         "tags": {"a", "b", "c"}
        ...     }
        ... }
        >>> encoded = serializer.serialize(data)
        >>> decoded = await serializer.deserialize(encoded)
    """

    __slots__ = (
        "_registry",
        "_encoder",
        "_decoder",
        "_enc_hook",
        "_ext_hook",
        "_buffer",
        "_async_markers",
    )

    _encoder: MsgspecEncoder
    _decoder: MsgspecDecoder
    _enc_hook: Any
    _ext_hook: Any
    _buffer: bytearray
    _async_markers: frozenset[str]

    def __init__(self, registry: HookRegistry | None = None) -> None:
        """Initialize serializer with optional custom registry.

        Args:
            registry: Custom hook registry. If None, uses default with all built-in hooks
                      including ORM support.
        """
        self._registry = registry or self._create_full_registry()

        # Create enc_hook for ORM models (datetime/UUID/Decimal/set/frozenset handled by pre-processing)
        self._enc_hook = _create_enc_hook(self._registry)

        # Create encoder with enc_hook for ORM models
        self._encoder = msgspec_msgpack.Encoder(enc_hook=self._enc_hook)

        # Create ext_hook for decoding Extension Types back to Python objects
        self._ext_hook = _create_ext_hook(self._registry)

        # Create decoder with ext_hook for binary-efficient type restoration
        self._decoder = msgspec_msgpack.Decoder(ext_hook=self._ext_hook)

        # Reusable buffer for encode_into (reduces memory allocations)
        self._buffer = bytearray(_DEFAULT_BUFFER_SIZE)

        # Pre-cache async type markers from registry for fast O(1) lookups
        self._async_markers = frozenset(hook.type_key for hook in self._registry.get_async_hooks())

    def _create_full_registry(self) -> HookRegistry:
        """Create a registry with all built-in hooks including ORM support."""
        registry = create_default_registry()
        register_orm_hooks(registry)
        return registry

    @property
    def registry(self) -> HookRegistry:
        """Get the hook registry for custom type registration."""
        return self._registry

    @property
    def pipeline(self) -> Any:
        """Get the serialization pipeline (for API compatibility with BaseSerializer)."""
        from .hooks import SerializationPipeline

        return SerializationPipeline(self._registry)

    @property
    def hook_registry(self) -> HookRegistry:
        """Alias for registry property for API consistency."""
        return self._registry

    def register_hook(self, hook: Any) -> None:
        """Register a custom type hook.

        After registration, recreates encoder/decoder with updated hooks and updates async markers.

        Args:
            hook: TypeHook instance to register
        """
        self._registry.register(hook)
        # Recreate enc_hook and encoder with updated registry
        self._enc_hook = _create_enc_hook(self._registry)
        self._encoder = msgspec_msgpack.Encoder(enc_hook=self._enc_hook)
        # Recreate ext_hook and decoder (ext_hook closure captures registry state)
        self._ext_hook = _create_ext_hook(self._registry)
        self._decoder = msgspec_msgpack.Decoder(ext_hook=self._ext_hook)
        # Update async markers cache
        self._async_markers = frozenset(h.type_key for h in self._registry.get_async_hooks())

    def unregister_hook(self, type_key: str) -> Any:
        """Unregister a hook by its type_key.

        After unregistration, recreates encoder/decoder with updated hooks and updates async markers.

        Args:
            type_key: The type_key of the hook to remove

        Returns:
            The removed hook, or None if not found
        """
        result = self._registry.unregister(type_key)
        # Recreate enc_hook and encoder with updated registry
        self._enc_hook = _create_enc_hook(self._registry)
        self._encoder = msgspec_msgpack.Encoder(enc_hook=self._enc_hook)
        # Recreate ext_hook and decoder
        self._ext_hook = _create_ext_hook(self._registry)
        self._decoder = msgspec_msgpack.Decoder(ext_hook=self._ext_hook)
        # Update async markers cache
        self._async_markers = frozenset(h.type_key for h in self._registry.get_async_hooks())
        return result

    def serialize(self, obj: dict[str, Any]) -> bytes:
        """Serialize task data dict to msgpack bytes.

        Pre-processes data to convert datetime/UUID/Decimal/set/frozenset to
        MessagePack Extension Types. This is necessary because msgspec handles
        these types natively (converting to strings/lists) but loses type info
        on schemaless decode. Using Ext objects preserves type information with
        compact binary encoding.

        Note: Pre-processing is required because msgspec's enc_hook is only called
        for types msgspec doesn't know how to handle - it converts datetime/UUID/Decimal
        to strings before enc_hook can intercept them.

        Performance optimizations:
        - _encode_types creates new containers only when needed
        - encode_into with reusable buffer minimizes allocations

        Args:
            obj: Task data dictionary to serialize

        Returns:
            Msgpack-encoded bytes
        """
        # Pre-process to convert special types to Ext objects
        processed = _encode_types(obj, self._enc_hook)
        # encode_into with reusable buffer
        self._encoder.encode_into(processed, self._buffer)
        return bytes(self._buffer)

    async def deserialize(self, data: bytes) -> dict[str, Any]:
        """Deserialize msgpack bytes back to task data dict.

        Two-phase deserialization:
        1. Decode msgpack with ext_hook -> Python objects with types restored
           (datetime/UUID/Decimal/set/frozenset handled by ext_hook)
        2. Process ORM dict markers via registry hooks (_decode_sync_types)
        3. Optional async processing for ORM models

        Args:
            data: Msgpack-encoded bytes

        Returns:
            Task data dictionary with all types restored
        """
        # Decode msgpack - ext_hook restores datetime/UUID/Decimal/set/frozenset
        result = cast(dict[str, Any], self._decoder.decode(data))

        # Process ORM dict markers via registry hooks
        result = self._decode_sync_types(result)

        # Only do async processing if ORM models might be present
        if "params" in result and self._needs_async_processing(result["params"]):
            result["params"] = await self._decode_async_types(result["params"])

        return result

    def _decode_sync_types(self, obj: Any) -> Any:
        """Process registry hooks for custom types (ORM models).

        Note: datetime/date/UUID/Decimal/set/frozenset are already restored
        by ext_hook during msgpack decoding. This method only handles
        registry-based hooks (ORM models use dict markers).

        Performance optimizations:
        - Tuple isinstance for primitives (single C-level check)
        - Tuple isinstance for ext_hook decoded types
        - Only create new containers when values change
        """
        # Fast path for None (very common in task params)
        if obj is None:
            return obj

        # Fast path for primitives (tuple isinstance = single C check)
        if isinstance(obj, _PRIMITIVES):
            return obj

        # Fast path for types already restored by ext_hook
        if isinstance(obj, _EXT_DECODED_TYPES):
            return obj

        if isinstance(obj, dict):
            # Check registry for custom sync hooks (ORM models use dict markers)
            hook = self._registry.find_decoder(obj)
            if hook is not None and not isinstance(hook, AsyncTypeHook):
                return hook.decode(obj)

            # Recursively process dict values, only create new if changes
            new_dict: dict[Any, Any] | None = None
            for key, value in obj.items():
                new_value = self._decode_sync_types(value)
                if new_value is not value:
                    if new_dict is None:
                        new_dict = {}
                        for k, v in obj.items():
                            if k == key:
                                break
                            new_dict[k] = v
                    new_dict[key] = new_value
                elif new_dict is not None:
                    new_dict[key] = new_value
            return new_dict if new_dict is not None else obj

        # Handle lists - only create new if changes
        if isinstance(obj, list):
            new_list: list[Any] | None = None
            for i, item in enumerate(obj):
                new_item = self._decode_sync_types(item)
                if new_item is not item:
                    if new_list is None:
                        new_list = obj[:i]
                    new_list.append(new_item)
                elif new_list is not None:
                    new_list.append(new_item)
            return new_list if new_list is not None else obj

        # Handle tuples (returned as tuples)
        if isinstance(obj, tuple):
            return tuple(self._decode_sync_types(item) for item in obj)

        return obj

    def _needs_async_processing(self, obj: Any) -> bool:
        """Check if object contains types requiring async processing.

        Optimized with pre-cached async markers for O(1) lookup.
        Early return when no async hooks registered.
        """
        if not self._async_markers:
            return False
        return self._needs_async_impl(obj)

    def _needs_async_impl(self, obj: Any) -> bool:
        """Internal implementation of async detection.

        Uses frozenset.isdisjoint for faster check than intersection.
        """
        if isinstance(obj, dict):
            # Fast O(1) check: isdisjoint is faster than intersection for detection
            if not self._async_markers.isdisjoint(obj.keys()):
                return True
            # Recursively check nested structures - only containers can have ORM refs
            for value in obj.values():
                if isinstance(value, dict):
                    if self._needs_async_impl(value):
                        return True
                elif isinstance(value, (list, tuple)):
                    if self._needs_async_impl(value):
                        return True
            return False

        if isinstance(obj, (list, tuple)):
            for item in obj:
                if isinstance(item, dict):
                    if self._needs_async_impl(item):
                        return True
                elif isinstance(item, (list, tuple)):
                    if self._needs_async_impl(item):
                        return True
            return False

        return False

    async def _decode_async_types(self, obj: Any) -> Any:
        """Decode types requiring async processing (ORM models).

        Performance optimizations:
        - Collects ALL async tasks first, then runs single batched gather
        - Avoids gather overhead for single items
        - Fast-path returns for primitives and already-decoded types
        - Uses in-place mutation where possible to avoid allocations
        - Tuple isinstance checks for single C-level type checks
        """
        # Collect all async tasks - simple list of awaitables
        tasks: list[Any] = []

        def collect_tasks(value: Any) -> Any:
            """Recursively collect async tasks and return modified structure."""
            # Fast path for None
            if value is None:
                return value

            # Fast path for primitives (tuple isinstance = single C check)
            if isinstance(value, _PRIMITIVES):
                return value

            # Fast path for types already restored by ext_hook
            if isinstance(value, _EXT_DECODED_TYPES):
                return value

            if isinstance(value, dict):
                # Check for async hook (ORM models)
                hook = self._registry.find_decoder(value)
                if hook is not None and isinstance(hook, AsyncTypeHook):
                    # Create placeholder and record task
                    placeholder = {"__pending__": len(tasks)}
                    tasks.append(hook.decode_async(value))
                    return placeholder

                # Process dict values recursively (in-place mutation)
                for k, v in list(value.items()):
                    new_v = collect_tasks(v)
                    if new_v is not v:
                        value[k] = new_v
                return value

            if isinstance(value, list):
                # Process list items (in-place mutation)
                for i, item in enumerate(value):
                    new_item = collect_tasks(item)
                    if new_item is not item:
                        value[i] = new_item
                return value

            if isinstance(value, tuple):
                # Convert to list, process, convert back
                return tuple(collect_tasks(item) for item in value)

            return value

        # First pass: collect all async tasks
        result = collect_tasks(obj)

        # If no async tasks, return immediately
        if not tasks:
            return result

        # Execute all async tasks
        if len(tasks) == 1:
            # Avoid gather overhead for single task
            resolved_values = [await tasks[0]]
        else:
            # Parallel execution for multiple tasks
            resolved_values = list(await asyncio.gather(*tasks))

        # Second pass: replace placeholders with resolved values
        def replace_placeholders(value: Any) -> Any:
            """Replace placeholder dicts with resolved values."""
            if isinstance(value, dict):
                pending = value.get("__pending__")
                if pending is not None:
                    return resolved_values[pending]
                # Process dict values (in-place mutation)
                for k, v in list(value.items()):
                    new_v = replace_placeholders(v)
                    if new_v is not v:
                        value[k] = new_v
                return value

            if isinstance(value, list):
                for i, item in enumerate(value):
                    new_item = replace_placeholders(item)
                    if new_item is not item:
                        value[i] = new_item
                return value

            if isinstance(value, tuple):
                return tuple(replace_placeholders(item) for item in value)

            return value

        return replace_placeholders(result)
