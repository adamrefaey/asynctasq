import asyncio
from dataclasses import dataclass, field
import struct
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
        - Delayed tasks: Stored in delayed queue with timestamp prepended to message body
        - Receipt handles: Task data bytes mapped to AbstractIncomingMessage for ack/nack
        - Queue caching: Queues are cached in _queues and _delayed_queues dicts
        - Auto-queue creation: Queues are created on-demand when first accessed

    Features:
        - Reliable message delivery with persistent messages
        - Delayed task support without plugins (timestamp-based)
        - Auto-reconnection with connect_robust for resilience
        - Fair task distribution via prefetch_count=1
        - Message acknowledgments for reliable processing
        - Queue auto-creation on enqueue/dequeue operations
        - Polling support with configurable timeout

    Design Decisions:
        - Direct exchange pattern: Simple routing (queue_name = routing_key)
        - Delayed task implementation: Timestamp-based (ready_at prepended to message)
          - Avoids RabbitMQ per-message TTL limitations (requires consumption to dead-letter)
          - _process_delayed_tasks() checks timestamps and moves ready messages
          - Timestamp encoded as 8-byte double using struct.pack/unpack
        - Consumer prefetch: Set to 1 for fair distribution across workers
        - Auto-delete queues: False (persistent queues for reliability)
        - Durable queues: True (survive broker restarts)
        - Polling implementation: Manual loop with 100ms intervals (not blocking AMQP)
        - Receipt handle: Uses task data bytes as key (enables idempotent ack/nack)

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
    _in_flight_per_queue: dict[str, int] = field(default_factory=dict, init=False, repr=False)

    async def connect(self) -> None:
        """Initialize RabbitMQ connection with auto-reconnection.

        Implementation:
            - Uses connect_robust for automatic reconnection and state recovery
            - Creates a single channel for all queue operations
            - Sets QoS prefetch_count for fair task distribution
            - Declares durable direct exchange for message routing
            - Idempotent: safe to call multiple times

        Raises:
            aio_pika.exceptions.AMQPConnectionError: If connection fails
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
        """Close connection and cleanup resources.

        Implementation:
            - Closes channel and connection gracefully
            - Clears all cached queues and receipt handles
            - Idempotent: safe to call multiple times
        """
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
        self._in_flight_per_queue.clear()

    async def _ensure_queue(self, queue_name: str) -> AbstractQueue:
        """Ensure queue exists and return it.

        Args:
            queue_name: Name of the queue to ensure exists

        Returns:
            AbstractQueue instance for the queue

        Implementation:
            - Checks cache first (_queues dict) for performance
            - Creates queue if not cached (durable, not auto-delete)
            - Binds queue to direct exchange with routing_key = queue_name
            - Caches queue for subsequent operations
            - Auto-connects if channel not initialized
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

        Args:
            queue_name: Name of the main queue (delayed queue name = "{queue_name}_delayed")

        Returns:
            AbstractQueue instance for the delayed queue

        Implementation:
            - Creates delayed queue named "{queue_name}_delayed"
            - Handles precondition failures (queue exists with wrong args)
            - On precondition failure: disconnects, deletes old queue, recreates
            - Binds delayed queue to exchange for routing
            - Caches queue for subsequent operations
            - Auto-connects if channel not initialized
        """
        delayed_queue_name = f"{queue_name}_delayed"

        if delayed_queue_name in self._delayed_queues:
            return self._delayed_queues[delayed_queue_name]

        if self.channel is None:
            await self.connect()
            assert self.channel is not None
            assert self._delayed_exchange is not None

        # Create delayed queue with dead-letter exchange configuration
        # Dead-letter exchange routes expired/delayed messages back to main queue
        # If it fails due to precondition (wrong args from old implementation), delete and recreate
        try:
            delayed_queue = await self.channel.declare_queue(
                delayed_queue_name,
                durable=True,
                auto_delete=False,
                arguments={
                    "x-dead-letter-exchange": self.exchange_name,
                    "x-dead-letter-routing-key": queue_name,
                },
            )
        except Exception as e:
            # If queue exists with wrong arguments, we need to delete and recreate
            error_str = str(e).lower()
            if "precondition" in error_str or "inequivalent" in error_str:
                # Channel is now closed due to the error, need to reconnect
                await self.disconnect()
                await self.connect()
                assert self.channel is not None
                assert self.connection is not None

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
                arguments={
                    "x-dead-letter-exchange": self.exchange_name,
                    "x-dead-letter-routing-key": queue_name,
                },
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
            - Immediate (delay_seconds <= 0):
              - Creates persistent message with task_data
              - Publishes directly to main queue via direct exchange
              - Queue auto-created if doesn't exist
            - Delayed (delay_seconds > 0):
              - Calculates ready_at = current_time + delay_seconds
              - Encodes ready_at as 8-byte double using struct.pack
              - Prepends ready_at_bytes to task_data (delayed_body)
              - Creates persistent message with delayed_body
              - Publishes to delayed queue (auto-created if needed)
              - _process_delayed_tasks() will move to main queue when ready
            - All messages use PERSISTENT delivery mode for durability
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
            # Ensure queue exists and is bound before publishing immediate tasks
            await self._ensure_queue(queue_name)
            # Publish directly to main exchange
            assert self._delayed_exchange is not None
            await self._delayed_exchange.publish(message, routing_key=queue_name)

    async def dequeue(self, queue_name: str, poll_seconds: int = 0) -> bytes | None:
        """Retrieve next task from queue.

        Args:
            queue_name: Name of the queue
            poll_seconds: Seconds to poll for task (0 = non-blocking)

        Returns:
            Serialized task data (bytes) or None if queue empty

        Implementation:
            - Processes delayed tasks first via _process_delayed_tasks()
            - Ensures queue exists and refreshes state via queue.declare()
            - Non-blocking (poll_seconds=0):
              - Uses queue.get(fail=False) for immediate retrieval
              - Returns None immediately if no message available
            - Polling (poll_seconds > 0):
              - Manual loop with 100ms poll interval
              - Checks deadline on each iteration
              - Returns None when deadline exceeded
            - Stores message in _receipt_handles dict (key=task_data, value=message)
              for subsequent ack/nack operations
            - Returns task_data bytes (not the message object)
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
            # Track in-flight message for this queue
            self._in_flight_per_queue[queue_name] = self._in_flight_per_queue.get(queue_name, 0) + 1
            return task_data

        # For polling, use manual loop with short intervals
        # Note: queue.get(timeout=..., fail=False) doesn't wait when fail=False
        deadline = current_time() + poll_seconds
        poll_interval = 0.1  # Poll every 100ms

        while True:
            # Try to get message (non-blocking)
            message = await queue.get(fail=False)
            if message is not None:
                # Store message for ack/nack
                task_data = message.body
                self._receipt_handles[task_data] = message
                # Track in-flight message for this queue
                self._in_flight_per_queue[queue_name] = (
                    self._in_flight_per_queue.get(queue_name, 0) + 1
                )
                return task_data

            # Check if we've exceeded the deadline
            if current_time() >= deadline:
                return None

            # Sleep before next poll
            await asyncio.sleep(poll_interval)

    async def ack(self, queue_name: str, receipt_handle: bytes) -> None:
        """Acknowledge successful task processing.

        Args:
            queue_name: Name of the queue (unused but required by protocol)
            receipt_handle: Task data bytes from dequeue (used as key in _receipt_handles)

        Implementation:
            - Looks up message in _receipt_handles dict using receipt_handle as key
            - If message found: acknowledges it (removes from queue)
            - Removes receipt_handle from dict after ack
            - Idempotent: safe to call multiple times (no-op if handle not found)
            - Prevents duplicate processing by removing message from queue
        """
        message = self._receipt_handles.get(receipt_handle)

        if message is not None:
            await message.ack()
            self._receipt_handles.pop(receipt_handle, None)
            # Decrement in-flight counter
            if queue_name in self._in_flight_per_queue:
                self._in_flight_per_queue[queue_name] = max(
                    0, self._in_flight_per_queue[queue_name] - 1
                )

    async def nack(self, queue_name: str, receipt_handle: bytes) -> None:
        """Reject task and re-queue for immediate retry.

        Args:
            queue_name: Name of the queue (unused but required by protocol)
            receipt_handle: Task data bytes from dequeue (used as key in _receipt_handles)

        Implementation:
            - Looks up message in _receipt_handles dict using receipt_handle as key
            - If message found: rejects with requeue=True (adds back to queue)
            - Removes receipt_handle from dict after nack
            - Idempotent: safe to call multiple times (no-op if handle not found)
            - Prevents nack-after-ack bugs by only requeuing if message exists
            - Message is requeued at front of queue for immediate retry
        """
        message = self._receipt_handles.get(receipt_handle)

        if message is not None:
            # Reject and requeue
            await message.nack(requeue=True)
            self._receipt_handles.pop(receipt_handle, None)
            # Decrement in-flight counter
            if queue_name in self._in_flight_per_queue:
                self._in_flight_per_queue[queue_name] = max(
                    0, self._in_flight_per_queue[queue_name] - 1
                )

    async def purge_queue(self, queue_name: str) -> None:
        """Purge both main and delayed queues for a given queue name."""
        if self.channel is None:
            await self.connect()
        # Purge main queue
        queue = await self._ensure_queue(queue_name)
        await queue.purge()
        # Purge delayed queue if exists
        delayed_queue_name = f"{queue_name}_delayed"
        if delayed_queue_name in self._delayed_queues:
            delayed_queue = self._delayed_queues[delayed_queue_name]
            await delayed_queue.purge()

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
            Task count based on parameters:
            - Both False: Only ready tasks in main queue
            - include_delayed=True: Ready + delayed tasks
            - include_in_flight=True: Ready tasks (in-flight not tracked)
            - Both True: Ready + delayed tasks (in-flight not tracked)

        Implementation:
            - Gets main queue size via queue.declare().message_count
            - If include_delayed: adds delayed queue size
            - Note: include_in_flight is not supported (requires management API)
            - In-flight messages are those delivered but not yet acknowledged
            - Queue auto-created if doesn't exist

        Note:
            RabbitMQ doesn't provide exact in-flight counts without management API.
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
        # RabbitMQ's message_count only includes ready messages (excludes in-flight)
        size += message_count

        # Add in-flight messages if requested
        if include_in_flight:
            in_flight_count = self._in_flight_per_queue.get(queue_name, 0)
            size += in_flight_count

        if include_delayed:
            # Get delayed queue size
            delayed_queue = await self._ensure_delayed_queue(queue_name)
            delayed_state = await delayed_queue.declare()
            delayed_count = delayed_state.message_count or 0
            size += delayed_count

        return size

    async def _process_delayed_tasks(self, queue_name: str) -> None:
        """Process delayed tasks that are ready.

        Checks delayed queue for messages with ready_at timestamp <= current time.
        Moves ready messages to the main queue and requeues not-ready messages.

        Args:
            queue_name: Name of the main queue (delayed queue = "{queue_name}_delayed")

        Implementation:
            - Returns early if delayed queue doesn't exist (no delayed tasks)
            - Processes all messages in delayed queue:
              1. Gets message from delayed queue (non-blocking)
              2. Extracts ready_at timestamp from first 8 bytes (struct.unpack)
              3. Extracts task_data from remaining bytes
              4. If ready_at <= current_time:
                 - Publishes task_data to main queue (persistent message)
                 - Acknowledges delayed message (removes from delayed queue)
              5. If ready_at > current_time:
                 - Stores message for requeuing
            - Requeues not-ready messages via nack(requeue=True)
            - Handles malformed messages (< 8 bytes) by acking them (removes)
            - Called automatically before each dequeue operation
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
