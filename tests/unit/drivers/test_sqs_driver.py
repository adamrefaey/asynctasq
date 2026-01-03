"""Unit tests for SQSDriver.

Testing Strategy:
- pytest 9.0.1 with asyncio_mode="auto" (no decorators needed)
- AAA pattern (Arrange, Act, Assert)
- Use mocks to test SQSDriver without requiring real AWS SQS
- Test all methods, edge cases, and error conditions
- Achieve >90% code coverage
"""

from base64 import b64encode
from unittest.mock import AsyncMock, MagicMock, patch

from pytest import mark, raises

from asynctasq.drivers.sqs_driver import SQSDriver


@mark.unit
class TestSQSDriverInitialization:
    """Test SQSDriver initialization and connection lifecycle."""

    def test_driver_initializes_with_defaults(self) -> None:
        """Test driver initializes with default values."""
        # Act
        driver = SQSDriver()

        # Assert
        assert driver.region_name == "us-east-1"
        assert driver.aws_access_key_id is None
        assert driver.aws_secret_access_key is None
        assert driver.endpoint_url is None
        assert driver.session is None
        assert driver.client is None

    def test_driver_initializes_with_custom_values(self) -> None:
        """Test driver initializes with custom values."""
        # Act
        driver = SQSDriver(
            region_name="us-west-2",
            aws_access_key_id="test_key",
            aws_secret_access_key="test_secret",
            endpoint_url="http://localhost:4566",
        )

        # Assert
        assert driver.region_name == "us-west-2"
        assert driver.aws_access_key_id == "test_key"
        assert driver.aws_secret_access_key == "test_secret"
        assert driver.endpoint_url == "http://localhost:4566"

    @mark.asyncio
    async def test_connect_creates_session_and_client(self) -> None:
        """Test connect() creates session and client."""
        # Arrange
        driver = SQSDriver()
        mock_session = MagicMock()
        mock_client = AsyncMock()
        mock_exit_stack = AsyncMock()

        with (
            patch("asynctasq.drivers.sqs_driver.Session", return_value=mock_session),
            patch("asynctasq.drivers.sqs_driver.AsyncExitStack", return_value=mock_exit_stack),
        ):
            mock_exit_stack.enter_async_context = AsyncMock(return_value=mock_client)

            # Act
            await driver.connect()

            # Assert
            assert driver.session == mock_session
            assert driver.client == mock_client
            assert driver._exit_stack == mock_exit_stack

    @mark.asyncio
    async def test_connect_with_endpoint_url(self) -> None:
        """Test connect() with custom endpoint URL."""
        # Arrange
        driver = SQSDriver(endpoint_url="http://localhost:4566")
        mock_session = MagicMock()
        mock_client = AsyncMock()
        mock_exit_stack = AsyncMock()

        with (
            patch("asynctasq.drivers.sqs_driver.Session", return_value=mock_session),
            patch("asynctasq.drivers.sqs_driver.AsyncExitStack", return_value=mock_exit_stack),
        ):
            mock_exit_stack.enter_async_context = AsyncMock(return_value=mock_client)

            # Act
            await driver.connect()

            # Assert
            assert driver.client == mock_client

    @mark.asyncio
    async def test_connect_is_idempotent(self) -> None:
        """Test connect() can be called multiple times safely."""
        # Arrange
        driver = SQSDriver()
        mock_session = MagicMock()
        mock_client = AsyncMock()
        mock_exit_stack = AsyncMock()

        with (
            patch("asynctasq.drivers.sqs_driver.Session", return_value=mock_session),
            patch("asynctasq.drivers.sqs_driver.AsyncExitStack", return_value=mock_exit_stack),
        ):
            mock_exit_stack.enter_async_context = AsyncMock(return_value=mock_client)

            # Act
            await driver.connect()
            first_client = driver.client
            await driver.connect()  # Second call

            # Assert
            assert driver.client == first_client

    @mark.asyncio
    async def test_disconnect_closes_exit_stack(self) -> None:
        """Test disconnect() closes exit stack and clears state."""
        # Arrange
        driver = SQSDriver()
        mock_exit_stack = AsyncMock()
        driver._exit_stack = mock_exit_stack
        driver.client = AsyncMock()
        driver.session = MagicMock()
        driver._queue_urls = {"test_queue": "http://queue_url"}
        driver._receipt_handles = {b"receipt": "handle"}

        # Act
        await driver.disconnect()

        # Assert
        mock_exit_stack.aclose.assert_called_once()
        assert driver.client is None
        assert driver.session is None
        assert driver._queue_urls == {}
        assert driver._receipt_handles == {}

    @mark.asyncio
    async def test_disconnect_handles_none_exit_stack(self) -> None:
        """Test disconnect() handles None exit stack gracefully."""
        # Arrange
        driver = SQSDriver()

        # Act & Assert - Should not raise
        await driver.disconnect()

        assert driver.client is None


@mark.unit
class TestSQSDriverEnqueue:
    """Test SQSDriver.enqueue() method."""

    @mark.asyncio
    async def test_enqueue_immediate_task(self) -> None:
        """Test enqueue() with immediate task (delay=0)."""
        # Arrange
        driver = SQSDriver()
        mock_client = AsyncMock()
        driver.client = mock_client
        driver._queue_urls = {"test_queue": "http://queue_url"}

        # Act
        await driver.enqueue("test_queue", b"task_data", delay_seconds=0)

        # Assert
        mock_client.send_message.assert_called_once()
        call_kwargs = mock_client.send_message.call_args[1]
        assert call_kwargs["QueueUrl"] == "http://queue_url"
        assert call_kwargs["MessageBody"] == b64encode(b"task_data").decode("ascii")
        assert "DelaySeconds" not in call_kwargs

    @mark.asyncio
    async def test_enqueue_delayed_task(self) -> None:
        """Test enqueue() with delayed task."""
        # Arrange
        driver = SQSDriver()
        mock_client = AsyncMock()
        driver.client = mock_client
        driver._queue_urls = {"test_queue": "http://queue_url"}

        # Act
        await driver.enqueue("test_queue", b"task_data", delay_seconds=60)

        # Assert
        mock_client.send_message.assert_called_once()
        call_kwargs = mock_client.send_message.call_args[1]
        assert call_kwargs["DelaySeconds"] == 60

    @mark.asyncio
    async def test_enqueue_with_visibility_timeout(self) -> None:
        """Test enqueue() stores visibility timeout in message attributes."""
        # Arrange
        driver = SQSDriver()
        mock_client = AsyncMock()
        driver.client = mock_client
        driver._queue_urls = {"test_queue": "http://queue_url"}

        # Act
        await driver.enqueue("test_queue", b"task_data", visibility_timeout=600)

        # Assert
        mock_client.send_message.assert_called_once()
        call_kwargs = mock_client.send_message.call_args[1]
        assert call_kwargs["MessageAttributes"]["visibility_timeout"]["StringValue"] == "600"

    @mark.asyncio
    async def test_enqueue_raises_on_excessive_delay(self) -> None:
        """Test enqueue() raises ValueError for delay > 900 seconds."""
        # Arrange
        driver = SQSDriver()
        driver.client = AsyncMock()
        driver._queue_urls = {"test_queue": "http://queue_url"}

        # Act & Assert
        with raises(ValueError, match="SQS delay_seconds cannot exceed 900"):
            await driver.enqueue("test_queue", b"task_data", delay_seconds=901)

    @mark.asyncio
    async def test_enqueue_creates_queue_if_not_cached(self) -> None:
        """Test enqueue() calls _get_queue_url when queue not in cache."""
        # Arrange
        driver = SQSDriver()
        mock_client = AsyncMock()
        driver.client = mock_client
        driver._queue_urls = {}

        mock_client.get_queue_url = AsyncMock(return_value={"QueueUrl": "http://queue_url"})

        # Act
        await driver.enqueue("new_queue", b"task_data")

        # Assert
        mock_client.get_queue_url.assert_called_once_with(QueueName="new_queue")
        assert driver._queue_urls["new_queue"] == "http://queue_url"


@mark.unit
class TestSQSDriverDequeue:
    """Test SQSDriver.dequeue() method."""

    @mark.asyncio
    async def test_dequeue_returns_task_data(self) -> None:
        """Test dequeue() returns decoded task data."""
        # Arrange
        driver = SQSDriver()
        mock_client = AsyncMock()
        driver.client = mock_client
        driver._queue_urls = {"test_queue": "http://queue_url"}

        mock_client.receive_message = AsyncMock(
            return_value={
                "Messages": [
                    {
                        "Body": b64encode(b"task_data").decode("ascii"),
                        "ReceiptHandle": "receipt_handle_123",
                        "MessageAttributes": {"visibility_timeout": {"StringValue": "300"}},
                    }
                ]
            }
        )

        # Act
        result = await driver.dequeue("test_queue", poll_seconds=0)

        # Assert
        assert result == b"task_data"
        assert driver._receipt_handles[b"task_data"] == "receipt_handle_123"
        mock_client.change_message_visibility.assert_called_once()

    @mark.asyncio
    async def test_dequeue_returns_none_when_no_messages(self) -> None:
        """Test dequeue() returns None when no messages available."""
        # Arrange
        driver = SQSDriver()
        mock_client = AsyncMock()
        driver.client = mock_client
        driver._queue_urls = {"test_queue": "http://queue_url"}

        mock_client.receive_message = AsyncMock(return_value={"Messages": []})

        # Act
        result = await driver.dequeue("test_queue", poll_seconds=0)

        # Assert
        assert result is None

    @mark.asyncio
    async def test_dequeue_with_poll_seconds(self) -> None:
        """Test dequeue() respects poll_seconds (capped at 20)."""
        # Arrange
        driver = SQSDriver()
        mock_client = AsyncMock()
        driver.client = mock_client
        driver._queue_urls = {"test_queue": "http://queue_url"}

        mock_client.receive_message = AsyncMock(return_value={"Messages": []})

        # Act
        await driver.dequeue("test_queue", poll_seconds=25)

        # Assert
        call_kwargs = mock_client.receive_message.call_args[1]
        assert call_kwargs["WaitTimeSeconds"] == 20  # Capped at 20

    @mark.asyncio
    async def test_dequeue_uses_custom_visibility_timeout(self) -> None:
        """Test dequeue() uses per-task visibility timeout from message attributes."""
        # Arrange
        driver = SQSDriver()
        mock_client = AsyncMock()
        driver.client = mock_client
        driver._queue_urls = {"test_queue": "http://queue_url"}

        mock_client.receive_message = AsyncMock(
            return_value={
                "Messages": [
                    {
                        "Body": b64encode(b"task_data").decode("ascii"),
                        "ReceiptHandle": "receipt_handle_123",
                        "MessageAttributes": {"visibility_timeout": {"StringValue": "600"}},
                    }
                ]
            }
        )

        # Act
        await driver.dequeue("test_queue")

        # Assert
        call_kwargs = mock_client.change_message_visibility.call_args[1]
        assert call_kwargs["VisibilityTimeout"] == 600

    @mark.asyncio
    async def test_dequeue_handles_missing_message_attributes(self) -> None:
        """Test dequeue() uses default visibility timeout when attributes missing."""
        # Arrange
        driver = SQSDriver()
        mock_client = AsyncMock()
        driver.client = mock_client
        driver._queue_urls = {"test_queue": "http://queue_url"}

        mock_client.receive_message = AsyncMock(
            return_value={
                "Messages": [
                    {
                        "Body": b64encode(b"task_data").decode("ascii"),
                        "ReceiptHandle": "receipt_handle_123",
                    }
                ]
            }
        )

        # Act
        await driver.dequeue("test_queue")

        # Assert
        call_kwargs = mock_client.change_message_visibility.call_args[1]
        assert call_kwargs["VisibilityTimeout"] == 3600  # Default

    @mark.asyncio
    async def test_dequeue_returns_none_when_body_is_none(self) -> None:
        """Test dequeue() returns None when message body is None."""
        # Arrange
        driver = SQSDriver()
        mock_client = AsyncMock()
        driver.client = mock_client
        driver._queue_urls = {"test_queue": "http://queue_url"}

        mock_client.receive_message = AsyncMock(
            return_value={"Messages": [{"Body": None, "ReceiptHandle": "receipt_handle_123"}]}
        )

        # Act
        result = await driver.dequeue("test_queue")

        # Assert
        assert result is None


@mark.unit
class TestSQSDriverAckNack:
    """Test SQSDriver.ack() and nack() methods."""

    @mark.asyncio
    async def test_ack_deletes_message(self) -> None:
        """Test ack() deletes message from queue."""
        # Arrange
        driver = SQSDriver()
        mock_client = AsyncMock()
        driver.client = mock_client
        driver._queue_urls = {"test_queue": "http://queue_url"}
        driver._receipt_handles = {b"receipt_handle": "sqs_receipt_handle"}

        # Act
        await driver.ack("test_queue", b"receipt_handle")

        # Assert
        mock_client.delete_message.assert_called_once_with(
            QueueUrl="http://queue_url", ReceiptHandle="sqs_receipt_handle"
        )
        assert b"receipt_handle" not in driver._receipt_handles

    @mark.asyncio
    async def test_ack_handles_missing_receipt(self) -> None:
        """Test ack() handles missing receipt handle gracefully."""
        # Arrange
        driver = SQSDriver()
        mock_client = AsyncMock()
        driver.client = mock_client
        driver._queue_urls = {"test_queue": "http://queue_url"}
        driver._receipt_handles = {}

        # Act - Should not raise
        await driver.ack("test_queue", b"unknown_receipt")

        # Assert
        mock_client.delete_message.assert_not_called()

    @mark.asyncio
    async def test_nack_changes_visibility_to_zero(self) -> None:
        """Test nack() sets visibility timeout to 0 for immediate reprocessing."""
        # Arrange
        driver = SQSDriver()
        mock_client = AsyncMock()
        driver.client = mock_client
        driver._queue_urls = {"test_queue": "http://queue_url"}
        driver._receipt_handles = {b"receipt_handle": "sqs_receipt_handle"}

        # Act
        await driver.nack("test_queue", b"receipt_handle")

        # Assert
        mock_client.change_message_visibility.assert_called_once_with(
            QueueUrl="http://queue_url",
            ReceiptHandle="sqs_receipt_handle",
            VisibilityTimeout=0,
        )
        assert b"receipt_handle" not in driver._receipt_handles

    @mark.asyncio
    async def test_nack_handles_missing_receipt(self) -> None:
        """Test nack() handles missing receipt handle gracefully."""
        # Arrange
        driver = SQSDriver()
        mock_client = AsyncMock()
        driver.client = mock_client
        driver._queue_urls = {"test_queue": "http://queue_url"}
        driver._receipt_handles = {}

        # Act - Should not raise
        await driver.nack("test_queue", b"unknown_receipt")

        # Assert
        mock_client.change_message_visibility.assert_not_called()


@mark.unit
class TestSQSDriverMarkFailed:
    """Test SQSDriver.mark_failed() method."""

    @mark.asyncio
    async def test_mark_failed_deletes_message(self) -> None:
        """Test mark_failed() deletes message from queue."""
        # Arrange
        driver = SQSDriver()
        mock_client = AsyncMock()
        driver.client = mock_client
        driver._queue_urls = {"test_queue": "http://queue_url"}
        driver._receipt_handles = {b"receipt_handle": "sqs_receipt_handle"}

        # Act
        await driver.mark_failed("test_queue", b"receipt_handle")

        # Assert
        mock_client.delete_message.assert_called_once_with(
            QueueUrl="http://queue_url", ReceiptHandle="sqs_receipt_handle"
        )
        assert b"receipt_handle" not in driver._receipt_handles


@mark.unit
class TestSQSDriverGetQueueUrl:
    """Test SQSDriver._get_queue_url() method."""

    @mark.asyncio
    async def test_get_queue_url_returns_cached(self) -> None:
        """Test _get_queue_url() returns cached URL."""
        # Arrange
        driver = SQSDriver()
        driver.client = AsyncMock()
        driver._queue_urls = {"test_queue": "http://cached_queue_url"}

        # Act
        url = await driver._get_queue_url("test_queue")

        # Assert
        assert url == "http://cached_queue_url"
        driver.client.get_queue_url.assert_not_called()

    @mark.asyncio
    async def test_get_queue_url_fetches_existing_queue(self) -> None:
        """Test _get_queue_url() fetches existing queue URL."""
        # Arrange
        driver = SQSDriver()
        mock_client = AsyncMock()
        driver.client = mock_client
        driver._queue_urls = {}

        mock_client.get_queue_url = AsyncMock(return_value={"QueueUrl": "http://queue_url"})

        # Act
        url = await driver._get_queue_url("existing_queue")

        # Assert
        assert url == "http://queue_url"
        assert driver._queue_urls["existing_queue"] == "http://queue_url"

    @mark.asyncio
    async def test_get_queue_url_creates_queue_when_not_found(self) -> None:
        """Test _get_queue_url() creates queue when it doesn't exist."""
        # Arrange
        driver = SQSDriver()
        mock_client = AsyncMock()
        driver.client = mock_client
        driver._queue_urls = {}

        # Mock get_queue_url to succeed (queue exists)
        # For creating queue test, we need to test the create path separately
        mock_client.get_queue_url = AsyncMock(return_value={"QueueUrl": "http://queue_url"})

        # Act
        url = await driver._get_queue_url("new_queue")

        # Assert
        assert url == "http://queue_url"
        mock_client.get_queue_url.assert_called_once_with(QueueName="new_queue")
        assert driver._queue_urls["new_queue"] == "http://queue_url"


@mark.unit
class TestSQSDriverGetQueueSize:
    """Test SQSDriver.get_queue_size() method."""

    @mark.asyncio
    async def test_get_queue_size_ready_only(self) -> None:
        """Test get_queue_size() returns only ready messages."""
        # Arrange
        driver = SQSDriver()
        mock_client = AsyncMock()
        driver.client = mock_client
        driver._queue_urls = {"test_queue": "http://queue_url"}

        mock_client.get_queue_attributes = AsyncMock(
            return_value={
                "Attributes": {
                    "ApproximateNumberOfMessages": "10",
                    "ApproximateNumberOfMessagesDelayed": "5",
                    "ApproximateNumberOfMessagesNotVisible": "3",
                }
            }
        )

        # Act
        size = await driver.get_queue_size(
            "test_queue", include_delayed=False, include_in_flight=False
        )

        # Assert
        assert size == 10

    @mark.asyncio
    async def test_get_queue_size_with_delayed(self) -> None:
        """Test get_queue_size() includes delayed messages."""
        # Arrange
        driver = SQSDriver()
        mock_client = AsyncMock()
        driver.client = mock_client
        driver._queue_urls = {"test_queue": "http://queue_url"}

        mock_client.get_queue_attributes = AsyncMock(
            return_value={
                "Attributes": {
                    "ApproximateNumberOfMessages": "10",
                    "ApproximateNumberOfMessagesDelayed": "5",
                    "ApproximateNumberOfMessagesNotVisible": "3",
                }
            }
        )

        # Act
        size = await driver.get_queue_size(
            "test_queue", include_delayed=True, include_in_flight=False
        )

        # Assert
        assert size == 15  # 10 + 5

    @mark.asyncio
    async def test_get_queue_size_with_in_flight(self) -> None:
        """Test get_queue_size() includes in-flight messages."""
        # Arrange
        driver = SQSDriver()
        mock_client = AsyncMock()
        driver.client = mock_client
        driver._queue_urls = {"test_queue": "http://queue_url"}

        mock_client.get_queue_attributes = AsyncMock(
            return_value={
                "Attributes": {
                    "ApproximateNumberOfMessages": "10",
                    "ApproximateNumberOfMessagesDelayed": "5",
                    "ApproximateNumberOfMessagesNotVisible": "3",
                }
            }
        )

        # Act
        size = await driver.get_queue_size(
            "test_queue", include_delayed=False, include_in_flight=True
        )

        # Assert
        assert size == 13  # 10 + 3

    @mark.asyncio
    async def test_get_queue_size_with_all(self) -> None:
        """Test get_queue_size() includes all message types."""
        # Arrange
        driver = SQSDriver()
        mock_client = AsyncMock()
        driver.client = mock_client
        driver._queue_urls = {"test_queue": "http://queue_url"}

        mock_client.get_queue_attributes = AsyncMock(
            return_value={
                "Attributes": {
                    "ApproximateNumberOfMessages": "10",
                    "ApproximateNumberOfMessagesDelayed": "5",
                    "ApproximateNumberOfMessagesNotVisible": "3",
                }
            }
        )

        # Act
        size = await driver.get_queue_size(
            "test_queue", include_delayed=True, include_in_flight=True
        )

        # Assert
        assert size == 18  # 10 + 5 + 3


@mark.unit
class TestSQSDriverGetQueueStats:
    """Test SQSDriver.get_queue_stats() method."""

    @mark.asyncio
    async def test_get_queue_stats_returns_stats(self) -> None:
        """Test get_queue_stats() returns queue statistics."""
        # Arrange
        driver = SQSDriver()
        mock_client = AsyncMock()
        driver.client = mock_client
        driver._queue_urls = {"test_queue": "http://queue_url"}

        mock_client.get_queue_attributes = AsyncMock(
            return_value={
                "Attributes": {
                    "ApproximateNumberOfMessages": "10",
                    "ApproximateNumberOfMessagesNotVisible": "3",
                }
            }
        )

        # Act
        stats = await driver.get_queue_stats("test_queue")

        # Assert
        assert stats["name"] == "test_queue"
        assert stats["depth"] == 10
        assert stats["processing"] == 3
        assert stats["completed_total"] == 0
        assert stats["failed_total"] == 0


@mark.unit
class TestSQSDriverMonitoringMethods:
    """Test SQSDriver monitoring API methods."""

    @mark.asyncio
    async def test_get_all_queue_names_with_prefix(self) -> None:
        """Test get_all_queue_names() with queue_url_prefix."""
        # Arrange
        driver = SQSDriver(queue_url_prefix="https://sqs.us-east-1.amazonaws.com/123456789012/")
        mock_client = AsyncMock()
        driver.client = mock_client

        mock_client.list_queues = AsyncMock(
            return_value={
                "QueueUrls": [
                    "https://sqs.us-east-1.amazonaws.com/123456789012/queue1",
                    "https://sqs.us-east-1.amazonaws.com/123456789012/queue2",
                ]
            }
        )

        # Act
        queues = await driver.get_all_queue_names()

        # Assert
        assert queues == ["queue1", "queue2"]

    @mark.asyncio
    async def test_get_all_queue_names_without_prefix(self) -> None:
        """Test get_all_queue_names() without queue_url_prefix."""
        # Arrange
        driver = SQSDriver()
        mock_client = AsyncMock()
        driver.client = mock_client

        mock_client.list_queues = AsyncMock(
            return_value={
                "QueueUrls": [
                    "https://sqs.us-east-1.amazonaws.com/123456789012/queue1",
                    "https://sqs.us-east-1.amazonaws.com/123456789012/queue2",
                ]
            }
        )

        # Act
        queues = await driver.get_all_queue_names()

        # Assert
        assert queues == ["queue1", "queue2"]

    @mark.asyncio
    async def test_get_all_queue_names_empty(self) -> None:
        """Test get_all_queue_names() with no queues."""
        # Arrange
        driver = SQSDriver()
        mock_client = AsyncMock()
        driver.client = mock_client

        mock_client.list_queues = AsyncMock(return_value={})

        # Act
        queues = await driver.get_all_queue_names()

        # Assert
        assert queues == []

    @mark.asyncio
    async def test_get_global_stats(self) -> None:
        """Test get_global_stats() aggregates stats across queues."""
        # Arrange
        driver = SQSDriver()
        mock_client = AsyncMock()
        driver.client = mock_client

        # Mock list_queues
        mock_client.list_queues = AsyncMock(
            return_value={
                "QueueUrls": [
                    "https://sqs.us-east-1.amazonaws.com/123456789012/queue1",
                    "https://sqs.us-east-1.amazonaws.com/123456789012/queue2",
                ]
            }
        )

        # Mock get_queue_attributes for both queues
        mock_client.get_queue_attributes = AsyncMock(
            side_effect=[
                {
                    "Attributes": {
                        "ApproximateNumberOfMessages": "10",
                        "ApproximateNumberOfMessagesNotVisible": "3",
                    }
                },
                {
                    "Attributes": {
                        "ApproximateNumberOfMessages": "5",
                        "ApproximateNumberOfMessagesNotVisible": "2",
                    }
                },
            ]
        )

        # Act
        stats = await driver.get_global_stats()

        # Assert
        assert stats["pending"] == 15  # 10 + 5
        assert stats["running"] == 5  # 3 + 2
        assert stats["failed"] == 0
        assert stats["total"] == 20  # 15 + 5

    @mark.asyncio
    async def test_get_running_tasks_returns_empty(self) -> None:
        """Test get_running_tasks() returns empty list (not supported)."""
        # Arrange
        driver = SQSDriver()
        driver.client = AsyncMock()

        # Act
        tasks = await driver.get_running_tasks()

        # Assert
        assert tasks == []

    @mark.asyncio
    async def test_get_tasks_returns_empty(self) -> None:
        """Test get_tasks() returns empty list (not supported)."""
        # Arrange
        driver = SQSDriver()
        driver.client = AsyncMock()

        # Act
        tasks, total = await driver.get_tasks()

        # Assert
        assert tasks == []
        assert total == 0

    @mark.asyncio
    async def test_get_task_by_id_returns_none(self) -> None:
        """Test get_task_by_id() returns None (not supported)."""
        # Arrange
        driver = SQSDriver()
        driver.client = AsyncMock()

        # Act
        task = await driver.get_task_by_id("task_id")

        # Assert
        assert task is None

    @mark.asyncio
    async def test_retry_task_returns_false(self) -> None:
        """Test retry_task() returns False (not supported)."""
        # Arrange
        driver = SQSDriver()
        driver.client = AsyncMock()

        # Act
        result = await driver.retry_task("task_id")

        # Assert
        assert result is False

    @mark.asyncio
    async def test_delete_task_returns_false(self) -> None:
        """Test delete_task() returns False (not supported)."""
        # Arrange
        driver = SQSDriver()
        driver.client = AsyncMock()

        # Act
        result = await driver.delete_task("task_id")

        # Assert
        assert result is False

    @mark.asyncio
    async def test_get_worker_stats_returns_empty(self) -> None:
        """Test get_worker_stats() returns empty list (not supported)."""
        # Arrange
        driver = SQSDriver()

        # Act
        stats = await driver.get_worker_stats()

        # Assert
        assert stats == []
