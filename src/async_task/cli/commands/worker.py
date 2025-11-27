"""Worker command implementation."""

import argparse
import logging

from async_task.cli.utils import DEFAULT_CONCURRENCY, parse_queues
from async_task.core.driver_factory import DriverFactory
from async_task.core.worker import Worker

logger = logging.getLogger(__name__)


async def run_worker(args: argparse.Namespace, config) -> None:
    """Run the worker command to process tasks from queues.

    Args:
        args: Parsed command-line arguments
        config: Configuration object
    """
    queues = parse_queues(getattr(args, "queues", None))
    concurrency = getattr(args, "concurrency", DEFAULT_CONCURRENCY)

    logger.info(
        f"Starting worker: driver={config.driver}, queues={queues}, concurrency={concurrency}"
    )

    driver = DriverFactory.create_from_config(config)
    worker = Worker(
        queue_driver=driver,
        queues=queues,
        concurrency=concurrency,
    )

    await worker.start()
