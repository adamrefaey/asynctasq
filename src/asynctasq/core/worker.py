import asyncio
from collections.abc import Sequence
from datetime import UTC, datetime
import logging
import signal
import socket
import traceback
from typing import Any
import uuid

from asynctasq.config import Config
from asynctasq.drivers.base_driver import BaseDriver
from asynctasq.drivers.retry_utils import calculate_retry_delay
from asynctasq.monitoring import EventRegistry, EventType, TaskEvent, WorkerEvent
from asynctasq.serializers import BaseSerializer, MsgpackSerializer
from asynctasq.tasks import BaseTask
from asynctasq.tasks.services.executor import TaskExecutor
from asynctasq.tasks.services.serializer import TaskSerializer

logger = logging.getLogger(__name__)


class Worker:
    """Asynchronous worker for consuming and executing tasks from queue backends.

    Continuously polls configured queues for tasks and executes them concurrently with
    respect to configured limits. Provides graceful shutdown, retry logic with exponential/
    fixed backoff, and event emission for observability.
    """

    queue_driver: BaseDriver
    queues: list[str]
    concurrency: int
    max_tasks: int | None
    serializer: BaseSerializer
    event_emitter: None
    worker_id: str
    heartbeat_interval: float
    process_pool_size: int | None
    process_pool_max_tasks_per_child: int | None

    def __init__(
        self,
        queue_driver: BaseDriver,
        queues: Sequence[str] | None = None,
        concurrency: int = 10,
        max_tasks: int | None = None,  # None = run indefinitely (production default)
        serializer: BaseSerializer | None = None,
        event_emitter: None = None,
        worker_id: str | None = None,
        heartbeat_interval: float = 60.0,
        process_pool_size: int | None = None,
        process_pool_max_tasks_per_child: int | None = None,
    ) -> None:
        self.queue_driver = queue_driver
        self.queues = list(queues) if queues else ["default"]
        self.concurrency = concurrency
        self.max_tasks = max_tasks  # None = continuous operation, N = stop after N tasks
        self.serializer = serializer or MsgpackSerializer()
        # Worker uses global event emitters via EventRegistry.emit()
        self.event_emitter = None
        self.worker_id = worker_id or f"worker-{uuid.uuid4().hex[:8]}"
        self.hostname = socket.gethostname()
        self.heartbeat_interval = heartbeat_interval
        self.process_pool_size = process_pool_size
        self.process_pool_max_tasks_per_child = process_pool_max_tasks_per_child

        self._running = False
        self._tasks: set[asyncio.Task[None]] = set()
        self._tasks_processed = 0
        self._start_time: datetime | None = None
        self._heartbeat_task: asyncio.Task[None] | None = None
        self._task_serializer = TaskSerializer(self.serializer)
        self._task_executor = TaskExecutor()

    async def start(self) -> None:
        """Initialize worker and begin processing tasks until shutdown.

        Sets up uvloop, connects to queue driver, initializes process pool if configured,
        registers signal handlers, and enters the main polling loop. Blocks until shutdown
        signal (SIGTERM/SIGINT) or max_tasks limit reached. Cleanup is always performed
        to ensure graceful shutdown.

        Raises
        ------
        Exception
            Any unhandled exception from the worker loop is propagated after cleanup
        """
        # Use uvloop as the event loop policy if available (optional)
        try:
            import uvloop

            asyncio.set_event_loop_policy(uvloop.EventLoopPolicy())
            logger.info("Using uvloop event loop policy")
        except ImportError:
            logger.info("uvloop not available, using default event loop policy")

        self._running = True
        self._start_time = datetime.now(UTC)

        # Ensure driver is connected
        await self.queue_driver.connect()

        # Initialize ProcessPoolManager if configured
        if self.process_pool_size is not None or self.process_pool_max_tasks_per_child is not None:
            from asynctasq.tasks.infrastructure.process_pool_manager import (
                ProcessPoolManager,
                set_default_manager,
            )

            logger.info(
                "Initializing ProcessPoolManager: size=%s, max_tasks_per_child=%s",
                self.process_pool_size,
                self.process_pool_max_tasks_per_child,
            )
            manager = ProcessPoolManager(
                sync_max_workers=self.process_pool_size,
                async_max_workers=self.process_pool_size,
                sync_max_tasks_per_child=self.process_pool_max_tasks_per_child,
                async_max_tasks_per_child=self.process_pool_max_tasks_per_child,
            )
            await manager.initialize()
            set_default_manager(manager)

        # Setup signal handlers
        loop = asyncio.get_running_loop()
        for sig in (signal.SIGTERM, signal.SIGINT):
            loop.add_signal_handler(sig, self._handle_shutdown)

        logger.info(
            "Worker %s starting: queues=%s, concurrency=%d",
            self.worker_id,
            self.queues,
            self.concurrency,
        )

        # Emit worker_online event via global emitters
        await EventRegistry.emit(
            WorkerEvent(
                event_type=EventType.WORKER_ONLINE,
                worker_id=self.worker_id,
                hostname=self.hostname,
                queues=tuple(self.queues),
                freq=self.heartbeat_interval,
            )
        )

        # Start heartbeat loop
        # Start heartbeat loop (will call EventRegistry.emit internally)
        self._heartbeat_task = asyncio.create_task(
            self._heartbeat_loop(), name=f"{self.worker_id}-heartbeat"
        )

        try:
            await self._run()
        finally:
            await self._cleanup()

    async def _heartbeat_loop(self) -> None:
        """Emit periodic heartbeat events for worker health monitoring.

        Sends WORKER_HEARTBEAT events at configured intervals containing worker statistics
        (active tasks, processed count, uptime). Runs as background task until shutdown.
        """
        while self._running:
            try:
                await asyncio.sleep(self.heartbeat_interval)

                if not self._running:
                    break

                uptime = (
                    int((datetime.now(UTC) - self._start_time).total_seconds())
                    if self._start_time
                    else 0
                )

                await EventRegistry.emit(
                    WorkerEvent(
                        event_type=EventType.WORKER_HEARTBEAT,
                        worker_id=self.worker_id,
                        hostname=self.hostname,
                        freq=self.heartbeat_interval,
                        active=len(self._tasks),
                        processed=self._tasks_processed,
                        queues=tuple(self.queues),
                        uptime_seconds=uptime,
                    )
                )

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.warning("Failed to send heartbeat: %s", e)

    async def _run(self) -> None:
        """Main worker polling loop - continuously fetches and processes tasks.

        Checks max_tasks limit, waits for concurrency slot if needed, fetches task from
        queues in round-robin order, spawns background task for processing. Sleeps 0.1s
        when no tasks available to prevent CPU spinning. Exits on shutdown signal or when
        max_tasks limit reached.
        """
        while self._running:
            # Check if we've reached max tasks (used for testing/batch processing)
            if self.max_tasks and self._tasks_processed >= self.max_tasks:
                logger.info(f"Reached max tasks limit: {self.max_tasks}")
                break

            # Check if we can accept more tasks
            if len(self._tasks) >= self.concurrency:
                # Wait for a task to complete
                done, pending = await asyncio.wait(self._tasks, return_when=asyncio.FIRST_COMPLETED)
                self._tasks = pending
                continue

            # Try to get a task from queues (in priority order)
            fetch_result = await self._fetch_task()
            if fetch_result is None:
                # No tasks available, sleep briefly then check again
                # This prevents CPU spinning while still being responsive
                # Note: asyncio.sleep(0) would yield to event loop without delay
                await asyncio.sleep(0.1)
                continue  # Loop continues - worker keeps checking for new tasks

            task_data, queue_name = fetch_result

            # Create asyncio task to process task
            task = asyncio.create_task(self._process_task(task_data, queue_name))
            self._tasks.add(task)
            task.add_done_callback(self._tasks.discard)

    async def _fetch_task(self) -> tuple[bytes, str] | None:
        """Fetch next available task from configured queues using round-robin polling.

        Iterates through queues in order until a task is found. Returns None if all queues
        are empty.

        Returns
        -------
        tuple[bytes, str] | None
            Tuple of (serialized_task_data, queue_name) or None if no tasks available
        """
        for queue_name in self.queues:
            task_data = await self.queue_driver.dequeue(queue_name)
            if task_data:
                return (task_data, queue_name)
        return None

    async def _process_task(self, task_data: bytes, queue_name: str) -> None:
        """Process a single task with error handling and lifecycle management.

        Deserializes task, increments attempt counter, executes via TaskExecutor, emits
        events, and handles success/failure. Deserialization errors re-enqueue with delay.
        Execution failures delegate to _handle_task_failure() for retry logic.

        Parameters
        ----------
        task_data : bytes
            Serialized task payload from queue
        queue_name : str
            Name of the queue this task was dequeued from
        """
        task: BaseTask | None = None
        start_time = datetime.now(UTC)

        try:
            # Deserialize task
            task = await self._deserialize_task(task_data)

            assert task is not None
            assert task._task_id is not None  # Task ID is set during deserialization

            logger.info(f"Processing task {task._task_id}: {task.__class__.__name__}")

            # Driver already incremented current_attempt in dequeue()
            # Sync the task object with the driver's state
            task._current_attempt += 1

            # Emit task_started event
            await EventRegistry.emit(
                TaskEvent(
                    event_type=EventType.TASK_STARTED,
                    task_id=task._task_id,
                    task_name=task.__class__.__name__,
                    queue=queue_name,
                    worker_id=self.worker_id,
                    attempt=task._current_attempt,
                )
            )

            # Execute task with timeout (delegated to TaskService)
            await self._task_executor.execute(task)

            # Calculate duration
            duration_ms = int((datetime.now(UTC) - start_time).total_seconds() * 1000)

            # Emit task_completed event
            await EventRegistry.emit(
                TaskEvent(
                    event_type=EventType.TASK_COMPLETED,
                    task_id=task._task_id,
                    task_name=task.__class__.__name__,
                    queue=queue_name,
                    worker_id=self.worker_id,
                    duration_ms=duration_ms,
                )
            )

            # Task succeeded - acknowledge and remove from queue
            logger.info(f"Task {task._task_id} completed successfully")
            try:
                # Add timeout to ack to prevent hanging
                await asyncio.wait_for(self.queue_driver.ack(queue_name, task_data), timeout=5.0)
            except TimeoutError:
                logger.error(
                    f"Ack timeout for task {task._task_id} from queue '{queue_name}'. "
                    f"Task completed but may remain in processing list."
                )
            except Exception as ack_error:
                # Log ack error but don't fail the task - it already completed successfully
                logger.error(
                    f"Failed to acknowledge task {task._task_id} from queue '{queue_name}': "
                    f"{ack_error}"
                )
                logger.exception(ack_error)
            self._tasks_processed += 1

        except (ImportError, AttributeError, ValueError, TypeError) as e:
            if task is None:
                # Deserialization failure - nack to retry with backoff
                # Driver tracks attempt count and will eventually move to DLQ
                logger.error(
                    f"Failed to deserialize task from queue '{queue_name}': {e}. Nacking for retry."
                )
                logger.exception(e)
                # Use nack to leverage driver's retry logic
                await self.queue_driver.nack(queue_name, task_data)
            else:
                # ValueError/TypeError during task execution - handle as task failure
                logger.exception(f"Task {task._task_id} failed: {e}")
                await self._handle_task_failure(task, e, queue_name, start_time, task_data)

        except TimeoutError as e:
            if task is None:
                # TimeoutError during deserialization - treat as deserialization failure
                logger.error(
                    f"Deserialization timeout for task from queue '{queue_name}': {e}. "
                    f"Nacking for retry."
                )
                logger.exception(e)
                await self.queue_driver.nack(queue_name, task_data)
            else:
                # TimeoutError during task execution - handle as task failure
                logger.error(f"Task {task._task_id} timed out")
                await self._handle_task_failure(
                    task, TimeoutError("Task exceeded timeout"), queue_name, start_time, task_data
                )

        except Exception as e:
            if task is None:
                # Unexpected error during deserialization that we didn't catch above
                logger.error(
                    f"Unexpected error deserializing task from queue '{queue_name}': {e}. "
                    f"Nacking for retry."
                )
                logger.exception(e)
                await self.queue_driver.nack(queue_name, task_data)
            else:
                logger.exception(f"Task {task._task_id} failed: {e}")
                await self._handle_task_failure(task, e, queue_name, start_time, task_data)

        # Note: Python 3.11+ ExceptionGroup can be used to collect
        # multiple errors if task spawns subtasks

    async def _handle_task_failure(
        self,
        task: BaseTask,
        exception: Exception,
        queue_name: str,
        start_time: datetime,
        task_data: bytes,
    ) -> None:
        """Handle task execution failure with retry and dead-letter logic.

        Checks if task should retry (via TaskExecutor). If yes, serializes task, calculates
        retry delay (exponential/fixed), emits TASK_REENQUEUED event, and re-enqueues. If no,
        emits TASK_FAILED event, calls task.failed() hook, and moves to dead letter queue.

        Parameters
        ----------
        task : BaseTask
            The task instance that failed execution
        exception : Exception
            The exception that caused the failure
        queue_name : str
            Name of the queue the task came from
        start_time : datetime
            Timestamp when task processing began
        task_data : bytes
            Original serialized task data (receipt handle)
        """
        duration_ms = int((datetime.now(UTC) - start_time).total_seconds() * 1000)
        task_id = task._task_id or "unknown"  # Fallback for type safety

        # Driver already incremented the attempt in dequeue(), and worker synced it.
        # Use the current value as the attempt that just ran for delay calculation
        # and event emission. Do not mutate attempts here to avoid double-counting.
        existing_attempt = task.current_attempt

        # Check if we should retry (uses TaskService for the decision logic)
        if self._task_executor.should_retry(task, exception):
            # Serialize and re-enqueue the task as-is. The serialized
            # representation should reflect attempts already run.
            serialized_task = self._task_serializer.serialize(task)
            logger.info(f"Re-enqueuing task {task_id}")

            # Emit task_reenqueued event
            await EventRegistry.emit(
                TaskEvent(
                    event_type=EventType.TASK_REENQUEUED,
                    task_id=task_id,
                    task_name=task.__class__.__name__,
                    queue=queue_name,
                    worker_id=self.worker_id,
                    attempt=task._current_attempt,
                    error=str(exception),
                    duration_ms=duration_ms,
                )
            )

            # Remove old task from processing list before re-enqueuing
            # Use ack() to clean up the old task data
            try:
                await self.queue_driver.ack(queue_name, task_data)
            except Exception as ack_error:
                logger.error(
                    f"Failed to cleanup task {task_id} before retry from queue '{queue_name}': "
                    f"{ack_error}"
                )

            # Re-enqueue with delay (this preserves the current attempt count
            # in the serialized payload; the driver will increment it on next dequeue)
            # Calculate retry delay based on strategy (fixed or exponential)
            config = Config.get()
            # Use the attempt that just ran (existing_attempt) for delay calculation.
            # Validate and cast to RetryStrategy for type safety
            retry_strategy = config.task_defaults.retry_strategy
            if retry_strategy not in ("fixed", "exponential"):
                retry_strategy = "exponential"  # fallback to default
            retry_delay = calculate_retry_delay(
                retry_strategy,
                config.task_defaults.retry_delay,
                existing_attempt,  # type: ignore[arg-type]
            )
            await self.queue_driver.enqueue(
                task.config.get("queue", "default"),
                serialized_task,
                delay_seconds=retry_delay,
                current_attempt=task._current_attempt,
            )
        else:
            # Task has failed permanently. The attempt count was incremented by
            # the driver in dequeue() and synced by worker, so `task._current_attempt`
            # reflects the final attempt number.
            logger.error(
                f"Task {task_id} failed permanently after {task._current_attempt} attempts"
            )

            # Emit task_failed event
            await EventRegistry.emit(
                TaskEvent(
                    event_type=EventType.TASK_FAILED,
                    task_id=task_id,
                    task_name=task.__class__.__name__,
                    queue=queue_name,
                    worker_id=self.worker_id,
                    duration_ms=duration_ms,
                    error=str(exception),
                    traceback=traceback.format_exc(),
                    attempt=task._current_attempt,
                )
            )

            # Call task's failed() hook via TaskService
            await self._task_executor.handle_failed(task, exception)

            # Remove task from processing and mark as failed
            # Use mark_failed() if available (Redis), otherwise use ack() for cleanup
            try:
                if hasattr(self.queue_driver, "mark_failed"):
                    await self.queue_driver.mark_failed(queue_name, task_data)  # type: ignore
                else:
                    # Fallback: use ack() to at least remove from processing list
                    await self.queue_driver.ack(queue_name, task_data)
            except Exception as cleanup_error:
                logger.error(
                    f"Failed to cleanup permanently failed task {task_id} from queue '{queue_name}': "
                    f"{cleanup_error}"
                )

            self._tasks_processed += 1

    async def _deserialize_task(self, task_data: bytes) -> BaseTask:
        """Deserialize task from bytes into task instance.

        Delegates to TaskSerializer to unpack payload, import task class, reconstruct
        with original parameters, and restore metadata.

        Parameters
        ----------
        task_data : bytes
            Serialized task payload from queue

        Returns
        -------
        BaseTask
            Reconstructed task instance ready for execution

        Raises
        ------
        ImportError, AttributeError, ValueError, TypeError
            Deserialization failures (handled by _process_task)
        """
        return await self._task_serializer.deserialize(task_data)

    def get_health_status(self) -> dict[str, Any]:
        """Get worker health status including process pool info.

        Returns
        -------
        dict[str, Any]
            Health status with worker_id, hostname, uptime, tasks_processed, active_tasks,
            queues, and process_pool information
        """
        from asynctasq.tasks.infrastructure.process_pool_manager import get_default_manager

        uptime = (
            int((datetime.now(UTC) - self._start_time).total_seconds()) if self._start_time else 0
        )

        return {
            "worker_id": self.worker_id,
            "hostname": self.hostname,
            "uptime_seconds": uptime,
            "tasks_processed": self._tasks_processed,
            "active_tasks": len(self._tasks),
            "queues": self.queues,
            "process_pool": get_default_manager().get_stats(),
        }

    def _handle_shutdown(self) -> None:
        """Handle graceful shutdown signal (SIGTERM or SIGINT).

        Sets self._running to False to exit polling loop. In-flight tasks complete
        before cleanup.
        """
        logger.info("Shutdown signal received")
        self._running = False

    async def _cleanup(self) -> None:
        """Perform graceful cleanup and resource deallocation on worker shutdown.

        Cancels heartbeat task, waits for in-flight tasks, shuts down process pool,
        emits WORKER_OFFLINE event, closes event emitter, and disconnects driver.
        Blocks until complete. Called automatically in finally block of start().
        """
        logger.info("Waiting for running tasks to complete...")

        # Cancel heartbeat task
        if self._heartbeat_task:
            self._heartbeat_task.cancel()
            try:
                await self._heartbeat_task
            except asyncio.CancelledError:
                pass

        if self._tasks:
            await asyncio.wait(self._tasks)

        # Shutdown process pool if initialized (graceful - wait for in-flight tasks)
        from asynctasq.tasks.infrastructure.process_pool_manager import get_default_manager

        manager = get_default_manager()
        if manager.is_initialized():
            logger.info("Shutting down process pool...")
            await manager.shutdown(wait=True, cancel_futures=False)

        # Emit worker_offline event and close global emitters
        uptime = (
            int((datetime.now(UTC) - self._start_time).total_seconds()) if self._start_time else 0
        )
        await EventRegistry.emit(
            WorkerEvent(
                event_type=EventType.WORKER_OFFLINE,
                worker_id=self.worker_id,
                hostname=self.hostname,
                processed=self._tasks_processed,
                uptime_seconds=uptime,
            )
        )

        # Close any registered global emitters
        await EventRegistry.close_all()

        # Disconnect driver
        await self.queue_driver.disconnect()

        logger.info("Worker shutdown complete")
