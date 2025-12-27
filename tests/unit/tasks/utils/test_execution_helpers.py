"""Unit tests for execution_helpers module."""

import concurrent.futures
from unittest.mock import MagicMock, patch

import pytest

from asynctasq.tasks.utils.execution_helpers import (
    _sync_process_task_worker,
    execute_in_process_sync,
    execute_in_thread,
)


class TestExecuteInThread:
    """Test execute_in_thread function."""

    @pytest.mark.asyncio
    async def test_execute_in_thread_success(self):
        """Test successful execution in thread pool."""

        def sync_work():
            return 42

        result = await execute_in_thread(sync_work)
        assert result == 42

    @pytest.mark.asyncio
    async def test_execute_in_thread_with_exception(self):
        """Test exception propagation from thread."""

        def failing_work():
            raise ValueError("Test error")

        with pytest.raises(ValueError, match="Test error"):
            await execute_in_thread(failing_work)


class TestExecuteInProcessSync:
    """Test execute_in_process_sync function."""

    @pytest.mark.asyncio
    async def test_execute_in_process_sync_success(self):
        """Test successful execution in process pool."""

        def sync_work():
            return 42

        with patch(
            "asynctasq.tasks.infrastructure.process_pool_manager.get_default_manager"
        ) as mock_get_manager:
            mock_manager = MagicMock()
            mock_pool = MagicMock()
            mock_manager.get_sync_pool.return_value = mock_pool
            mock_get_manager.return_value = mock_manager

            # Mock pool.submit to return a Future
            future = concurrent.futures.Future()
            future.set_result(42)
            mock_pool.submit.return_value = future

            result = await execute_in_process_sync(sync_work)
            assert result == 42
            mock_pool.submit.assert_called_once_with(sync_work)

    @pytest.mark.asyncio
    async def test_execute_in_process_sync_with_exception(self):
        """Test execution in process pool that raises an exception."""

        def sync_work():
            raise ValueError("Test error")

        with patch(
            "asynctasq.tasks.infrastructure.process_pool_manager.get_default_manager"
        ) as mock_get_manager:
            mock_manager = MagicMock()
            mock_pool = MagicMock()
            mock_manager.get_sync_pool.return_value = mock_pool
            mock_get_manager.return_value = mock_manager

            # Mock pool.submit to return a Future that raises
            future = concurrent.futures.Future()
            future.set_exception(ValueError("Test error"))
            mock_pool.submit.return_value = future

            with pytest.raises(ValueError, match="Test error"):
                await execute_in_process_sync(sync_work)
            mock_pool.submit.assert_called_once_with(sync_work)


class TestSyncProcessTaskWorker:
    """Test _sync_process_task_worker function."""

    @patch("asynctasq.tasks.services.serializer.TaskSerializer")
    def test_sync_process_task_worker_success(self, mock_serializer_class):
        """Test successful execution of sync process task worker."""
        # Mock the serializer
        mock_serializer = MagicMock()
        mock_serializer_class.return_value = mock_serializer

        # Mock the task
        mock_task = MagicMock()
        mock_task.execute.return_value = "task_result"
        mock_serializer.deserialize.return_value = mock_task

        # Mock asyncio.run
        with patch("asyncio.run", return_value=mock_task) as mock_asyncio_run:
            result = _sync_process_task_worker(b"serialized_task")

            assert result == "task_result"
            mock_serializer_class.assert_called_once()
            mock_asyncio_run.assert_called_once_with(
                mock_serializer.deserialize(b"serialized_task")
            )
            mock_task.execute.assert_called_once()

    @patch("asynctasq.tasks.services.serializer.TaskSerializer")
    def test_sync_process_task_worker_exception(self, mock_serializer_class):
        """Test sync process task worker when task execution raises exception."""
        # Mock the serializer
        mock_serializer = MagicMock()
        mock_serializer_class.return_value = mock_serializer

        # Mock the task
        mock_task = MagicMock()
        mock_task.execute.side_effect = RuntimeError("Task failed")
        mock_serializer.deserialize.return_value = mock_task

        # Mock asyncio.run
        with patch("asyncio.run", return_value=mock_task) as mock_asyncio_run:
            with pytest.raises(RuntimeError, match="Task failed"):
                _sync_process_task_worker(b"serialized_task")

            mock_serializer_class.assert_called_once()
            mock_asyncio_run.assert_called_once_with(
                mock_serializer.deserialize(b"serialized_task")
            )
            mock_task.execute.assert_called_once()
