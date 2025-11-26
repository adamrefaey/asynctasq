"""Unit tests for RabbitMQDriver.

Testing Strategy:
- pytest 9.0.1 with asyncio_mode="auto" (no decorators needed)
- AAA pattern (Arrange, Act, Assert)
- Use mocks to test RabbitMQDriver without requiring real RabbitMQ
- Test all methods, edge cases, and error conditions
- Achieve >90% code coverage
"""

from unittest.mock import AsyncMock, MagicMock, patch

from pytest import main, mark

from async_task.drivers.rabbitmq_driver import RabbitMQDriver


@mark.unit
class TestRabbitMQDriverInitialization:
    """Test RabbitMQDriver initialization and connection lifecycle."""

    def test_driver_initializes_with_defaults(self) -> None:
        """Test driver initializes with default values."""
        # Act
        driver = RabbitMQDriver()

        # Assert
        assert driver.url == "amqp://guest:guest@localhost:5672/"
        assert driver.exchange_name == "async_task"
        assert driver.prefetch_count == 1
        assert driver.connection is None
        assert driver.channel is None

    def test_driver_initializes_with_custom_values(self) -> None:
        """Test driver initializes with custom values."""
        # Act
        driver = RabbitMQDriver(
            url="amqp://user:pass@host:5672/",
            exchange_name="custom_exchange",
            prefetch_count=10,
        )

        # Assert
        assert driver.url == "amqp://user:pass@host:5672/"
        assert driver.exchange_name == "custom_exchange"
        assert driver.prefetch_count == 10

    @mark.asyncio
    async def test_connect_creates_connection_and_channel(self) -> None:
        """Test connect() creates connection and channel."""
        # Arrange
        driver = RabbitMQDriver()
        mock_connection = AsyncMock()
        mock_channel = AsyncMock()
        mock_exchange = AsyncMock()

        with patch("async_task.drivers.rabbitmq_driver.aio_pika.connect_robust", return_value=mock_connection):
            mock_connection.channel = AsyncMock(return_value=mock_channel)
            mock_channel.set_qos = AsyncMock()
            mock_channel.declare_exchange = AsyncMock(return_value=mock_exchange)

            # Act
            await driver.connect()

            # Assert
            assert driver.connection == mock_connection
            assert driver.channel == mock_channel
            assert driver._delayed_exchange == mock_exchange
            mock_connection.channel.assert_called_once()
            mock_channel.set_qos.assert_called_once_with(prefetch_count=1)
            mock_channel.declare_exchange.assert_called_once()

    @mark.asyncio
    async def test_connect_is_idempotent(self) -> None:
        """Test connect() can be called multiple times safely."""
        # Arrange
        driver = RabbitMQDriver()
        mock_connection = AsyncMock()
        mock_channel = AsyncMock()
        mock_exchange = AsyncMock()

        with patch("async_task.drivers.rabbitmq_driver.aio_pika.connect_robust", return_value=mock_connection):
            mock_connection.channel = AsyncMock(return_value=mock_channel)
            mock_channel.set_qos = AsyncMock()
            mock_channel.declare_exchange = AsyncMock(return_value=mock_exchange)

            # Act
            await driver.connect()
            first_connection = driver.connection
            await driver.connect()  # Second call

            # Assert
            assert driver.connection == first_connection
            assert mock_connection.channel.call_count == 1  # Only called once

    @mark.asyncio
    async def test_disconnect_closes_connection_and_channel(self) -> None:
        """Test disconnect() closes connection and channel."""
        # Arrange
        driver = RabbitMQDriver()
        mock_connection = AsyncMock()
        mock_channel = AsyncMock()
        mock_exchange = AsyncMock()

        with patch("async_task.drivers.rabbitmq_driver.aio_pika.connect_robust", return_value=mock_connection):
            mock_connection.channel = AsyncMock(return_value=mock_channel)
            mock_channel.set_qos = AsyncMock()
            mock_channel.declare_exchange = AsyncMock(return_value=mock_exchange)
            mock_channel.close = AsyncMock()
            mock_connection.close = AsyncMock()

            await driver.connect()

            # Act
            await driver.disconnect()

            # Assert
            mock_channel.close.assert_called_once()
            mock_connection.close.assert_called_once()
            assert driver.connection is None
            assert driver.channel is None
            assert driver._delayed_exchange is None

    @mark.asyncio
    async def test_disconnect_is_idempotent(self) -> None:
        """Test disconnect() can be called multiple times safely."""
        # Arrange
        driver = RabbitMQDriver()
        mock_connection = AsyncMock()
        mock_channel = AsyncMock()
        mock_exchange = AsyncMock()

        with patch("async_task.drivers.rabbitmq_driver.aio_pika.connect_robust", return_value=mock_connection):
            mock_connection.channel = AsyncMock(return_value=mock_channel)
            mock_channel.set_qos = AsyncMock()
            mock_channel.declare_exchange = AsyncMock(return_value=mock_exchange)
            mock_channel.close = AsyncMock()
            mock_connection.close = AsyncMock()

            await driver.connect()

            # Act
            await driver.disconnect()
            await driver.disconnect()  # Second call

            # Assert
            assert mock_channel.close.call_count == 1
            assert mock_connection.close.call_count == 1


@mark.unit
class TestRabbitMQDriverEnqueue:
    """Test RabbitMQDriver.enqueue() method."""

    @mark.asyncio
    async def test_enqueue_immediate_task(self) -> None:
        """Test enqueue() with immediate task (delay=0)."""
        # Arrange
        driver = RabbitMQDriver()
        mock_connection = AsyncMock()
        mock_channel = AsyncMock()
        mock_exchange = AsyncMock()
        mock_exchange.publish = AsyncMock()

        with patch("async_task.drivers.rabbitmq_driver.aio_pika.connect_robust", return_value=mock_connection):
            mock_connection.channel = AsyncMock(return_value=mock_channel)
            mock_channel.set_qos = AsyncMock()
            mock_channel.declare_exchange = AsyncMock(return_value=mock_exchange)

            await driver.connect()

            # Act
            await driver.enqueue("default", b"task_data", delay_seconds=0)

            # Assert
            mock_exchange.publish.assert_called_once()
            call_args = mock_exchange.publish.call_args
            assert call_args[1]["routing_key"] == "default"

    @mark.asyncio
    async def test_enqueue_delayed_task(self) -> None:
        """Test enqueue() with delayed task."""
        # Arrange
        driver = RabbitMQDriver()
        mock_connection = AsyncMock()
        mock_channel = AsyncMock()
        mock_exchange = AsyncMock()
        mock_exchange.publish = AsyncMock()
        mock_delayed_queue = AsyncMock()
        mock_delayed_queue.bind = AsyncMock()

        with patch("async_task.drivers.rabbitmq_driver.aio_pika.connect_robust", return_value=mock_connection):
            mock_connection.channel = AsyncMock(return_value=mock_channel)
            mock_channel.set_qos = AsyncMock()
            mock_channel.declare_exchange = AsyncMock(return_value=mock_exchange)
            mock_channel.declare_queue = AsyncMock(return_value=mock_delayed_queue)

            await driver.connect()

            # Act
            await driver.enqueue("default", b"task_data", delay_seconds=5)

            # Assert
            mock_channel.declare_queue.assert_called()
            mock_exchange.publish.assert_called_once()
            call_args = mock_exchange.publish.call_args
            assert call_args[1]["routing_key"] == "default_delayed"

    @mark.asyncio
    async def test_enqueue_auto_connects(self) -> None:
        """Test enqueue() auto-connects if not connected."""
        # Arrange
        driver = RabbitMQDriver()
        mock_connection = AsyncMock()
        mock_channel = AsyncMock()
        mock_exchange = AsyncMock()
        mock_exchange.publish = AsyncMock()

        with patch("async_task.drivers.rabbitmq_driver.aio_pika.connect_robust", return_value=mock_connection):
            mock_connection.channel = AsyncMock(return_value=mock_channel)
            mock_channel.set_qos = AsyncMock()
            mock_channel.declare_exchange = AsyncMock(return_value=mock_exchange)

            # Act
            await driver.enqueue("default", b"task_data")

            # Assert
            assert driver.connection is not None
            mock_exchange.publish.assert_called_once()


@mark.unit
class TestRabbitMQDriverDequeue:
    """Test RabbitMQDriver.dequeue() method."""

    @mark.asyncio
    async def test_dequeue_returns_task(self) -> None:
        """Test dequeue() returns task data."""
        # Arrange
        driver = RabbitMQDriver()
        mock_connection = AsyncMock()
        mock_channel = AsyncMock()
        mock_exchange = AsyncMock()
        mock_queue = AsyncMock()
        mock_message = AsyncMock()
        mock_message.body = b"task_data"

        with patch("async_task.drivers.rabbitmq_driver.aio_pika.connect_robust", return_value=mock_connection):
            mock_connection.channel = AsyncMock(return_value=mock_channel)
            mock_channel.set_qos = AsyncMock()
            mock_channel.declare_exchange = AsyncMock(return_value=mock_exchange)
            mock_channel.declare_queue = AsyncMock(return_value=mock_queue)
            mock_queue.bind = AsyncMock()
            mock_queue.get = AsyncMock(return_value=mock_message)

            await driver.connect()

            # Act
            result = await driver.dequeue("default", poll_seconds=0)

            # Assert
            assert result == b"task_data"
            assert b"task_data" in driver._receipt_handles

    @mark.asyncio
    async def test_dequeue_returns_none_when_empty(self) -> None:
        """Test dequeue() returns None when queue is empty."""
        # Arrange
        driver = RabbitMQDriver()
        mock_connection = AsyncMock()
        mock_channel = AsyncMock()
        mock_exchange = AsyncMock()
        mock_queue = AsyncMock()

        with patch("async_task.drivers.rabbitmq_driver.aio_pika.connect_robust", return_value=mock_connection):
            mock_connection.channel = AsyncMock(return_value=mock_channel)
            mock_channel.set_qos = AsyncMock()
            mock_channel.declare_exchange = AsyncMock(return_value=mock_exchange)
            mock_channel.declare_queue = AsyncMock(return_value=mock_queue)
            mock_queue.bind = AsyncMock()
            mock_queue.get = AsyncMock(return_value=None)

            await driver.connect()

            # Act
            result = await driver.dequeue("default", poll_seconds=0)

            # Assert
            assert result is None

    @mark.asyncio
    async def test_dequeue_with_poll_seconds(self) -> None:
        """Test dequeue() with poll_seconds > 0."""
        # Arrange
        driver = RabbitMQDriver()
        mock_connection = AsyncMock()
        mock_channel = AsyncMock()
        mock_exchange = AsyncMock()
        mock_queue = AsyncMock()
        mock_message = AsyncMock()
        mock_message.body = b"task_data"

        with patch("async_task.drivers.rabbitmq_driver.aio_pika.connect_robust", return_value=mock_connection):
            mock_connection.channel = AsyncMock(return_value=mock_channel)
            mock_channel.set_qos = AsyncMock()
            mock_channel.declare_exchange = AsyncMock(return_value=mock_exchange)
            mock_channel.declare_queue = AsyncMock(return_value=mock_queue)
            mock_queue.bind = AsyncMock()
            mock_queue.get = AsyncMock(return_value=mock_message)

            await driver.connect()

            # Act
            result = await driver.dequeue("default", poll_seconds=5)

            # Assert
            assert result == b"task_data"
            mock_queue.get.assert_called_once_with(timeout=5, fail=False)

    @mark.asyncio
    async def test_dequeue_auto_connects(self) -> None:
        """Test dequeue() auto-connects if not connected."""
        # Arrange
        driver = RabbitMQDriver()
        mock_connection = AsyncMock()
        mock_channel = AsyncMock()
        mock_exchange = AsyncMock()
        mock_queue = AsyncMock()

        with patch("async_task.drivers.rabbitmq_driver.aio_pika.connect_robust", return_value=mock_connection):
            mock_connection.channel = AsyncMock(return_value=mock_channel)
            mock_channel.set_qos = AsyncMock()
            mock_channel.declare_exchange = AsyncMock(return_value=mock_exchange)
            mock_channel.declare_queue = AsyncMock(return_value=mock_queue)
            mock_queue.bind = AsyncMock()
            mock_queue.get = AsyncMock(return_value=None)

            # Act
            await driver.dequeue("default", poll_seconds=0)

            # Assert
            assert driver.connection is not None


@mark.unit
class TestRabbitMQDriverAck:
    """Test RabbitMQDriver.ack() method."""

    @mark.asyncio
    async def test_ack_removes_message(self) -> None:
        """Test ack() acknowledges and removes message."""
        # Arrange
        driver = RabbitMQDriver()
        mock_message = AsyncMock()
        mock_message.ack = AsyncMock()
        receipt_handle = b"task_data"
        driver._receipt_handles[receipt_handle] = mock_message

        # Act
        await driver.ack("default", receipt_handle)

        # Assert
        mock_message.ack.assert_called_once()
        assert receipt_handle not in driver._receipt_handles

    @mark.asyncio
    async def test_ack_with_invalid_receipt_is_safe(self) -> None:
        """Test ack() with invalid receipt handle is safe."""
        # Arrange
        driver = RabbitMQDriver()
        receipt_handle = b"invalid"

        # Act & Assert - should not raise
        await driver.ack("default", receipt_handle)


@mark.unit
class TestRabbitMQDriverNack:
    """Test RabbitMQDriver.nack() method."""

    @mark.asyncio
    async def test_nack_requeues_message(self) -> None:
        """Test nack() requeues message."""
        # Arrange
        driver = RabbitMQDriver()
        mock_message = AsyncMock()
        mock_message.nack = AsyncMock()
        receipt_handle = b"task_data"
        driver._receipt_handles[receipt_handle] = mock_message

        # Act
        await driver.nack("default", receipt_handle)

        # Assert
        mock_message.nack.assert_called_once_with(requeue=True)
        assert receipt_handle not in driver._receipt_handles

    @mark.asyncio
    async def test_nack_with_invalid_receipt_is_safe(self) -> None:
        """Test nack() with invalid receipt handle is safe."""
        # Arrange
        driver = RabbitMQDriver()
        receipt_handle = b"invalid"

        # Act & Assert - should not raise
        await driver.nack("default", receipt_handle)


@mark.unit
class TestRabbitMQDriverGetQueueSize:
    """Test RabbitMQDriver.get_queue_size() method."""

    @mark.asyncio
    async def test_get_queue_size_returns_count(self) -> None:
        """Test get_queue_size() returns message count."""
        # Arrange
        driver = RabbitMQDriver()
        mock_connection = AsyncMock()
        mock_channel = AsyncMock()
        mock_exchange = AsyncMock()
        mock_queue = AsyncMock()
        mock_queue_state = MagicMock()
        mock_queue_state.message_count = 5
        mock_queue.declare = AsyncMock(return_value=mock_queue_state)

        with patch("async_task.drivers.rabbitmq_driver.aio_pika.connect_robust", return_value=mock_connection):
            mock_connection.channel = AsyncMock(return_value=mock_channel)
            mock_channel.set_qos = AsyncMock()
            mock_channel.declare_exchange = AsyncMock(return_value=mock_exchange)
            mock_channel.declare_queue = AsyncMock(return_value=mock_queue)
            mock_queue.bind = AsyncMock()

            await driver.connect()

            # Act
            size = await driver.get_queue_size("default", include_delayed=False, include_in_flight=False)

            # Assert
            assert size == 5

    @mark.asyncio
    async def test_get_queue_size_with_delayed(self) -> None:
        """Test get_queue_size() includes delayed queue."""
        # Arrange
        driver = RabbitMQDriver()
        mock_connection = AsyncMock()
        mock_channel = AsyncMock()
        mock_exchange = AsyncMock()
        mock_queue = AsyncMock()
        mock_delayed_queue = AsyncMock()
        mock_queue_state = MagicMock()
        mock_queue_state.message_count = 3
        mock_delayed_state = MagicMock()
        mock_delayed_state.message_count = 2
        mock_queue.declare = AsyncMock(return_value=mock_queue_state)
        mock_delayed_queue.declare = AsyncMock(return_value=mock_delayed_state)

        with patch("async_task.drivers.rabbitmq_driver.aio_pika.connect_robust", return_value=mock_connection):
            mock_connection.channel = AsyncMock(return_value=mock_channel)
            mock_channel.set_qos = AsyncMock()
            mock_channel.declare_exchange = AsyncMock(return_value=mock_exchange)
            mock_channel.declare_queue = AsyncMock(side_effect=[mock_queue, mock_delayed_queue])
            mock_queue.bind = AsyncMock()
            mock_delayed_queue.bind = AsyncMock()

            await driver.connect()

            # Act
            size = await driver.get_queue_size("default", include_delayed=True, include_in_flight=False)

            # Assert
            assert size == 5  # 3 + 2

    @mark.asyncio
    async def test_get_queue_size_handles_none_message_count(self) -> None:
        """Test get_queue_size() handles None message_count."""
        # Arrange
        driver = RabbitMQDriver()
        mock_connection = AsyncMock()
        mock_channel = AsyncMock()
        mock_exchange = AsyncMock()
        mock_queue = AsyncMock()
        mock_queue_state = MagicMock()
        mock_queue_state.message_count = None
        mock_queue.declare = AsyncMock(return_value=mock_queue_state)

        with patch("async_task.drivers.rabbitmq_driver.aio_pika.connect_robust", return_value=mock_connection):
            mock_connection.channel = AsyncMock(return_value=mock_channel)
            mock_channel.set_qos = AsyncMock()
            mock_channel.declare_exchange = AsyncMock(return_value=mock_exchange)
            mock_channel.declare_queue = AsyncMock(return_value=mock_queue)
            mock_queue.bind = AsyncMock()

            await driver.connect()

            # Act
            size = await driver.get_queue_size("default", include_delayed=False, include_in_flight=False)

            # Assert
            assert size == 0

    @mark.asyncio
    async def test_get_queue_size_auto_connects(self) -> None:
        """Test get_queue_size() auto-connects if not connected."""
        # Arrange
        driver = RabbitMQDriver()
        mock_connection = AsyncMock()
        mock_channel = AsyncMock()
        mock_exchange = AsyncMock()
        mock_queue = AsyncMock()
        mock_queue_state = MagicMock()
        mock_queue_state.message_count = 0
        mock_queue.declare = AsyncMock(return_value=mock_queue_state)

        with patch("async_task.drivers.rabbitmq_driver.aio_pika.connect_robust", return_value=mock_connection):
            mock_connection.channel = AsyncMock(return_value=mock_channel)
            mock_channel.set_qos = AsyncMock()
            mock_channel.declare_exchange = AsyncMock(return_value=mock_exchange)
            mock_channel.declare_queue = AsyncMock(return_value=mock_queue)
            mock_queue.bind = AsyncMock()

            # Act
            size = await driver.get_queue_size("default", include_delayed=False, include_in_flight=False)

            # Assert
            assert driver.connection is not None
            assert size == 0


@mark.unit
class TestRabbitMQDriverEnsureQueue:
    """Test RabbitMQDriver._ensure_queue() method."""

    @mark.asyncio
    async def test_ensure_queue_creates_and_binds_queue(self) -> None:
        """Test _ensure_queue() creates and binds queue."""
        # Arrange
        driver = RabbitMQDriver()
        mock_connection = AsyncMock()
        mock_channel = AsyncMock()
        mock_exchange = AsyncMock()
        mock_queue = AsyncMock()
        mock_queue.bind = AsyncMock()

        with patch("async_task.drivers.rabbitmq_driver.aio_pika.connect_robust", return_value=mock_connection):
            mock_connection.channel = AsyncMock(return_value=mock_channel)
            mock_channel.set_qos = AsyncMock()
            mock_channel.declare_exchange = AsyncMock(return_value=mock_exchange)
            mock_channel.declare_queue = AsyncMock(return_value=mock_queue)

            await driver.connect()

            # Act
            queue = await driver._ensure_queue("test_queue")

            # Assert
            assert queue == mock_queue
            mock_channel.declare_queue.assert_called_once_with(
                "test_queue", durable=True, auto_delete=False
            )
            mock_queue.bind.assert_called_once()

    @mark.asyncio
    async def test_ensure_queue_caches_queue(self) -> None:
        """Test _ensure_queue() caches queue for subsequent calls."""
        # Arrange
        driver = RabbitMQDriver()
        mock_connection = AsyncMock()
        mock_channel = AsyncMock()
        mock_exchange = AsyncMock()
        mock_queue = AsyncMock()
        mock_queue.bind = AsyncMock()

        with patch("async_task.drivers.rabbitmq_driver.aio_pika.connect_robust", return_value=mock_connection):
            mock_connection.channel = AsyncMock(return_value=mock_channel)
            mock_channel.set_qos = AsyncMock()
            mock_channel.declare_exchange = AsyncMock(return_value=mock_exchange)
            mock_channel.declare_queue = AsyncMock(return_value=mock_queue)

            await driver.connect()

            # Act
            queue1 = await driver._ensure_queue("test_queue")
            queue2 = await driver._ensure_queue("test_queue")

            # Assert
            assert queue1 == queue2
            assert queue1 == mock_queue
            mock_channel.declare_queue.assert_called_once()  # Only called once


@mark.unit
class TestRabbitMQDriverEnsureDelayedQueue:
    """Test RabbitMQDriver._ensure_delayed_queue() method."""

    @mark.asyncio
    async def test_ensure_delayed_queue_creates_with_dead_letter(self) -> None:
        """Test _ensure_delayed_queue() creates queue with dead-letter exchange."""
        # Arrange
        driver = RabbitMQDriver()
        driver.exchange_name = "test_exchange"
        mock_connection = AsyncMock()
        mock_channel = AsyncMock()
        mock_exchange = AsyncMock()
        mock_delayed_queue = AsyncMock()
        mock_delayed_queue.bind = AsyncMock()

        with patch("async_task.drivers.rabbitmq_driver.aio_pika.connect_robust", return_value=mock_connection):
            mock_connection.channel = AsyncMock(return_value=mock_channel)
            mock_channel.set_qos = AsyncMock()
            mock_channel.declare_exchange = AsyncMock(return_value=mock_exchange)
            mock_channel.declare_queue = AsyncMock(return_value=mock_delayed_queue)

            await driver.connect()

            # Act
            queue = await driver._ensure_delayed_queue("default")

            # Assert
            assert queue == mock_delayed_queue
            mock_channel.declare_queue.assert_called_once()
            call_kwargs = mock_channel.declare_queue.call_args[1]
            assert call_kwargs["durable"] is True
            assert call_kwargs["auto_delete"] is False
            assert "x-dead-letter-exchange" in call_kwargs["arguments"]
            assert call_kwargs["arguments"]["x-dead-letter-exchange"] == "test_exchange"
            assert call_kwargs["arguments"]["x-dead-letter-routing-key"] == "default"

    @mark.asyncio
    async def test_ensure_delayed_queue_caches_queue(self) -> None:
        """Test _ensure_delayed_queue() caches queue."""
        # Arrange
        driver = RabbitMQDriver()
        mock_connection = AsyncMock()
        mock_channel = AsyncMock()
        mock_exchange = AsyncMock()
        mock_delayed_queue = AsyncMock()
        mock_delayed_queue.bind = AsyncMock()

        with patch("async_task.drivers.rabbitmq_driver.aio_pika.connect_robust", return_value=mock_connection):
            mock_connection.channel = AsyncMock(return_value=mock_channel)
            mock_channel.set_qos = AsyncMock()
            mock_channel.declare_exchange = AsyncMock(return_value=mock_exchange)
            mock_channel.declare_queue = AsyncMock(return_value=mock_delayed_queue)

            await driver.connect()

            # Act
            queue1 = await driver._ensure_delayed_queue("default")
            queue2 = await driver._ensure_delayed_queue("default")

            # Assert
            assert queue1 == queue2
            mock_channel.declare_queue.assert_called_once()


@mark.unit
class TestRabbitMQDriverProcessDelayedTasks:
    """Test RabbitMQDriver._process_delayed_tasks() method."""

    @mark.asyncio
    async def test_process_delayed_tasks_is_noop(self) -> None:
        """Test _process_delayed_tasks() is a no-op (handled by RabbitMQ)."""
        # Arrange
        driver = RabbitMQDriver()

        # Act & Assert - should not raise
        await driver._process_delayed_tasks("default")


@mark.unit
class TestRabbitMQDriverEdgeCases:
    """Test edge cases and error conditions."""

    @mark.asyncio
    async def test_enqueue_negative_delay(self) -> None:
        """Test enqueue() with negative delay (treated as immediate)."""
        # Arrange
        driver = RabbitMQDriver()
        mock_connection = AsyncMock()
        mock_channel = AsyncMock()
        mock_exchange = AsyncMock()
        mock_exchange.publish = AsyncMock()

        with patch("async_task.drivers.rabbitmq_driver.aio_pika.connect_robust", return_value=mock_connection):
            mock_connection.channel = AsyncMock(return_value=mock_channel)
            mock_channel.set_qos = AsyncMock()
            mock_channel.declare_exchange = AsyncMock(return_value=mock_exchange)

            await driver.connect()

            # Act
            await driver.enqueue("default", b"task", delay_seconds=-1)

            # Assert - should go to main queue (delay <= 0)
            mock_exchange.publish.assert_called_once()
            call_args = mock_exchange.publish.call_args
            assert call_args[1]["routing_key"] == "default"

    @mark.asyncio
    async def test_receipt_handles_cleared_on_disconnect(self) -> None:
        """Test receipt handles are cleared on disconnect."""
        # Arrange
        driver = RabbitMQDriver()
        mock_message = AsyncMock()
        driver._receipt_handles[b"task1"] = mock_message
        driver._receipt_handles[b"task2"] = mock_message

        mock_connection = AsyncMock()
        mock_channel = AsyncMock()
        mock_exchange = AsyncMock()

        with patch("async_task.drivers.rabbitmq_driver.aio_pika.connect_robust", return_value=mock_connection):
            mock_connection.channel = AsyncMock(return_value=mock_channel)
            mock_channel.set_qos = AsyncMock()
            mock_channel.declare_exchange = AsyncMock(return_value=mock_exchange)
            mock_channel.close = AsyncMock()
            mock_connection.close = AsyncMock()

            await driver.connect()

            # Act
            await driver.disconnect()

            # Assert
            assert len(driver._receipt_handles) == 0

    @mark.asyncio
    async def test_multiple_queues_independent(self) -> None:
        """Test multiple queues are independent."""
        # Arrange
        driver = RabbitMQDriver()
        mock_connection = AsyncMock()
        mock_channel = AsyncMock()
        mock_exchange = AsyncMock()
        mock_queue1 = AsyncMock()
        mock_queue2 = AsyncMock()

        with patch("async_task.drivers.rabbitmq_driver.aio_pika.connect_robust", return_value=mock_connection):
            mock_connection.channel = AsyncMock(return_value=mock_channel)
            mock_channel.set_qos = AsyncMock()
            mock_channel.declare_exchange = AsyncMock(return_value=mock_exchange)
            mock_channel.declare_queue = AsyncMock(side_effect=[mock_queue1, mock_queue2])
            mock_queue1.bind = AsyncMock()
            mock_queue2.bind = AsyncMock()

            await driver.connect()

            # Act
            queue1 = await driver._ensure_queue("queue1")
            queue2 = await driver._ensure_queue("queue2")

            # Assert
            assert queue1 == mock_queue1
            assert queue2 == mock_queue2
            assert queue1 != queue2


if __name__ == "__main__":
    main([__file__, "-s", "-m", "unit"])

