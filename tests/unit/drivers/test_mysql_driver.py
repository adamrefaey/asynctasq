"""Unit tests for MySQLDriver.

Testing Strategy:
- pytest 9.0.1 with asyncio_mode="auto" (no decorators needed)
- AAA pattern (Arrange, Act, Assert)
- Use mocks to test MySQLDriver without requiring real MySQL
- Test error handling paths and rollback scenarios
- Achieve 100% code coverage when combined with integration tests
"""

from unittest.mock import AsyncMock, MagicMock, patch

from pytest import mark, raises

from asynctasq.drivers.mysql_driver import MySQLDriver


@mark.unit
class TestMySQLDriverErrorHandling:
    """Test MySQLDriver error handling and rollback scenarios."""

    @mark.asyncio
    async def test_enqueue_rollback_on_exception(self) -> None:
        """Test that enqueue() rolls back transaction on exception."""
        # Arrange
        driver = MySQLDriver(dsn="mysql://user:pass@localhost:3306/dbname")
        mock_pool = AsyncMock()
        mock_conn = AsyncMock()
        mock_cursor = AsyncMock()

        # Setup async context manager for pool.acquire()
        mock_acquire_context = MagicMock()
        mock_acquire_context.__aenter__ = AsyncMock(return_value=mock_conn)
        mock_acquire_context.__aexit__ = AsyncMock(return_value=None)
        mock_pool.acquire = MagicMock(return_value=mock_acquire_context)

        # Setup async context manager for conn.cursor()
        mock_cursor_context = MagicMock()
        mock_cursor_context.__aenter__ = AsyncMock(return_value=mock_cursor)
        mock_cursor_context.__aexit__ = AsyncMock(return_value=None)
        mock_conn.cursor = MagicMock(return_value=mock_cursor_context)

        driver.pool = mock_pool
        mock_cursor.execute.side_effect = Exception("Database error")

        # Act & Assert
        with raises(Exception, match="Database error"):
            await driver.enqueue("test_queue", b"task_data", delay_seconds=0)

        # Assert - rollback was called
        mock_conn.rollback.assert_called_once()
        mock_conn.commit.assert_not_called()

    @mark.asyncio
    async def test_dequeue_rollback_on_exception(self) -> None:
        """Test that dequeue() rolls back transaction on exception."""
        # Arrange
        driver = MySQLDriver(dsn="mysql://user:pass@localhost:3306/dbname")
        mock_pool = AsyncMock()
        mock_conn = AsyncMock()
        mock_cursor = AsyncMock()

        # Setup async context manager for pool.acquire()
        mock_acquire_context = MagicMock()
        mock_acquire_context.__aenter__ = AsyncMock(return_value=mock_conn)
        mock_acquire_context.__aexit__ = AsyncMock(return_value=None)
        mock_pool.acquire = MagicMock(return_value=mock_acquire_context)

        # Setup async context manager for conn.cursor()
        mock_cursor_context = MagicMock()
        mock_cursor_context.__aenter__ = AsyncMock(return_value=mock_cursor)
        mock_cursor_context.__aexit__ = AsyncMock(return_value=None)
        mock_conn.cursor = MagicMock(return_value=mock_cursor_context)

        driver.pool = mock_pool
        mock_cursor.execute.side_effect = Exception("Database error")

        # Act & Assert
        with raises(Exception, match="Database error"):
            await driver.dequeue("test_queue", poll_seconds=0)

        # Assert - rollback was called
        mock_conn.rollback.assert_called_once()

    @mark.asyncio
    async def test_dequeue_rollback_when_no_task_found(self) -> None:
        """Test that dequeue() rolls back when no task is found."""
        # Arrange
        driver = MySQLDriver(dsn="mysql://user:pass@localhost:3306/dbname")
        mock_pool = AsyncMock()
        mock_conn = AsyncMock()
        mock_cursor = AsyncMock()

        # Setup async context manager for pool.acquire()
        mock_acquire_context = MagicMock()
        mock_acquire_context.__aenter__ = AsyncMock(return_value=mock_conn)
        mock_acquire_context.__aexit__ = AsyncMock(return_value=None)
        mock_pool.acquire = MagicMock(return_value=mock_acquire_context)

        # Setup async context manager for conn.cursor()
        mock_cursor_context = MagicMock()
        mock_cursor_context.__aenter__ = AsyncMock(return_value=mock_cursor)
        mock_cursor_context.__aexit__ = AsyncMock(return_value=None)
        mock_conn.cursor = MagicMock(return_value=mock_cursor_context)

        driver.pool = mock_pool
        mock_cursor.fetchone.return_value = None  # No task found

        # Act
        result = await driver.dequeue("test_queue", poll_seconds=0)

        # Assert
        assert result is None
        mock_conn.rollback.assert_called_once()

    @mark.asyncio
    async def test_ack_rollback_on_exception(self) -> None:
        """Test that ack() rolls back transaction on exception."""
        # Arrange
        driver = MySQLDriver(dsn="mysql://user:pass@localhost:3306/dbname")
        driver._receipt_handles = {b"receipt_handle": 123}

        mock_pool = AsyncMock()
        mock_conn = AsyncMock()
        mock_cursor = AsyncMock()

        # Setup async context manager for pool.acquire()
        mock_acquire_context = MagicMock()
        mock_acquire_context.__aenter__ = AsyncMock(return_value=mock_conn)
        mock_acquire_context.__aexit__ = AsyncMock(return_value=None)
        mock_pool.acquire = MagicMock(return_value=mock_acquire_context)

        # Setup async context manager for conn.cursor()
        mock_cursor_context = MagicMock()
        mock_cursor_context.__aenter__ = AsyncMock(return_value=mock_cursor)
        mock_cursor_context.__aexit__ = AsyncMock(return_value=None)
        mock_conn.cursor = MagicMock(return_value=mock_cursor_context)

        driver.pool = mock_pool
        mock_cursor.execute.side_effect = Exception("Database error")

        # Act & Assert
        with raises(Exception, match="Database error"):
            await driver.ack("test_queue", b"receipt_handle")

        # Assert - rollback was called
        mock_conn.rollback.assert_called_once()
        mock_conn.commit.assert_not_called()

    @mark.asyncio
    async def test_nack_rollback_on_exception(self) -> None:
        """Test that nack() rolls back transaction on exception."""
        # Arrange
        driver = MySQLDriver(dsn="mysql://user:pass@localhost:3306/dbname")
        driver._receipt_handles = {b"receipt_handle": 123}

        mock_pool = AsyncMock()
        mock_conn = AsyncMock()
        mock_cursor = AsyncMock()

        # Setup async context manager for pool.acquire()
        mock_acquire_context = MagicMock()
        mock_acquire_context.__aenter__ = AsyncMock(return_value=mock_conn)
        mock_acquire_context.__aexit__ = AsyncMock(return_value=None)
        mock_pool.acquire = MagicMock(return_value=mock_acquire_context)

        # Setup async context manager for conn.cursor()
        mock_cursor_context = MagicMock()
        mock_cursor_context.__aenter__ = AsyncMock(return_value=mock_cursor)
        mock_cursor_context.__aexit__ = AsyncMock(return_value=None)
        mock_conn.cursor = MagicMock(return_value=mock_cursor_context)

        driver.pool = mock_pool

        # First execute (SELECT) succeeds, fetchone returns data, second execute (UPDATE) fails
        mock_cursor.fetchone.return_value = (
            1,
            3,
            "test_queue",
            b"payload",
        )  # current_attempt, max_attempts, queue_name, payload

        # Use side_effect to make first execute succeed, second fail
        execute_call_count = 0

        async def execute_side_effect(*args, **kwargs):
            nonlocal execute_call_count
            execute_call_count += 1
            if execute_call_count == 1:
                return None  # SELECT succeeds
            else:
                raise Exception("Database error")  # UPDATE fails

        mock_cursor.execute.side_effect = execute_side_effect

        # Act & Assert
        with raises(Exception, match="Database error"):
            await driver.nack("test_queue", b"receipt_handle")

        # Assert - rollback was called
        mock_conn.rollback.assert_called_once()
        mock_conn.commit.assert_not_called()

    # Note: Line 279 in dequeue() is defensive code that's unreachable in normal execution.
    # If poll_seconds > 0, deadline is always set. The else branch at line 279 is defensive
    # code that would require complex bytecode manipulation to test, which isn't practical.
    # This line can be marked with `# pragma: no cover` if desired, or we accept ~99.5% coverage.


@mark.unit
class TestMySQLDriverConnection:
    """Test MySQLDriver connection management."""

    @mark.asyncio
    @patch("asynctasq.drivers.mysql_driver.create_pool", new_callable=AsyncMock)
    async def test_connect_initializes_pool(self, mock_create_pool: AsyncMock) -> None:
        """Test that connect() initializes the connection pool."""
        mock_pool = AsyncMock()
        mock_create_pool.return_value = mock_pool

        driver = MySQLDriver(dsn="mysql://user:pass@localhost:3306/dbname")
        await driver.connect()

        mock_create_pool.assert_called_once_with(
            host="localhost",
            port=3306,
            user="user",
            password="pass",
            db="dbname",
            minsize=10,
            maxsize=10,
        )
        assert driver.pool is mock_pool

    @mark.asyncio
    async def test_connect_skips_if_already_connected(self) -> None:
        """Test that connect() skips initialization if pool already exists."""
        driver = MySQLDriver(dsn="mysql://user:pass@localhost:3306/dbname")
        existing_pool = AsyncMock()
        driver.pool = existing_pool

        await driver.connect()

        # Pool should remain unchanged
        assert driver.pool is existing_pool

    @mark.asyncio
    async def test_disconnect_closes_pool_and_clears_handles(self) -> None:
        """Test that disconnect() closes pool and clears receipt handles."""
        driver = MySQLDriver(dsn="mysql://user:pass@localhost:3306/dbname")
        mock_pool = AsyncMock()
        driver.pool = mock_pool
        driver._receipt_handles = {b"handle": 123}

        await driver.disconnect()

        mock_pool.close.assert_called_once()
        assert driver.pool is None
        assert driver._receipt_handles == {}

    @mark.asyncio
    async def test_disconnect_handles_none_pool(self) -> None:
        """Test that disconnect() handles None pool gracefully."""
        driver = MySQLDriver(dsn="mysql://user:pass@localhost:3306/dbname")

        # Should not raise exception
        await driver.disconnect()

        assert driver.pool is None

    @mark.asyncio
    async def test_init_schema_creates_tables(self) -> None:
        """Test that init_schema() creates queue and dead-letter tables."""
        driver = MySQLDriver(dsn="mysql://user:pass@localhost:3306/dbname")
        mock_pool = AsyncMock()
        mock_conn = AsyncMock()
        mock_cursor = AsyncMock()

        # Setup async context managers
        mock_acquire_context = MagicMock()
        mock_acquire_context.__aenter__ = AsyncMock(return_value=mock_conn)
        mock_acquire_context.__aexit__ = AsyncMock(return_value=None)
        mock_pool.acquire = MagicMock(return_value=mock_acquire_context)

        mock_cursor_context = MagicMock()
        mock_cursor_context.__aenter__ = AsyncMock(return_value=mock_cursor)
        mock_cursor_context.__aexit__ = AsyncMock(return_value=None)
        mock_conn.cursor = MagicMock(return_value=mock_cursor_context)

        driver.pool = mock_pool

        await driver.init_schema()

        # Should execute CREATE TABLE statements
        assert mock_cursor.execute.call_count == 2  # queue table + dead letter table


@mark.unit
class TestMySQLDriverEnqueueDequeue:
    """Test MySQLDriver enqueue and dequeue operations."""

    @mark.asyncio
    async def test_enqueue_immediate_task(self) -> None:
        """Test enqueue() with immediate task (delay_seconds=0)."""
        driver = MySQLDriver(dsn="mysql://user:pass@localhost:3306/dbname")
        mock_pool = AsyncMock()
        mock_conn = AsyncMock()
        mock_cursor = AsyncMock()

        # Setup async context managers
        mock_acquire_context = MagicMock()
        mock_acquire_context.__aenter__ = AsyncMock(return_value=mock_conn)
        mock_acquire_context.__aexit__ = AsyncMock(return_value=None)
        mock_pool.acquire = MagicMock(return_value=mock_acquire_context)

        mock_cursor_context = MagicMock()
        mock_cursor_context.__aenter__ = AsyncMock(return_value=mock_cursor)
        mock_cursor_context.__aexit__ = AsyncMock(return_value=None)
        mock_conn.cursor = MagicMock(return_value=mock_cursor_context)

        driver.pool = mock_pool

        await driver.enqueue("test_queue", b"task_data", delay_seconds=0)

        # Should execute INSERT query
        mock_cursor.execute.assert_called_once()
        args = mock_cursor.execute.call_args[0]
        assert "INSERT INTO task_queue" in args[0]
        assert args[1] == (
            "test_queue",
            b"task_data",
            0,
            0,
            3,
        )  # queue_name, payload, delay, current_attempt, max_attempts
        mock_conn.commit.assert_called_once()

    @mark.asyncio
    async def test_enqueue_delayed_task(self) -> None:
        """Test enqueue() with delayed task."""
        driver = MySQLDriver(dsn="mysql://user:pass@localhost:3306/dbname")
        mock_pool = AsyncMock()
        mock_conn = AsyncMock()
        mock_cursor = AsyncMock()

        # Setup async context managers
        mock_acquire_context = MagicMock()
        mock_acquire_context.__aenter__ = AsyncMock(return_value=mock_conn)
        mock_acquire_context.__aexit__ = AsyncMock(return_value=None)
        mock_pool.acquire = MagicMock(return_value=mock_acquire_context)

        mock_cursor_context = MagicMock()
        mock_cursor_context.__aenter__ = AsyncMock(return_value=mock_cursor)
        mock_cursor_context.__aexit__ = AsyncMock(return_value=None)
        mock_conn.cursor = MagicMock(return_value=mock_cursor_context)

        driver.pool = mock_pool

        await driver.enqueue("test_queue", b"task_data", delay_seconds=60)

        # Should execute INSERT query with delay
        mock_cursor.execute.assert_called_once()
        args = mock_cursor.execute.call_args[0]
        assert "DATE_ADD(NOW(6), INTERVAL %s SECOND)" in args[0]
        assert args[1] == ("test_queue", b"task_data", 60, 0, 3)

    @mark.asyncio
    @patch("asynctasq.drivers.mysql_driver.create_pool", new_callable=AsyncMock)
    async def test_enqueue_raises_when_no_pool(self, mock_create_pool: AsyncMock) -> None:
        """Test that enqueue() raises when connection fails."""
        mock_create_pool.side_effect = Exception("Connection failed")
        driver = MySQLDriver(dsn="mysql://user:pass@localhost:3306/dbname")

        with raises(Exception, match="Connection failed"):
            await driver.enqueue("test_queue", b"task_data")

    @mark.asyncio
    async def test_dequeue_returns_task_data(self) -> None:
        """Test dequeue() returns task data when available."""
        driver = MySQLDriver(dsn="mysql://user:pass@localhost:3306/dbname")
        mock_pool = AsyncMock()
        mock_conn = AsyncMock()
        mock_cursor = AsyncMock()

        # Setup async context managers
        mock_acquire_context = MagicMock()
        mock_acquire_context.__aenter__ = AsyncMock(return_value=mock_conn)
        mock_acquire_context.__aexit__ = AsyncMock(return_value=None)
        mock_pool.acquire = MagicMock(return_value=mock_acquire_context)

        mock_cursor_context = MagicMock()
        mock_cursor_context.__aenter__ = AsyncMock(return_value=mock_cursor)
        mock_cursor_context.__aexit__ = AsyncMock(return_value=None)
        mock_conn.cursor = MagicMock(return_value=mock_cursor_context)

        driver.pool = mock_pool

        # Mock fetchone to return task data
        mock_cursor.fetchone.return_value = (
            123,  # id
            b"task_payload",  # payload
            "test_queue",  # queue_name
            1,  # current_attempt
            3,  # max_attempts
        )

        result = await driver.dequeue("test_queue", poll_seconds=0)

        assert result == b"task_payload"
        assert driver._receipt_handles[b"task_payload"] == 123
        mock_conn.commit.assert_called_once()

    @mark.asyncio
    async def test_dequeue_returns_none_when_no_tasks(self) -> None:
        """Test dequeue() returns None when no tasks available."""
        driver = MySQLDriver(dsn="mysql://user:pass@localhost:3306/dbname")
        mock_pool = AsyncMock()
        mock_conn = AsyncMock()
        mock_cursor = AsyncMock()

        # Setup async context managers
        mock_acquire_context = MagicMock()
        mock_acquire_context.__aenter__ = AsyncMock(return_value=mock_conn)
        mock_acquire_context.__aexit__ = AsyncMock(return_value=None)
        mock_pool.acquire = MagicMock(return_value=mock_acquire_context)

        mock_cursor_context = MagicMock()
        mock_cursor_context.__aenter__ = AsyncMock(return_value=mock_cursor)
        mock_cursor_context.__aexit__ = AsyncMock(return_value=None)
        mock_conn.cursor = MagicMock(return_value=mock_cursor_context)

        driver.pool = mock_pool

        # Mock fetchone to return None (no task)
        mock_cursor.fetchone.return_value = None

        result = await driver.dequeue("test_queue", poll_seconds=0)

        assert result is None
        mock_conn.rollback.assert_called_once()

    @mark.asyncio
    async def test_dequeue_with_polling(self) -> None:
        """Test dequeue() with polling enabled."""
        driver = MySQLDriver(dsn="mysql://user:pass@localhost:3306/dbname")
        mock_pool = AsyncMock()
        mock_conn = AsyncMock()
        mock_cursor = AsyncMock()

        # Setup async context managers
        mock_acquire_context = MagicMock()
        mock_acquire_context.__aenter__ = AsyncMock(return_value=mock_conn)
        mock_acquire_context.__aexit__ = AsyncMock(return_value=None)
        mock_pool.acquire = MagicMock(return_value=mock_acquire_context)

        mock_cursor_context = MagicMock()
        mock_cursor_context.__aenter__ = AsyncMock(return_value=mock_cursor)
        mock_cursor_context.__aexit__ = AsyncMock(return_value=None)
        mock_conn.cursor = MagicMock(return_value=mock_cursor_context)

        driver.pool = mock_pool

        # Mock fetchone to return task data on second call
        mock_cursor.fetchone.side_effect = [
            None,
            (
                123,  # id
                b"task_payload",  # payload
                "test_queue",  # queue_name
                1,  # current_attempt
                3,  # max_attempts
            ),
        ]

        with patch("asyncio.sleep", new_callable=AsyncMock) as mock_sleep:
            result = await driver.dequeue("test_queue", poll_seconds=1)

            assert result == b"task_payload"
            mock_sleep.assert_called_once_with(0.2)  # 200ms interval

    @mark.asyncio
    @patch("asynctasq.drivers.mysql_driver.create_pool", new_callable=AsyncMock)
    async def test_dequeue_raises_when_no_pool(self, mock_create_pool: AsyncMock) -> None:
        """Test that dequeue() raises when connection fails."""
        mock_create_pool.side_effect = Exception("Connection failed")
        driver = MySQLDriver(dsn="mysql://user:pass@localhost:3306/dbname")

        with raises(Exception, match="Connection failed"):
            await driver.dequeue("test_queue")

    @mark.asyncio
    async def test_ack_deletes_completed_task(self) -> None:
        """Test ack() deletes task when keep_completed_tasks=False."""
        driver = MySQLDriver(dsn="mysql://user:pass@localhost:3306/dbname")
        driver._receipt_handles = {b"receipt_handle": 123}
        mock_pool = AsyncMock()
        mock_conn = AsyncMock()
        mock_cursor = AsyncMock()

        # Setup async context managers
        mock_acquire_context = MagicMock()
        mock_acquire_context.__aenter__ = AsyncMock(return_value=mock_conn)
        mock_acquire_context.__aexit__ = AsyncMock(return_value=None)
        mock_pool.acquire = MagicMock(return_value=mock_acquire_context)

        mock_cursor_context = MagicMock()
        mock_cursor_context.__aenter__ = AsyncMock(return_value=mock_cursor)
        mock_cursor_context.__aexit__ = AsyncMock(return_value=None)
        mock_conn.cursor = MagicMock(return_value=mock_cursor_context)

        driver.pool = mock_pool

        await driver.ack("test_queue", b"receipt_handle")

        # Should execute DELETE query
        mock_cursor.execute.assert_called_once()
        args = mock_cursor.execute.call_args[0]
        assert "DELETE FROM task_queue" in args[0]
        assert args[1] == (123,)  # task_id
        mock_conn.commit.assert_called_once()
        assert b"receipt_handle" not in driver._receipt_handles

    @mark.asyncio
    async def test_ack_marks_completed_when_keep_tasks_true(self) -> None:
        """Test ack() marks task as completed when keep_completed_tasks=True."""
        driver = MySQLDriver(
            dsn="mysql://user:pass@localhost:3306/dbname", keep_completed_tasks=True
        )
        driver._receipt_handles = {b"receipt_handle": 123}
        mock_pool = AsyncMock()
        mock_conn = AsyncMock()
        mock_cursor = AsyncMock()

        # Setup async context managers
        mock_acquire_context = MagicMock()
        mock_acquire_context.__aenter__ = AsyncMock(return_value=mock_conn)
        mock_acquire_context.__aexit__ = AsyncMock(return_value=None)
        mock_pool.acquire = MagicMock(return_value=mock_acquire_context)

        mock_cursor_context = MagicMock()
        mock_cursor_context.__aenter__ = AsyncMock(return_value=mock_cursor)
        mock_cursor_context.__aexit__ = AsyncMock(return_value=None)
        mock_conn.cursor = MagicMock(return_value=mock_cursor_context)

        driver.pool = mock_pool

        await driver.ack("test_queue", b"receipt_handle")

        # Check that pool.acquire was called
        mock_pool.acquire.assert_called_once()

        # Should execute UPDATE query to set status to 'completed'
        mock_cursor.execute.assert_called_once()
        args = mock_cursor.execute.call_args[0]
        assert "UPDATE task_queue SET status = 'completed'" in args[0]
        assert args[1] == (123,)  # task_id

    @mark.asyncio
    async def test_ack_ignores_unknown_receipt_handle(self) -> None:
        """Test ack() ignores unknown receipt handles."""
        driver = MySQLDriver(dsn="mysql://user:pass@localhost:3306/dbname")
        driver.pool = AsyncMock()  # Prevent connect() call

        # Should not raise exception
        await driver.ack("test_queue", b"unknown_handle")

    @mark.asyncio
    @patch("asynctasq.drivers.mysql_driver.create_pool", new_callable=AsyncMock)
    async def test_ack_raises_when_no_pool(self, mock_create_pool: AsyncMock) -> None:
        """Test that ack() raises when connection fails."""
        mock_create_pool.side_effect = Exception("Connection failed")
        driver = MySQLDriver(dsn="mysql://user:pass@localhost:3306/dbname")
        driver._receipt_handles = {b"receipt_handle": 123}

        with raises(Exception, match="Connection failed"):
            await driver.ack("test_queue", b"receipt_handle")

    @mark.asyncio
    async def test_nack_retries_task(self) -> None:
        """Test nack() retries task when attempts < max_attempts."""
        driver = MySQLDriver(dsn="mysql://user:pass@localhost:3306/dbname")
        driver._receipt_handles = {b"receipt_handle": 123}
        mock_pool = AsyncMock()
        mock_conn = AsyncMock()
        mock_cursor = AsyncMock()

        # Setup async context managers
        mock_acquire_context = MagicMock()
        mock_acquire_context.__aenter__ = AsyncMock(return_value=mock_conn)
        mock_acquire_context.__aexit__ = AsyncMock(return_value=None)
        mock_pool.acquire = MagicMock(return_value=mock_acquire_context)

        mock_cursor_context = MagicMock()
        mock_cursor_context.__aenter__ = AsyncMock(return_value=mock_cursor)
        mock_cursor_context.__aexit__ = AsyncMock(return_value=None)
        mock_conn.cursor = MagicMock(return_value=mock_cursor_context)

        driver.pool = mock_pool

        # Mock SELECT to return task data with current_attempt=1, max_attempts=3
        mock_cursor.fetchone.return_value = (
            1,  # current_attempt
            3,  # max_attempts
            "test_queue",  # queue_name
            b"task_payload",  # payload
        )

        await driver.nack("test_queue", b"receipt_handle")

        # Should execute SELECT then UPDATE for retry
        assert mock_cursor.execute.call_count == 2
        mock_conn.commit.assert_called_once()
        assert b"receipt_handle" not in driver._receipt_handles

    @mark.asyncio
    async def test_nack_moves_to_dead_letter_when_max_attempts_reached(self) -> None:
        """Test nack() moves task to dead letter queue when max attempts reached."""
        driver = MySQLDriver(dsn="mysql://user:pass@localhost:3306/dbname")
        driver._receipt_handles = {b"receipt_handle": 123}
        mock_pool = AsyncMock()
        mock_conn = AsyncMock()
        mock_cursor = AsyncMock()

        # Setup async context managers
        mock_acquire_context = MagicMock()
        mock_acquire_context.__aenter__ = AsyncMock(return_value=mock_conn)
        mock_acquire_context.__aexit__ = AsyncMock(return_value=None)
        mock_pool.acquire = MagicMock(return_value=mock_acquire_context)

        mock_cursor_context = MagicMock()
        mock_cursor_context.__aenter__ = AsyncMock(return_value=mock_cursor)
        mock_cursor_context.__aexit__ = AsyncMock(return_value=None)
        mock_conn.cursor = MagicMock(return_value=mock_cursor_context)

        driver.pool = mock_pool

        # Mock SELECT to return task data with current_attempt=3, max_attempts=3
        mock_cursor.fetchone.return_value = (
            3,  # current_attempt
            3,  # max_attempts
            "test_queue",  # queue_name
            b"task_payload",  # payload
        )

        await driver.nack("test_queue", b"receipt_handle")

        # Should execute SELECT, INSERT to dead_letter, DELETE from queue
        assert mock_cursor.execute.call_count == 3
        mock_conn.commit.assert_called_once()
        assert b"receipt_handle" not in driver._receipt_handles

    @mark.asyncio
    async def test_nack_ignores_unknown_receipt_handle(self) -> None:
        """Test nack() ignores unknown receipt handles."""
        driver = MySQLDriver(dsn="mysql://user:pass@localhost:3306/dbname")
        driver.pool = AsyncMock()  # Prevent connect() call

        # Should not raise exception
        await driver.nack("test_queue", b"unknown_handle")

    @mark.asyncio
    @patch("asynctasq.drivers.mysql_driver.create_pool", new_callable=AsyncMock)
    async def test_nack_raises_when_no_pool(self, mock_create_pool: AsyncMock) -> None:
        """Test that nack() raises when connection fails."""
        mock_create_pool.side_effect = Exception("Connection failed")
        driver = MySQLDriver(dsn="mysql://user:pass@localhost:3306/dbname")
        driver._receipt_handles = {b"receipt_handle": 123}

        with raises(Exception, match="Connection failed"):
            await driver.nack("test_queue", b"receipt_handle")

    @mark.asyncio
    async def test_mark_failed_moves_to_dead_letter(self) -> None:
        """Test mark_failed() moves task to dead letter queue."""
        driver = MySQLDriver(dsn="mysql://user:pass@localhost:3306/dbname")
        driver._receipt_handles = {b"receipt_handle": 123}
        mock_pool = AsyncMock()
        mock_conn = AsyncMock()
        mock_cursor = AsyncMock()

        # Setup async context managers
        mock_acquire_context = MagicMock()
        mock_acquire_context.__aenter__ = AsyncMock(return_value=mock_conn)
        mock_acquire_context.__aexit__ = AsyncMock(return_value=None)
        mock_pool.acquire = MagicMock(return_value=mock_acquire_context)

        mock_cursor_context = MagicMock()
        mock_cursor_context.__aenter__ = AsyncMock(return_value=mock_cursor)
        mock_cursor_context.__aexit__ = AsyncMock(return_value=None)
        mock_conn.cursor = MagicMock(return_value=mock_cursor_context)

        driver.pool = mock_pool

        # Mock SELECT to return task data
        mock_cursor.fetchone.return_value = (
            "test_queue",  # queue_name
            b"task_payload",  # payload
            1,  # current_attempt
        )

        await driver.mark_failed("test_queue", b"receipt_handle")

        # Should execute SELECT, INSERT to dead_letter, DELETE from queue
        assert mock_cursor.execute.call_count == 3
        mock_conn.commit.assert_called_once()
        assert b"receipt_handle" not in driver._receipt_handles

    @mark.asyncio
    async def test_mark_failed_ignores_unknown_receipt_handle(self) -> None:
        """Test mark_failed() ignores unknown receipt handles."""
        driver = MySQLDriver(dsn="mysql://user:pass@localhost:3306/dbname")
        driver.pool = AsyncMock()  # Prevent connect() call

        # Should not raise exception
        await driver.mark_failed("test_queue", b"unknown_handle")

    @mark.asyncio
    @patch("asynctasq.drivers.mysql_driver.create_pool", new_callable=AsyncMock)
    async def test_mark_failed_raises_when_no_pool(self, mock_create_pool: AsyncMock) -> None:
        """Test that mark_failed() raises when connection fails."""
        mock_create_pool.side_effect = Exception("Connection failed")
        driver = MySQLDriver(dsn="mysql://user:pass@localhost:3306/dbname")
        driver._receipt_handles = {b"receipt_handle": 123}

        with raises(Exception, match="Connection failed"):
            await driver.mark_failed("test_queue", b"receipt_handle")


@mark.unit
class TestMySQLDriverStatsAndManagement:
    @mark.asyncio
    async def test_get_queue_stats_and_global(self) -> None:
        driver = MySQLDriver(dsn="mysql://user:pass@localhost:3306/dbname")
        mock_pool = AsyncMock()
        mock_conn = AsyncMock()
        mock_cursor = AsyncMock()

        mock_acquire_context = MagicMock()
        mock_acquire_context.__aenter__ = AsyncMock(return_value=mock_conn)
        mock_acquire_context.__aexit__ = AsyncMock(return_value=None)
        mock_pool.acquire = MagicMock(return_value=mock_acquire_context)

        mock_cursor_context = MagicMock()
        mock_cursor_context.__aenter__ = AsyncMock(return_value=mock_cursor)
        mock_cursor_context.__aexit__ = AsyncMock(return_value=None)
        mock_conn.cursor = MagicMock(return_value=mock_cursor_context)

        # Setup fetchone return values for sequence of calls
        # get_queue_stats: depth, processing, failed
        # get_global_stats: pending, processing, failed, total
        mock_cursor.fetchone.side_effect = [(5,), (2,), (1,), (10,), (3,), (1,), (20,)]

        driver.pool = mock_pool

        qs = await driver.get_queue_stats("default")
        assert qs["name"] == "default"
        assert qs["depth"] == 5
        assert qs["processing"] == 2

        g = await driver.get_global_stats()
        assert g["pending"] == 10
        assert g["running"] == 3
        assert g["failed"] == 1
        assert g["total"] == 20

    @mark.asyncio
    async def test_get_all_queue_names_and_running_tasks(self) -> None:
        driver = MySQLDriver(dsn="mysql://user:pass@localhost:3306/dbname")
        mock_pool = AsyncMock()
        mock_conn = AsyncMock()
        mock_cursor = AsyncMock()

        mock_acquire_context = MagicMock()
        mock_acquire_context.__aenter__ = AsyncMock(return_value=mock_conn)
        mock_acquire_context.__aexit__ = AsyncMock(return_value=None)
        mock_pool.acquire = MagicMock(return_value=mock_acquire_context)

        mock_cursor_context = MagicMock()
        mock_cursor_context.__aenter__ = AsyncMock(return_value=mock_cursor)
        mock_cursor_context.__aexit__ = AsyncMock(return_value=None)
        mock_conn.cursor = MagicMock(return_value=mock_cursor_context)

        # fetchall for queue names
        mock_cursor.fetchall.side_effect = [[("q1",), ("q2",)], [(1, "q1", 1, 3, None, None)]]

        driver.pool = mock_pool
        names = await driver.get_all_queue_names()
        assert names == ["q1", "q2"]

        running = await driver.get_running_tasks(limit=1, offset=0)
        assert isinstance(running, list)
        assert len(running) == 1

    @mark.asyncio
    async def test_get_tasks_and_get_task_by_id(self) -> None:
        driver = MySQLDriver(dsn="mysql://user:pass@localhost:3306/dbname")
        mock_pool = AsyncMock()
        mock_conn = AsyncMock()
        mock_cursor = AsyncMock()

        mock_acquire_context = MagicMock()
        mock_acquire_context.__aenter__ = AsyncMock(return_value=mock_conn)
        mock_acquire_context.__aexit__ = AsyncMock(return_value=None)
        mock_pool.acquire = MagicMock(return_value=mock_acquire_context)

        mock_cursor_context = MagicMock()
        mock_cursor_context.__aenter__ = AsyncMock(return_value=mock_cursor)
        mock_cursor_context.__aexit__ = AsyncMock(return_value=None)
        mock_conn.cursor = MagicMock(return_value=mock_cursor_context)

        # rows for get_tasks (now returns payload, queue_name, status)
        mock_cursor.fetchall.side_effect = [
            [(b"task_data", "q", "pending")],
        ]
        mock_cursor.fetchone.side_effect = [(1,), (b"task_by_id_data",)]

        driver.pool = mock_pool
        tasks, total = await driver.get_tasks(status="pending", queue="q", limit=1, offset=0)
        assert total == 1
        assert len(tasks) == 1
        # Now returns list of (bytes, queue_name, status) tuples
        assert tasks[0] == (b"task_data", "q", "pending")

        # get_task_by_id (now returns just payload bytes)
        t = await driver.get_task_by_id("1")
        assert t is not None
        assert t == b"task_by_id_data"

    @mark.asyncio
    async def test_retry_and_delete_task(self) -> None:
        driver = MySQLDriver(dsn="mysql://user:pass@localhost:3306/dbname")
        mock_pool = AsyncMock()
        mock_conn = AsyncMock()
        mock_cursor = AsyncMock()

        mock_acquire_context = MagicMock()
        mock_acquire_context.__aenter__ = AsyncMock(return_value=mock_conn)
        mock_acquire_context.__aexit__ = AsyncMock(return_value=None)
        mock_pool.acquire = MagicMock(return_value=mock_acquire_context)

        mock_cursor_context = MagicMock()
        mock_cursor_context.__aenter__ = AsyncMock(return_value=mock_cursor)
        mock_cursor_context.__aexit__ = AsyncMock(return_value=None)
        mock_conn.cursor = MagicMock(return_value=mock_cursor_context)

        # retry_task: select returns one row
        mock_cursor.fetchone.side_effect = [
            ("q", b"payload", 1, 3),
        ]
        driver.pool = mock_pool
        mock_conn.begin = AsyncMock()
        mock_conn.commit = AsyncMock()
        mock_conn.rollback = AsyncMock()

        ok = await driver.retry_task("1")
        assert ok is True

        # delete_task: simulate rowcount via attribute on cursor
        def set_rowcount_zero(*a, **k):
            mock_cursor.rowcount = 0

        def set_rowcount_one(*a, **k):
            mock_cursor.rowcount = 1

        # First call: delete from queue returns 1
        mock_cursor.execute.side_effect = set_rowcount_one
        driver.pool = mock_pool
        deleted = await driver.delete_task("1")
        assert deleted is True

        # Second call: delete from queue returns 0, dlq returns 1
        mock_cursor.execute.side_effect = [set_rowcount_zero, set_rowcount_one]
        deleted = await driver.delete_task("2")
        assert deleted is True

    @mark.asyncio
    async def test_get_worker_stats_empty(self) -> None:
        driver = MySQLDriver(dsn="mysql://user:pass@localhost:3306/dbname")
        res = await driver.get_worker_stats()
        assert res == []
