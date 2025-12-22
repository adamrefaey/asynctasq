"""Unit tests for TaskRepository.

Testing Strategy:
- pytest 9.0.1 with asyncio_mode="auto"
- Test repository pattern with mocked driver and serializer
- Test pagination, filtering, and CRUD operations
- Test fallback behavior for drivers without efficient lookups
"""

from unittest.mock import AsyncMock

from pytest import main, mark

from asynctasq.core.models import TaskInfo
from asynctasq.tasks.services.repository import TaskRepository


@mark.unit
class TestTaskRepository:
    """Test TaskRepository class."""

    @mark.asyncio
    async def test_get_running_tasks_calls_driver(self) -> None:
        # Arrange
        driver = AsyncMock()
        driver.get_running_tasks.return_value = [
            (b"task1_bytes", "queue1"),
            (b"task2_bytes", "queue2"),
        ]
        serializer = AsyncMock()
        repo = TaskRepository(driver, serializer)

        # Act
        result = await repo.get_running_tasks(limit=10, offset=0)

        # Assert
        driver.get_running_tasks.assert_called_once_with(limit=10, offset=0)
        assert len(result) == 2
        assert result[0] == (b"task1_bytes", "queue1")

    @mark.asyncio
    async def test_get_running_task_infos_converts_to_task_info(self) -> None:
        # Arrange
        driver = AsyncMock()
        driver.get_running_tasks.return_value = [(b"task_bytes", "queue1")]

        serializer = AsyncMock()
        task_info = TaskInfo(
            id="task-1",
            name="TestTask",
            queue="queue1",
            status="running",
            enqueued_at=None,  # type: ignore[arg-type]
        )
        serializer.to_task_info.return_value = task_info

        repo = TaskRepository(driver, serializer)

        # Act
        result = await repo.get_running_task_infos(limit=5, offset=0)

        # Assert
        assert len(result) == 1
        assert result[0] == task_info
        serializer.to_task_info.assert_called_once_with(b"task_bytes", "queue1", "running")

    @mark.asyncio
    async def test_get_tasks_with_filtering(self) -> None:
        # Arrange
        driver = AsyncMock()
        driver.get_tasks.return_value = (
            [(b"task1", "queue1", "pending"), (b"task2", "queue1", "pending")],
            2,
        )
        serializer = AsyncMock()
        repo = TaskRepository(driver, serializer)

        # Act
        result, total = await repo.get_tasks(status="pending", queue="queue1", limit=10, offset=0)

        # Assert
        driver.get_tasks.assert_called_once_with(
            status="pending", queue="queue1", limit=10, offset=0
        )
        assert len(result) == 2
        assert total == 2

    @mark.asyncio
    async def test_get_task_infos_with_pagination(self) -> None:
        # Arrange
        driver = AsyncMock()
        driver.get_tasks.return_value = (
            [(b"task1", "queue1", "completed"), (b"task2", "queue2", "completed")],
            100,  # Total count
        )

        serializer = AsyncMock()
        task_info_1 = TaskInfo(
            id="task-1",
            name="Task1",
            queue="queue1",
            status="completed",
            enqueued_at=None,  # type: ignore[arg-type]
        )
        task_info_2 = TaskInfo(
            id="task-2",
            name="Task2",
            queue="queue2",
            status="completed",
            enqueued_at=None,  # type: ignore[arg-type]
        )
        serializer.to_task_info.side_effect = [task_info_1, task_info_2]

        repo = TaskRepository(driver, serializer, scan_limit=10000)

        # Act
        result, total = await repo.get_task_infos(
            status="completed", queue=None, limit=2, offset=10
        )

        # Assert
        assert len(result) == 2
        assert total == 100
        assert result[0] == task_info_1
        assert result[1] == task_info_2

    @mark.asyncio
    async def test_find_task_with_metadata_efficient_lookup(self) -> None:
        # Arrange
        driver = AsyncMock()
        driver.get_task_by_id.return_value = b"task_bytes"
        serializer = AsyncMock()
        repo = TaskRepository(driver, serializer)

        # Act
        result = await repo._find_task_with_metadata("task-123")

        # Assert
        driver.get_task_by_id.assert_called_once_with("task-123")
        assert result == (b"task_bytes", None, None)

    @mark.asyncio
    async def test_find_task_with_metadata_scan_fallback(self) -> None:
        # Arrange
        driver = AsyncMock()
        driver.get_task_by_id.return_value = None  # Efficient lookup fails
        driver.get_tasks.return_value = (
            [
                (b"other_task", "queue1", "pending"),
                (b"target_task", "queue2", "running"),
            ],
            2,
        )

        serializer = AsyncMock()
        serializer.serializer.deserialize.side_effect = [
            {"metadata": {"task_id": "other-task"}},
            {"metadata": {"task_id": "target-123"}},
        ]

        repo = TaskRepository(driver, serializer, scan_limit=1000)

        # Act
        result = await repo._find_task_with_metadata("target-123")

        # Assert
        assert result == (b"target_task", "queue2", "running")

    @mark.asyncio
    async def test_find_task_with_metadata_scan_fallback_not_found(self) -> None:
        # Arrange
        driver = AsyncMock()
        driver.get_task_by_id.return_value = None
        driver.get_tasks.return_value = ([], 0)

        serializer = AsyncMock()
        repo = TaskRepository(driver, serializer)

        # Act
        result = await repo._find_task_with_metadata("nonexistent")

        # Assert
        assert result is None

    @mark.asyncio
    async def test_find_task_with_metadata_scan_skips_deserialization_errors(self) -> None:
        # Arrange
        driver = AsyncMock()
        driver.get_task_by_id.return_value = None
        driver.get_tasks.return_value = (
            [
                (b"corrupt_task", "queue1", "pending"),
                (b"valid_task", "queue2", "running"),
            ],
            2,
        )

        serializer = AsyncMock()
        serializer.serializer.deserialize.side_effect = [
            Exception("Corrupt data"),  # First task fails
            {"metadata": {"task_id": "found-123"}},  # Second succeeds
        ]

        repo = TaskRepository(driver, serializer)

        # Act
        result = await repo._find_task_with_metadata("found-123")

        # Assert
        assert result == (b"valid_task", "queue2", "running")

    @mark.asyncio
    async def test_extract_task_id_from_nested_format(self) -> None:
        # Arrange
        repo = TaskRepository(AsyncMock(), AsyncMock())
        task_dict = {"metadata": {"task_id": "nested-123"}}

        # Act
        result = repo._extract_task_id(task_dict)

        # Assert
        assert result == "nested-123"

    @mark.asyncio
    async def test_extract_task_id_from_flat_format(self) -> None:
        # Arrange
        repo = TaskRepository(AsyncMock(), AsyncMock())
        task_dict = {"task_id": "flat-456"}

        # Act
        result = repo._extract_task_id(task_dict)

        # Assert
        assert result == "flat-456"

    @mark.asyncio
    async def test_extract_task_id_from_flat_format_with_id_field(self) -> None:
        # Arrange
        repo = TaskRepository(AsyncMock(), AsyncMock())
        task_dict = {"id": "alt-789"}

        # Act
        result = repo._extract_task_id(task_dict)

        # Assert
        assert result == "alt-789"

    @mark.asyncio
    async def test_get_task_by_id_returns_task(self) -> None:
        # Arrange
        driver = AsyncMock()
        driver.get_task_by_id.return_value = b"task_bytes"
        serializer = AsyncMock()
        repo = TaskRepository(driver, serializer)

        # Act
        result = await repo.get_task_by_id("task-123")

        # Assert
        assert result == (b"task_bytes", None, None)

    @mark.asyncio
    async def test_get_task_by_id_returns_none_when_not_found(self) -> None:
        # Arrange
        driver = AsyncMock()
        driver.get_task_by_id.return_value = None
        driver.get_tasks.return_value = ([], 0)
        serializer = AsyncMock()
        repo = TaskRepository(driver, serializer)

        # Act
        result = await repo.get_task_by_id("nonexistent")

        # Assert
        assert result is None

    @mark.asyncio
    async def test_get_task_info_by_id_converts_to_task_info(self) -> None:
        # Arrange
        driver = AsyncMock()
        driver.get_task_by_id.return_value = b"task_bytes"

        serializer = AsyncMock()
        task_info = TaskInfo(
            id="task-123",
            name="TestTask",
            queue="default",
            status="pending",
            enqueued_at=None,  # type: ignore[arg-type]
        )
        serializer.to_task_info.return_value = task_info

        repo = TaskRepository(driver, serializer)

        # Act
        result = await repo.get_task_info_by_id("task-123")

        # Assert
        assert result == task_info
        serializer.to_task_info.assert_called_once()

    @mark.asyncio
    async def test_get_task_info_by_id_returns_none_when_not_found(self) -> None:
        # Arrange
        driver = AsyncMock()
        driver.get_task_by_id.return_value = None
        driver.get_tasks.return_value = ([], 0)
        serializer = AsyncMock()
        repo = TaskRepository(driver, serializer)

        # Act
        result = await repo.get_task_info_by_id("nonexistent")

        # Assert
        assert result is None

    @mark.asyncio
    async def test_delete_task_efficient_delete_succeeds(self) -> None:
        # Arrange
        driver = AsyncMock()
        driver.delete_task.return_value = True
        serializer = AsyncMock()
        repo = TaskRepository(driver, serializer)

        # Act
        result = await repo.delete_task("task-123")

        # Assert
        driver.delete_task.assert_called_once_with("task-123")
        assert result is True

    @mark.asyncio
    async def test_delete_task_fallback_to_scan_and_delete(self) -> None:
        # Arrange
        driver = AsyncMock()
        driver.delete_task.return_value = False  # Efficient delete fails
        driver.get_task_by_id.return_value = None
        driver.get_tasks.return_value = (
            [(b"target_task", "queue1", "pending")],
            1,
        )
        driver.delete_raw_task.return_value = True

        serializer = AsyncMock()
        serializer.serializer.deserialize.return_value = {"metadata": {"task_id": "task-123"}}

        repo = TaskRepository(driver, serializer)

        # Act
        result = await repo.delete_task("task-123")

        # Assert
        assert result is True
        driver.delete_raw_task.assert_called_once_with("queue1", b"target_task")

    @mark.asyncio
    async def test_delete_task_returns_false_when_not_found(self) -> None:
        # Arrange
        driver = AsyncMock()
        driver.delete_task.return_value = False
        driver.get_task_by_id.return_value = None
        driver.get_tasks.return_value = ([], 0)
        serializer = AsyncMock()
        repo = TaskRepository(driver, serializer)

        # Act
        result = await repo.delete_task("nonexistent")

        # Assert
        assert result is False

    @mark.asyncio
    async def test_delete_task_fallback_without_queue_name(self) -> None:
        # Arrange
        driver = AsyncMock()
        driver.delete_task.return_value = False
        driver.get_task_by_id.return_value = b"task_bytes"  # Efficient lookup but no queue
        serializer = AsyncMock()
        repo = TaskRepository(driver, serializer)

        # Act
        result = await repo.delete_task("task-123")

        # Assert (can't delete without queue_name)
        assert result is False


if __name__ == "__main__":
    main([__file__, "-s", "-m", "unit"])
