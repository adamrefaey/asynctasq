import asyncio
import struct
from dataclasses import dataclass, field
from time import time as current_time

import aio_pika
from aio_pika.abc import (
    AbstractChannel,
    AbstractExchange,
    AbstractIncomingMessage,
    AbstractQueue,
    AbstractRobustConnection,
)

from .base_driver import BaseDriver


@dataclass
class RabbitMQDriver(BaseDriver):
    """RabbitMQ-based queue driver using AMQP 0.9.1 protocol.

    Architecture:
        - Immediate tasks: Direct exchange with queue (routing_key = queue_name)
        - Delayed tasks: Stored in delayed queue with timestamp, moved when ready
        - Uses aio-pika for async AMQP operations
        - Auto-reconnection with connect_robust
        - Message acknowledgments for reliable processing

    Design Decisions:
        - Direct exchange pattern: Simple routing (queue_name = routing_key)
        - Delayed task implementation: Timestamp-based (ready_at prepended to message)
          - Avoids RabbitMQ per-message TTL limitations (requires consumption to dead-letter)
          - _process_delayed_tasks() checks timestamps and moves ready messages
        - Consumer prefetch: Set to 1 for fair distribution across workers
        - Auto-delete queues: False (persistent queues for reliability)
        - Durable queues: True (survive broker restarts)

    Requirements:
        - Python 3.11+, aio-pika 9.0+, RabbitMQ server 3.8+
        - No plugins required for delayed messages
    """

    url: str = "amqp://guest:guest@localhost:5672/"
    exchange_name: str = "async_task"
    prefetch_count: int = 1
    connection: AbstractRobustConnection | None = field(default=None, init=False, repr=False)
    channel: AbstractChannel | None = field(default=None, init=False, repr=False)
    _queues: dict[str, AbstractQueue] = field(default_factory=dict, init=False, repr=False)
    _delayed_queues: dict[str, AbstractQueue] = field(default_factory=dict, init=False, repr=False)
    _delayed_exchange: AbstractExchange | None = field(default=None, init=False, repr=False)
    _receipt_handles: dict[bytes, AbstractIncomingMessage] = field(
        default_factory=dict, init=False, repr=False
    )

    async def connect(self) -> None:
        """Initialize RabbitMQ connection with auto-reconnection.

        Uses connect_robust for automatic reconnection and state recovery.
        Creates exchange and channel for queue operations.
        """
        if self.connection is not None:
            return

        self.connection = await aio_pika.connect_robust(self.url)
        self.channel = await self.connection.channel()

        # Set prefetch count for fair distribution
        await self.channel.set_qos(prefetch_count=self.prefetch_count)

        # Declare main exchange (direct exchange for routing)
        exchange = await self.channel.declare_exchange(
            self.exchange_name, aio_pika.ExchangeType.DIRECT, durable=True
        )
        self._delayed_exchange = exchange

    async def disconnect(self) -> None:
        """Close connection and cleanup resources."""
        if self.channel is not None:
            await self.channel.close()
            self.channel = None

        if self.connection is not None:
            await self.connection.close()
            self.connection = None

        self._queues.clear()
        self._delayed_queues.clear()
        self._delayed_exchange = None
        self._receipt_handles.clear()

    async def _ensure_queue(self, queue_name: str) -> AbstractQueue:
        """Ensure queue exists and return it.

        Creates queue if it doesn't exist, binds to exchange.
        Caches queue for subsequent operations.
        """
        if queue_name in self._queues:
            return self._queues[queue_name]

        if self.channel is None:
            await self.connect()
            assert self.channel is not None
            assert self._delayed_exchange is not None

        # Declare queue (durable, not auto-delete)
        queue = await self.channel.declare_queue(queue_name, durable=True, auto_delete=False)

        # Bind queue to exchange with routing_key = queue_name
        exchange = self._delayed_exchange
        assert exchange is not None
        await queue.bind(exchange, routing_key=queue_name)

        self._queues[queue_name] = queue
        return queue

    async def _ensure_delayed_queue(self, queue_name: str) -> AbstractQueue:
        """Ensure delayed queue exists for delayed message handling.

        Creates a delayed queue with TTL that moves messages to main queue when ready.
        """
        assert self.connection is not None

        delayed_queue_name = f"{queue_name}_delayed"

        if delayed_queue_name in self._delayed_queues:
            return self._delayed_queues[delayed_queue_name]

        if self.channel is None:
            await self.connect()
            assert self.channel is not None
            assert self._delayed_exchange is not None

        # Create delayed queue (no dead-letter exchange needed - we handle manually)
        # If it fails due to precondition (wrong args from old implementation), delete and recreate
        try:
            delayed_queue = await self.channel.declare_queue(
                delayed_queue_name,
                durable=True,
                auto_delete=False,
            )
        except Exception as e:
            # If queue exists with wrong arguments, we need to delete and recreate
            error_str = str(e).lower()
            if "precondition" in error_str or "inequivalent" in error_str:
                # Channel is now closed due to the error, need to reconnect
                await self.disconnect()
                await self.connect()
                assert self.channel is not None

                # Delete the old queue with wrong arguments
                try:
                    # Use management HTTP API or just purge and try to delete via new channel
                    temp_channel = await self.connection.channel()
                    temp_queue = await temp_channel.get_queue(delayed_queue_name)
                    await temp_queue.delete(if_unused=False, if_empty=False)
                    await temp_channel.close()
                except Exception:
                    pass

            # Try to create again with new channel
            delayed_queue = await self.channel.declare_queue(
                delayed_queue_name,
                durable=True,
                auto_delete=False,
            )

        # Bind delayed queue to exchange so we can route messages to it
        exchange = self._delayed_exchange
        assert exchange is not None
        await delayed_queue.bind(exchange, routing_key=delayed_queue_name)

        self._delayed_queues[delayed_queue_name] = delayed_queue
        return delayed_queue

    async def enqueue(self, queue_name: str, task_data: bytes, delay_seconds: int = 0) -> None:
        """Add task to queue with optional delay.

        Args:
            queue_name: Name of the queue
            task_data: Serialized task data
            delay_seconds: Seconds to delay task visibility (0 = immediate)

        Implementation:
            - Immediate: Publish to main queue via direct exchange
            - Delayed: Publish to delayed queue with TTL = delay_seconds
        """
        if self.channel is None:
            await self.connect()
            assert self.channel is not None
            assert self._delayed_exchange is not None

        message = aio_pika.Message(
            body=task_data,
            delivery_mode=aio_pika.DeliveryMode.PERSISTENT,  # Make message persistent
        )

        if delay_seconds > 0:
            # Ensure both delayed queue and main queue exist
            # Main queue must exist for dead-letter routing to work
            await self._ensure_queue(queue_name)
            await self._ensure_delayed_queue(queue_name)

            # Store the ready_at timestamp in the message headers
            # We'll use this to determine when the message should be processed
            ready_at = current_time() + delay_seconds

            # Encode ready_at as bytes (8-byte double)
            ready_at_bytes = struct.pack("d", ready_at)

            # Prepend ready_at timestamp to task_data
            delayed_body = ready_at_bytes + task_data

            message = aio_pika.Message(
                body=delayed_body,
                delivery_mode=aio_pika.DeliveryMode.PERSISTENT,
            )

            # Publish to delayed queue
            # We'll manually check timestamps and move to main queue when ready
            delayed_queue_name = f"{queue_name}_delayed"
            assert self._delayed_exchange is not None
            await self._delayed_exchange.publish(message, routing_key=delayed_queue_name)
        else:
            # Publish directly to main exchange
            assert self._delayed_exchange is not None
            await self._delayed_exchange.publish(message, routing_key=queue_name)

    async def dequeue(self, queue_name: str, poll_seconds: int = 0) -> bytes | None:
        """Retrieve next task from queue.

        Args:
            queue_name: Name of the queue
            poll_seconds: Seconds to poll for task (0 = non-blocking)

        Returns:
            Serialized task data or None if queue empty

        Implementation:
            Uses queue.get() for non-blocking or blocking retrieval.
            Stores message in _receipt_handles for ack/nack operations.
            For polling, uses manual loop with short timeouts for better control.
        """
        if self.channel is None:
            await self.connect()
            assert self.channel is not None

        # Process any ready delayed tasks
        await self._process_delayed_tasks(queue_name)

        # Ensure queue exists and is bound - re-declare to refresh state
        queue = await self._ensure_queue(queue_name)
        # Re-declare queue to ensure we have fresh state
        await queue.declare()

        # For non-blocking, use queue.get() directly
        if poll_seconds == 0:
            message = await queue.get(fail=False)
            if message is None:
                return None

            # Store message for ack/nack
            task_data = message.body
            self._receipt_handles[task_data] = message
            return task_data

        # For polling, use manual loop with short timeouts
        deadline = current_time() + poll_seconds
        poll_interval = 0.1  # Poll every 100ms

        while True:
            # Try to get message (non-blocking)
            message = await queue.get(fail=False)
            if message is not None:
                # Store message for ack/nack
                task_data = message.body
                self._receipt_handles[task_data] = message
                return task_data

            # Check if we've exceeded the deadline
            if current_time() >= deadline:
                return None

            # Sleep before next poll
            await asyncio.sleep(poll_interval)

    async def ack(self, queue_name: str, receipt_handle: bytes) -> None:
        """Acknowledge successful task processing.

        Args:
            queue_name: Name of the queue
            receipt_handle: Task data from dequeue

        Implementation:
            Acknowledges the message, removing it from queue.
            Idempotent operation.
        """
        message = self._receipt_handles.get(receipt_handle)

        if message is not None:
            await message.ack()
            self._receipt_handles.pop(receipt_handle, None)

    async def nack(self, queue_name: str, receipt_handle: bytes) -> None:
        """Reject task and re-queue for immediate retry.

        Args:
            queue_name: Name of the queue
            receipt_handle: Task data from dequeue

        Implementation:
            Rejects message and requeues it immediately.
            Only requeues if message exists (prevents nack-after-ack).
        """
        message = self._receipt_handles.get(receipt_handle)

        if message is not None:
            # Reject and requeue
            await message.nack(requeue=True)
            self._receipt_handles.pop(receipt_handle, None)

    async def get_queue_size(
        self,
        queue_name: str,
        include_delayed: bool,
        include_in_flight: bool,
    ) -> int:
        """Get number of tasks in queue.

        Args:
            queue_name: Name of the queue
            include_delayed: Include delayed tasks in count
            include_in_flight: Include in-flight tasks in count

        Returns:
            Task count based on parameters

        Note:
            RabbitMQ doesn't provide exact in-flight counts via management API.
            This implementation uses queue.declare() to get message count,
            which includes ready messages only.
            In-flight messages are tracked by unacknowledged messages.
        """
        if self.channel is None:
            await self.connect()
            assert self.channel is not None

        size = 0

        # Get main queue size
        queue = await self._ensure_queue(queue_name)
        queue_state = await queue.declare()
        message_count = queue_state.message_count or 0
        size += message_count

        if include_delayed:
            # Get delayed queue size
            delayed_queue = await self._ensure_delayed_queue(queue_name)
            delayed_state = await delayed_queue.declare()
            delayed_count = delayed_state.message_count or 0
            size += delayed_count

        # Note: include_in_flight is not easily trackable in RabbitMQ
        # without using management API. For now, we approximate by not including it.
        # In-flight messages are those that are delivered but not yet ack'd.
        # This would require management plugin access.

        return size

    async def _process_delayed_tasks(self, queue_name: str) -> None:
        """Process delayed tasks that are ready.

        Checks delayed queue for messages with ready_at timestamp <= current time.
        Moves ready messages to the main queue and requeues not-ready messages.

        Args:
            queue_name: Name of the queue
        """
        delayed_queue_name = f"{queue_name}_delayed"

        # If delayed queue doesn't exist yet, nothing to process
        if delayed_queue_name not in self._delayed_queues:
            return

        if self.channel is None or self._delayed_exchange is None:
            await self.connect()
            assert self.channel is not None
            assert self._delayed_exchange is not None

        # Get the delayed queue
        delayed_queue = self._delayed_queues[delayed_queue_name]

        # Process messages from delayed queue
        # We need to peek at all messages and move ready ones
        now = current_time()
        messages_to_requeue = []

        while True:
            # Get message from delayed queue
            message = await delayed_queue.get(fail=False)
            if message is None:
                break  # No more messages

            # Extract ready_at timestamp from message body
            if len(message.body) < 8:
                # Malformed message, ack it to remove
                await message.ack()
                continue

            # Decode ready_at (first 8 bytes)
            ready_at = struct.unpack("d", message.body[:8])[0]
            task_data = message.body[8:]  # Rest is actual task data

            # Check if message is ready
            if now >= ready_at:
                # Message is ready - publish to main queue
                await self._delayed_exchange.publish(
                    aio_pika.Message(
                        body=task_data,
                        delivery_mode=aio_pika.DeliveryMode.PERSISTENT,
                    ),
                    routing_key=queue_name,
                )
                # Acknowledge the delayed message
                await message.ack()
            else:
                # Not ready yet - store for requeuing
                messages_to_requeue.append(message)

        # Requeue messages that aren't ready yet
        for message in messages_to_requeue:
            # Requeue by nacking with requeue=True
            await message.nack(requeue=True)
