"""Unit tests for BaseDriver default method implementations."""

import pytest

from asynctasq.drivers.base_driver import BaseDriver


@pytest.mark.unit
class TestBaseDriverDefaultImplementations:
    """Test BaseDriver methods with default implementations."""

    @pytest.mark.asyncio
    async def test_retry_raw_task_default_returns_false(self) -> None:
        """Test that retry_raw_task returns False by default."""

        # Create minimal BaseDriver subclass for testing
        class TestDriver(BaseDriver):
            async def connect(self) -> None:
                pass

            async def disconnect(self) -> None:
                pass

            async def enqueue(
                self,
                queue_name: str,
                task_data: bytes,
                delay_seconds: int = 0,
                current_attempt: int = 0,
                visibility_timeout: int = 0,
            ) -> None:
                pass

            async def dequeue(self, queue_name: str, poll_seconds: int = 0) -> bytes | None:
                return None

            async def ack(self, queue_name: str, receipt_handle: bytes) -> None:
                pass

            async def nack(self, queue_name: str, receipt_handle: bytes) -> None:
                pass

            async def get_queue_size(
                self,
                queue_name: str,
                include_delayed: bool,
                include_in_flight: bool,
            ) -> int:
                return 0

            async def get_queue_stats(self, queue: str) -> dict:
                return {}

            async def get_all_queue_names(self) -> list[str]:
                return []

            async def get_global_stats(self) -> dict:
                return {}

            async def get_running_tasks(
                self, limit: int = 50, offset: int = 0
            ) -> list[tuple[bytes, str]]:
                return []

            async def get_tasks(
                self,
                status: str | None = None,
                queue: str | None = None,
                limit: int = 50,
                offset: int = 0,
            ) -> tuple[list[tuple[bytes, str, str]], int]:
                return [], 0

            async def get_task_by_id(self, task_id: str) -> bytes | None:
                return None

            async def retry_task(self, task_id: str) -> bool:
                return False

            async def delete_task(self, task_id: str) -> bool:
                return False

            async def get_worker_stats(self) -> list[dict]:
                return []

        driver = TestDriver()

        # Act
        result = await driver.retry_raw_task("default", b"task_data")

        # Assert
        assert result is False

    @pytest.mark.asyncio
    async def test_delete_raw_task_default_returns_false(self) -> None:
        """Test that delete_raw_task returns False by default."""

        class TestDriver(BaseDriver):
            async def connect(self) -> None:
                pass

            async def disconnect(self) -> None:
                pass

            async def enqueue(
                self,
                queue_name: str,
                task_data: bytes,
                delay_seconds: int = 0,
                current_attempt: int = 0,
                visibility_timeout: int = 0,
            ) -> None:
                pass

            async def dequeue(self, queue_name: str, poll_seconds: int = 0) -> bytes | None:
                return None

            async def ack(self, queue_name: str, receipt_handle: bytes) -> None:
                pass

            async def nack(self, queue_name: str, receipt_handle: bytes) -> None:
                pass

            async def get_queue_size(
                self,
                queue_name: str,
                include_delayed: bool,
                include_in_flight: bool,
            ) -> int:
                return 0

            async def get_queue_stats(self, queue: str) -> dict:
                return {}

            async def get_all_queue_names(self) -> list[str]:
                return []

            async def get_global_stats(self) -> dict:
                return {}

            async def get_running_tasks(
                self, limit: int = 50, offset: int = 0
            ) -> list[tuple[bytes, str]]:
                return []

            async def get_tasks(
                self,
                status: str | None = None,
                queue: str | None = None,
                limit: int = 50,
                offset: int = 0,
            ) -> tuple[list[tuple[bytes, str, str]], int]:
                return [], 0

            async def get_task_by_id(self, task_id: str) -> bytes | None:
                return None

            async def retry_task(self, task_id: str) -> bool:
                return False

            async def delete_task(self, task_id: str) -> bool:
                return False

            async def get_worker_stats(self) -> list[dict]:
                return []

        driver = TestDriver()

        # Act
        result = await driver.delete_raw_task("default", b"task_data")

        # Assert
        assert result is False
