"""Tests for subprocess I/O configuration in process pools."""

import asyncio
import sys

import pytest

from asynctasq.tasks import AsyncProcessTask, SyncProcessTask
from asynctasq.tasks.infrastructure.process_pool_manager import (
    ProcessPoolManager,
    set_default_manager,
)


class PrintSyncTask(SyncProcessTask[str]):
    """Test task that prints to stdout."""

    message: str

    def execute(self) -> str:
        print(f"SYNC: {self.message}", flush=True)
        return "done"


class PrintAsyncTask(AsyncProcessTask[str]):
    """Test task that prints to stdout from async context."""

    message: str

    async def execute(self) -> str:
        print(f"ASYNC: {self.message}", flush=True)
        await asyncio.sleep(0.01)
        return "done"


class MultiPrintTask(SyncProcessTask[int]):
    """Test task that prints multiple lines."""

    def execute(self) -> int:
        print("Line 1", flush=True)
        print("Line 2", flush=True)
        print("Line 3", flush=True)
        return 123


class StderrTask(SyncProcessTask[str]):
    """Test task that prints to stderr."""

    def execute(self) -> str:
        print("ERROR MESSAGE", file=sys.stderr, flush=True)
        return "done"


@pytest.mark.asyncio
async def test_sync_process_task_stdout_visible(capfd):
    """Verify print statements in SyncProcessTask appear in stdout."""
    manager = ProcessPoolManager(sync_max_workers=1)
    await manager.initialize()
    set_default_manager(manager)

    try:
        task = PrintSyncTask(message="Hello from sync subprocess")
        result = await task.run()

        # Capture output
        captured = capfd.readouterr()

        assert result == "done"
        assert "SYNC: Hello from sync subprocess" in captured.out
    finally:
        await manager.shutdown()


@pytest.mark.asyncio
async def test_async_process_task_stdout_visible(capfd):
    """Verify print statements in AsyncProcessTask appear in stdout."""
    manager = ProcessPoolManager(async_max_workers=1)
    await manager.initialize()
    set_default_manager(manager)

    try:
        task = PrintAsyncTask(message="Hello from async subprocess")
        result = await task.run()

        # Capture output
        captured = capfd.readouterr()

        assert result == "done"
        assert "ASYNC: Hello from async subprocess" in captured.out
    finally:
        await manager.shutdown()


@pytest.mark.asyncio
async def test_multiple_print_statements_visible(capfd):
    """Verify multiple print statements from subprocess are visible."""
    manager = ProcessPoolManager(sync_max_workers=1)
    await manager.initialize()
    set_default_manager(manager)

    try:
        task = MultiPrintTask()
        result = await task.run()

        captured = capfd.readouterr()

        assert result == 123
        assert "Line 1" in captured.out
        assert "Line 2" in captured.out
        assert "Line 3" in captured.out
    finally:
        await manager.shutdown()


@pytest.mark.asyncio
async def test_stderr_also_visible(capfd):
    """Verify stderr output from subprocess is visible."""
    manager = ProcessPoolManager(sync_max_workers=1)
    await manager.initialize()
    set_default_manager(manager)

    try:
        task = StderrTask()
        result = await task.run()

        captured = capfd.readouterr()

        assert result == "done"
        assert "ERROR MESSAGE" in captured.err
    finally:
        await manager.shutdown()
