from unittest.mock import AsyncMock, MagicMock, patch

from pytest import mark

from asynctasq.drivers.postgres_driver import PostgresDriver


@mark.unit
class TestPostgresDriverConnection:
    @mark.asyncio
    @patch("asynctasq.drivers.postgres_driver.create_pool", new_callable=AsyncMock)
    async def test_connect(self, mock_create_pool: AsyncMock) -> None:
        """Test connect creates pool."""
        mock_pool = AsyncMock()
        mock_create_pool.return_value = mock_pool

        driver = PostgresDriver(dsn="postgresql://user:pass@localhost/db")
        await driver.connect()

        mock_create_pool.assert_called_once_with(
            dsn="postgresql://user:pass@localhost/db",
            min_size=10,
            max_size=10,
        )
        assert driver.pool == mock_pool

    @mark.asyncio
    async def test_disconnect(self) -> None:
        """Test disconnect closes pool."""
        driver = PostgresDriver(dsn="postgresql://user:pass@localhost/db")
        mock_pool = AsyncMock()
        driver.pool = mock_pool

        await driver.disconnect()

        mock_pool.close.assert_called_once()
        assert driver.pool is None

    @mark.asyncio
    async def test_disconnect_no_pool(self) -> None:
        """Test disconnect does nothing when pool is None."""
        driver = PostgresDriver(dsn="postgresql://user:pass@localhost/db")
        await driver.disconnect()
        # Should not raise

    @mark.asyncio
    @patch("asynctasq.drivers.postgres_driver.create_pool", new_callable=AsyncMock)
    async def test_init_schema(self, mock_create_pool: AsyncMock) -> None:
        """Test init_schema creates tables and indexes."""
        mock_pool = AsyncMock()
        mock_create_pool.return_value = mock_pool
        mock_conn = AsyncMock()
        mock_acquire_context = MagicMock()
        mock_acquire_context.__aenter__ = AsyncMock(return_value=mock_conn)
        mock_acquire_context.__aexit__ = AsyncMock(return_value=None)
        mock_pool.acquire = MagicMock(return_value=mock_acquire_context)

        driver = PostgresDriver(dsn="postgresql://user:pass@localhost/db")
        await driver.init_schema()

        # Should have called connect first
        mock_create_pool.assert_called_once()
        # Should have executed 4 SQL statements (create table, migration check, create index, create dead-letter table)
        assert mock_conn.execute.call_count == 4


@mark.unit
class TestPostgresDriverStatsAndManagement:
    @mark.asyncio
    async def test_get_queue_stats_and_global(self) -> None:
        driver = PostgresDriver(dsn="postgresql://user:pass@localhost/db")
        mock_pool = AsyncMock()
        mock_conn = AsyncMock()

        mock_acquire_context = MagicMock()
        mock_acquire_context.__aenter__ = AsyncMock(return_value=mock_conn)
        mock_acquire_context.__aexit__ = AsyncMock(return_value=None)
        mock_pool.acquire = MagicMock(return_value=mock_acquire_context)

        # transaction context manager for asyncpg (async with conn.transaction())
        tx_ctx = MagicMock()
        tx_ctx.__aenter__ = AsyncMock(return_value=None)
        tx_ctx.__aexit__ = AsyncMock(return_value=None)
        mock_conn.transaction = MagicMock(return_value=tx_ctx)

        # fetchrow side effects for get_queue_stats: depth, processing, failed
        # then for get_global_stats: pending, processing, failed, total
        mock_conn.fetchrow.side_effect = [
            {"count": 5},
            {"count": 2},
            {"count": 1},
            {"count": 10},
            {"count": 3},
            {"count": 1},
            {"count": 20},
        ]

        driver.pool = mock_pool

        qs = await driver.get_queue_stats("default")
        assert qs["name"] == "default"
        assert qs["depth"] == 5
        assert qs["processing"] == 2

        g = await driver.get_global_stats()
        assert g["pending"] == 10
        assert g["running"] == 3
        assert g["failed"] == 1

    @mark.asyncio
    async def test_get_all_queue_names_and_running_tasks(self) -> None:
        driver = PostgresDriver(dsn="postgresql://user:pass@localhost/db")
        mock_pool = AsyncMock()
        mock_conn = AsyncMock()

        mock_acquire_context = MagicMock()
        mock_acquire_context.__aenter__ = AsyncMock(return_value=mock_conn)
        mock_acquire_context.__aexit__ = AsyncMock(return_value=None)
        mock_pool.acquire = MagicMock(return_value=mock_acquire_context)

        tx_ctx = MagicMock()
        tx_ctx.__aenter__ = AsyncMock(return_value=None)
        tx_ctx.__aexit__ = AsyncMock(return_value=None)
        mock_conn.transaction = MagicMock(return_value=tx_ctx)

        # fetch for get_all_queue_names
        mock_conn.fetch.return_value = [{"queue_name": "a"}, {"queue_name": "b"}]

        # fetch for get_running_tasks (now returns payload, queue_name)
        mock_conn.fetch.side_effect = [
            [{"queue_name": "a"}, {"queue_name": "b"}],
            [
                {
                    "payload": b"task_data",
                    "queue_name": "default",
                }
            ],
        ]

        driver.pool = mock_pool

        names = await driver.get_all_queue_names()
        assert names == ["a", "b"]

        tasks = await driver.get_running_tasks()
        assert isinstance(tasks, list)
        # Now returns list of (bytes, str) tuples
        assert len(tasks) == 1
        assert tasks[0] == (b"task_data", "default")

    @mark.asyncio
    async def test_get_tasks_and_get_task_by_id(self) -> None:
        driver = PostgresDriver(dsn="postgresql://user:pass@localhost/db")
        mock_pool = AsyncMock()
        mock_conn = AsyncMock()

        mock_acquire_context = MagicMock()
        mock_acquire_context.__aenter__ = AsyncMock(return_value=mock_conn)
        mock_acquire_context.__aexit__ = AsyncMock(return_value=None)
        mock_pool.acquire = MagicMock(return_value=mock_acquire_context)

        tx_ctx = MagicMock()
        tx_ctx.__aenter__ = AsyncMock(return_value=None)
        tx_ctx.__aexit__ = AsyncMock(return_value=None)
        mock_conn.transaction = MagicMock(return_value=tx_ctx)

        # fetch for list (now returns payload, queue_name, status)
        mock_conn.fetch.return_value = [
            {
                "payload": b"task_data",
                "queue_name": "default",
                "status": "pending",
            }
        ]
        mock_conn.fetchrow.return_value = {"count": 1}

        driver.pool = mock_pool

        tasks, total = await driver.get_tasks()
        assert total == 1
        assert len(tasks) == 1
        # Now returns list of (bytes, queue_name, status) tuples
        assert tasks[0] == (b"task_data", "default", "pending")

        # get_task_by_id (now returns just payload bytes)
        mock_conn.fetchrow.return_value = {
            "payload": b"task_data_by_id",
        }
        t = await driver.get_task_by_id("1")
        assert t is not None
        assert t == b"task_data_by_id"

    @mark.asyncio
    async def test_retry_and_delete_task(self) -> None:
        driver = PostgresDriver(dsn="postgresql://user:pass@localhost/db")
        mock_pool = AsyncMock()
        mock_conn = AsyncMock()

        mock_acquire_context = MagicMock()
        mock_acquire_context.__aenter__ = AsyncMock(return_value=mock_conn)
        mock_acquire_context.__aexit__ = AsyncMock(return_value=None)
        mock_pool.acquire = MagicMock(return_value=mock_acquire_context)

        tx_ctx = MagicMock()
        tx_ctx.__aenter__ = AsyncMock(return_value=None)
        tx_ctx.__aexit__ = AsyncMock(return_value=None)
        mock_conn.transaction = MagicMock(return_value=tx_ctx)

        # retry_task: fetchrow returns dead-letter row
        mock_conn.fetchrow.side_effect = [
            {"queue_name": "default", "payload": b"p", "current_attempt": 1},
            None,
        ]

        driver.pool = mock_pool

        ok = await driver.retry_task("1")
        assert ok is True

        # delete_task: first delete returns row
        mock_conn.fetchrow.side_effect = [{"id": 1}, None]
        deleted = await driver.delete_task("1")
        assert deleted is True

    @mark.asyncio
    async def test_get_worker_stats_empty(self) -> None:
        driver = PostgresDriver(dsn="postgresql://user:pass@localhost/db")
        workers = await driver.get_worker_stats()
        assert workers == []


@mark.unit
class TestPostgresDriverAutoConnect:
    """Test auto-connect functionality when pool is None."""

    @mark.asyncio
    @patch("asynctasq.drivers.postgres_driver.create_pool", new_callable=AsyncMock)
    async def test_enqueue_auto_connects(self, mock_create_pool: AsyncMock) -> None:
        """Test enqueue calls connect when pool is None."""
        mock_pool = AsyncMock()
        mock_create_pool.return_value = mock_pool

        driver = PostgresDriver(dsn="postgresql://user:pass@localhost/db")
        await driver.enqueue("test_queue", b"test_data")

        mock_create_pool.assert_called_once_with(
            dsn="postgresql://user:pass@localhost/db",
            min_size=10,
            max_size=10,
        )
        mock_pool.execute.assert_called_once()

    @mark.asyncio
    @patch("asynctasq.drivers.postgres_driver.create_pool", new_callable=AsyncMock)
    async def test_dequeue_auto_connects(self, mock_create_pool: AsyncMock) -> None:
        """Test dequeue calls connect when pool is None."""
        mock_pool = AsyncMock()
        mock_conn = AsyncMock()
        mock_create_pool.return_value = mock_pool

        # Mock the acquire context manager
        mock_acquire_context = MagicMock()
        mock_acquire_context.__aenter__ = AsyncMock(return_value=mock_conn)
        mock_acquire_context.__aexit__ = AsyncMock(return_value=None)
        mock_pool.acquire = MagicMock(return_value=mock_acquire_context)

        # Mock transaction context manager
        tx_ctx = MagicMock()
        tx_ctx.__aenter__ = AsyncMock(return_value=None)
        tx_ctx.__aexit__ = AsyncMock(return_value=None)
        mock_conn.transaction = MagicMock(return_value=tx_ctx)

        # Mock fetchrow to return None (no tasks)
        mock_conn.fetchrow.return_value = None

        driver = PostgresDriver(dsn="postgresql://user:pass@localhost/db")
        result = await driver.dequeue("test_queue")

        mock_create_pool.assert_called_once()
        assert result is None

    @mark.asyncio
    @patch("asynctasq.drivers.postgres_driver.create_pool", new_callable=AsyncMock)
    async def test_ack_auto_connects(self, mock_create_pool: AsyncMock) -> None:
        """Test ack calls connect when pool is None."""
        mock_pool = AsyncMock()
        mock_create_pool.return_value = mock_pool

        driver = PostgresDriver(dsn="postgresql://user:pass@localhost/db")
        # Test with invalid receipt handle (should not raise)
        await driver.ack("test_queue", b"invalid")

        mock_create_pool.assert_called_once()

    @mark.asyncio
    @patch("asynctasq.drivers.postgres_driver.create_pool", new_callable=AsyncMock)
    async def test_nack_auto_connects(self, mock_create_pool: AsyncMock) -> None:
        """Test nack calls connect when pool is None."""
        mock_pool = AsyncMock()
        mock_create_pool.return_value = mock_pool

        driver = PostgresDriver(dsn="postgresql://user:pass@localhost/db")
        # Test with invalid receipt handle (should not raise)
        await driver.nack("test_queue", b"invalid")

        mock_create_pool.assert_called_once()

    @mark.asyncio
    @patch("asynctasq.drivers.postgres_driver.create_pool", new_callable=AsyncMock)
    async def test_mark_failed_auto_connects(self, mock_create_pool: AsyncMock) -> None:
        """Test mark_failed calls connect when pool is None."""
        mock_pool = AsyncMock()
        mock_create_pool.return_value = mock_pool

        driver = PostgresDriver(dsn="postgresql://user:pass@localhost/db")
        # Test with invalid receipt handle (should not raise)
        await driver.mark_failed("test_queue", b"invalid")

        mock_create_pool.assert_called_once()


@mark.unit
class TestPostgresDriverEnqueueDequeue:
    @mark.asyncio
    @patch("asynctasq.drivers.postgres_driver.create_pool", new_callable=AsyncMock)
    async def test_enqueue(self, mock_create_pool: AsyncMock) -> None:
        """Test enqueue inserts task into database."""
        mock_pool = AsyncMock()
        mock_conn = AsyncMock()
        mock_acquire_context = MagicMock()
        mock_acquire_context.__aenter__ = AsyncMock(return_value=mock_conn)
        mock_acquire_context.__aexit__ = AsyncMock(return_value=None)
        mock_pool.acquire = MagicMock(return_value=mock_acquire_context)

        driver = PostgresDriver(dsn="postgresql://user:pass@localhost/db")
        driver.pool = mock_pool
        await driver.enqueue("test_queue", b"task_data")

        mock_pool.execute.assert_called_once()
        sql, *params = mock_pool.execute.call_args[0]
        assert "INSERT INTO task_queue" in sql
        assert params[0] == "test_queue"
        assert params[1] == b"task_data"

    @mark.asyncio
    @patch("asynctasq.drivers.postgres_driver.create_pool", new_callable=AsyncMock)
    async def test_enqueue_with_delay(self, mock_create_pool: AsyncMock) -> None:
        """Test enqueue with delay sets available_at correctly."""
        mock_pool = AsyncMock()
        mock_conn = AsyncMock()
        mock_acquire_context = MagicMock()
        mock_acquire_context.__aenter__ = AsyncMock(return_value=mock_conn)
        mock_acquire_context.__aexit__ = AsyncMock(return_value=None)
        mock_pool.acquire = MagicMock(return_value=mock_acquire_context)

        driver = PostgresDriver(dsn="postgresql://user:pass@localhost/db")
        driver.pool = mock_pool
        await driver.enqueue("test_queue", b"task_data", delay_seconds=60)

        mock_pool.execute.assert_called_once()
        sql, *params = mock_pool.execute.call_args[0]
        assert "INSERT INTO task_queue" in sql
        assert params[0] == "test_queue"
        assert params[1] == b"task_data"
        # available_at should be set to NOW() + INTERVAL '60 seconds'

    @mark.asyncio
    @patch("asynctasq.drivers.postgres_driver.create_pool", new_callable=AsyncMock)
    async def test_dequeue_returns_task(self, mock_create_pool: AsyncMock) -> None:
        """Test dequeue returns available task."""
        mock_pool = AsyncMock()
        mock_create_pool.return_value = mock_pool
        mock_conn = AsyncMock()
        mock_acquire_context = MagicMock()
        mock_acquire_context.__aenter__ = AsyncMock(return_value=mock_conn)
        mock_acquire_context.__aexit__ = AsyncMock(return_value=None)
        mock_pool.acquire = MagicMock(return_value=mock_acquire_context)

        tx_ctx = MagicMock()
        tx_ctx.__aenter__ = AsyncMock(return_value=None)
        tx_ctx.__aexit__ = AsyncMock(return_value=None)
        mock_conn.transaction = MagicMock(return_value=tx_ctx)

        # Mock fetchrow to return a task
        mock_conn.fetchrow.return_value = {
            "id": 1,
            "payload": b"task_data",
            "current_attempt": 1,
            "max_attempts": 3,
            "visibility_timeout_seconds": 300,
        }

        driver = PostgresDriver(dsn="postgresql://user:pass@localhost/db")
        result = await driver.dequeue("test_queue")

        assert result == b"task_data"
        # Should have updated the task status and locked_until
        assert mock_conn.execute.call_count == 1

    @mark.asyncio
    @patch("asynctasq.drivers.postgres_driver.create_pool", new_callable=AsyncMock)
    async def test_dequeue_with_polling(self, mock_create_pool: AsyncMock) -> None:
        """Test dequeue with polling waits and retries."""

        mock_pool = AsyncMock()
        mock_create_pool.return_value = mock_pool
        mock_conn = AsyncMock()
        mock_acquire_context = MagicMock()
        mock_acquire_context.__aenter__ = AsyncMock(return_value=mock_conn)
        mock_acquire_context.__aexit__ = AsyncMock(return_value=None)
        mock_pool.acquire = MagicMock(return_value=mock_acquire_context)

        tx_ctx = MagicMock()
        tx_ctx.__aenter__ = AsyncMock(return_value=None)
        tx_ctx.__aexit__ = AsyncMock(return_value=None)
        mock_conn.transaction = MagicMock(return_value=tx_ctx)

        # First call returns None, second returns a task
        mock_conn.fetchrow.side_effect = [
            None,
            {
                "id": 1,
                "payload": b"task_data",
                "current_attempt": 1,
                "max_attempts": 3,
                "visibility_timeout_seconds": 300,
            },
        ]

        driver = PostgresDriver(dsn="postgresql://user:pass@localhost/db")
        result = await driver.dequeue("test_queue", poll_seconds=1)

        assert result == b"task_data"
        # Should have called fetchrow twice
        assert mock_conn.fetchrow.call_count == 2

    @mark.asyncio
    @patch("asynctasq.drivers.postgres_driver.create_pool", new_callable=AsyncMock)
    async def test_ack(self, mock_create_pool: AsyncMock) -> None:
        """Test ack deletes completed task."""
        mock_pool = AsyncMock()
        mock_create_pool.return_value = mock_pool
        mock_conn = AsyncMock()
        mock_acquire_context = MagicMock()
        mock_acquire_context.__aenter__ = AsyncMock(return_value=mock_conn)
        mock_acquire_context.__aexit__ = AsyncMock(return_value=None)
        mock_pool.acquire = MagicMock(return_value=mock_acquire_context)

        driver = PostgresDriver(dsn="postgresql://user:pass@localhost/db")
        driver.pool = mock_pool
        driver._receipt_handles[b"receipt"] = 1

        await driver.ack("test_queue", b"receipt")

        mock_pool.execute.assert_called_once()
        sql, *params = mock_pool.execute.call_args[0]
        assert "DELETE FROM task_queue" in sql
        assert params[0] == 1

    @mark.asyncio
    @patch("asynctasq.drivers.postgres_driver.create_pool", new_callable=AsyncMock)
    async def test_nack_retries_task(self, mock_create_pool: AsyncMock) -> None:
        """Test nack retries task with backoff."""
        mock_pool = AsyncMock()
        mock_conn = AsyncMock()
        mock_acquire_context = MagicMock()
        mock_acquire_context.__aenter__ = AsyncMock(return_value=mock_conn)
        mock_acquire_context.__aexit__ = AsyncMock(return_value=None)
        mock_pool.acquire = MagicMock(return_value=mock_acquire_context)

        # Mock transaction context manager
        tx_ctx = MagicMock()
        tx_ctx.__aenter__ = AsyncMock(return_value=None)
        tx_ctx.__aexit__ = AsyncMock(return_value=None)
        mock_conn.transaction = MagicMock(return_value=tx_ctx)

        driver = PostgresDriver(dsn="postgresql://user:pass@localhost/db")
        driver.pool = mock_pool
        driver._receipt_handles[b"receipt"] = 1

        # Mock fetchrow to return task info
        mock_conn.fetchrow.return_value = {
            "current_attempt": 1,
            "max_attempts": 3,
            "queue_name": "test_queue",
            "payload": b"task_data",
        }

        await driver.nack("test_queue", b"receipt")

        # Should have updated attempt count and available_at
        assert mock_conn.execute.call_count == 1

    @mark.asyncio
    @patch("asynctasq.drivers.postgres_driver.create_pool", new_callable=AsyncMock)
    async def test_nack_marks_failed_after_max_attempts(self, mock_create_pool: AsyncMock) -> None:
        """Test nack moves task to dead-letter after max attempts."""
        mock_pool = AsyncMock()
        mock_conn = AsyncMock()
        mock_acquire_context = MagicMock()
        mock_acquire_context.__aenter__ = AsyncMock(return_value=mock_conn)
        mock_acquire_context.__aexit__ = AsyncMock(return_value=None)
        mock_pool.acquire = MagicMock(return_value=mock_acquire_context)

        # Mock transaction context manager
        tx_ctx = MagicMock()
        tx_ctx.__aenter__ = AsyncMock(return_value=None)
        tx_ctx.__aexit__ = AsyncMock(return_value=None)
        mock_conn.transaction = MagicMock(return_value=tx_ctx)

        driver = PostgresDriver(dsn="postgresql://user:pass@localhost/db")
        driver.pool = mock_pool
        driver._receipt_handles[b"receipt"] = 1

        # Mock fetchrow to return task at max attempts
        mock_conn.fetchrow.return_value = {
            "current_attempt": 3,
            "max_attempts": 3,
            "queue_name": "test_queue",
            "payload": b"task_data",
        }

        await driver.nack("test_queue", b"receipt")

        # Should have inserted into dead_letter and deleted from queue
        assert mock_conn.execute.call_count == 2

    @mark.asyncio
    @patch("asynctasq.drivers.postgres_driver.create_pool", new_callable=AsyncMock)
    async def test_mark_failed(self, mock_create_pool: AsyncMock) -> None:
        """Test mark_failed moves task to dead-letter."""
        mock_pool = AsyncMock()
        mock_conn = AsyncMock()
        mock_acquire_context = MagicMock()
        mock_acquire_context.__aenter__ = AsyncMock(return_value=mock_conn)
        mock_acquire_context.__aexit__ = AsyncMock(return_value=None)
        mock_pool.acquire = MagicMock(return_value=mock_acquire_context)

        # Mock transaction context manager
        tx_ctx = MagicMock()
        tx_ctx.__aenter__ = AsyncMock(return_value=None)
        tx_ctx.__aexit__ = AsyncMock(return_value=None)
        mock_conn.transaction = MagicMock(return_value=tx_ctx)

        driver = PostgresDriver(dsn="postgresql://user:pass@localhost/db")
        driver.pool = mock_pool
        driver._receipt_handles[b"receipt"] = 1

        await driver.mark_failed("test_queue", b"receipt")

        # Should have inserted into dead_letter and deleted from queue
        assert mock_conn.execute.call_count == 2
