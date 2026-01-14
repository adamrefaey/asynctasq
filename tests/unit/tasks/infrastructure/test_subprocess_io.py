"""Tests for subprocess I/O configuration in process pools."""

import asyncio
import sys

import pytest

from asynctasq.tasks import AsyncProcessTask, SyncProcessTask


class PrintSyncTask(SyncProcessTask):
    """Test task that prints to stdout."""

    message: str

    def execute(self) -> str:
        print(f"SYNC: {self.message}", flush=True)
        return "done"


class PrintAsyncTask(AsyncProcessTask):
    """Test task that prints to stdout from async context."""

    message: str

    async def execute(self) -> str:
        print(f"ASYNC: {self.message}", flush=True)
        await asyncio.sleep(0.01)
        return "done"


class MultiPrintTask(SyncProcessTask):
    """Test task that prints multiple lines."""

    def execute(self) -> int:
        print("Line 1", flush=True)
        print("Line 2", flush=True)
        print("Line 3", flush=True)
        return 123


class StderrTask(SyncProcessTask):
    """Test task that prints to stderr."""

    def execute(self) -> str:
        print("ERROR MESSAGE", file=sys.stderr, flush=True)
        return "done"


@pytest.mark.asyncio
async def test_sync_process_task_stdout_visible(capfd, reset_default_manager):
    """Verify print statements in SyncProcessTask appear in stdout."""
    # Use the reset_default_manager fixture instead of creating a new one
    manager = reset_default_manager
    manager.sync_max_workers = 1
    await manager.initialize()

    task = PrintSyncTask(message="Hello from sync subprocess")
    result = await task.run()

    # Capture output
    captured = capfd.readouterr()

    assert result == "done"
    assert "SYNC: Hello from sync subprocess" in captured.out


@pytest.mark.asyncio
async def test_async_process_task_stdout_visible(capfd, reset_default_manager):
    """Verify print statements in AsyncProcessTask appear in stdout."""
    # Use the reset_default_manager fixture instead of creating a new one
    manager = reset_default_manager
    manager.async_max_workers = 1
    await manager.initialize()

    task = PrintAsyncTask(message="Hello from async subprocess")
    result = await task.run()

    # Capture output
    captured = capfd.readouterr()

    assert result == "done"
    assert "ASYNC: Hello from async subprocess" in captured.out


@pytest.mark.asyncio
async def test_multiple_print_statements_visible(capfd, reset_default_manager):
    """Verify multiple print statements from subprocess are visible."""
    # Use the reset_default_manager fixture instead of creating a new one
    manager = reset_default_manager
    manager.sync_max_workers = 1
    await manager.initialize()

    task = MultiPrintTask()
    result = await task.run()

    captured = capfd.readouterr()

    assert result == 123
    assert "Line 1" in captured.out
    assert "Line 2" in captured.out
    assert "Line 3" in captured.out


@pytest.mark.asyncio
async def test_stderr_also_visible(capfd, reset_default_manager):
    """Verify stderr output from subprocess is visible."""
    # Use the reset_default_manager fixture instead of creating a new one
    manager = reset_default_manager
    manager.sync_max_workers = 1
    await manager.initialize()

    task = StderrTask()
    result = await task.run()

    captured = capfd.readouterr()

    assert result == "done"
    assert "ERROR MESSAGE" in captured.err
