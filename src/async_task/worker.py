"""Worker CLI entry point.

This module provides a shortcut for running the worker command:
    python -m async_task.worker --driver redis --queues default,high

This is equivalent to:
    python -m async_task worker --driver redis --queues default,high
"""

import argparse
import asyncio
import logging
import sys

from .cli.commands.worker import run_worker
from .cli.config import build_config
from .cli.parser import add_driver_args
from .cli.utils import DEFAULT_CONCURRENCY, DEFAULT_QUEUE, setup_logging

logger = logging.getLogger(__name__)


def main() -> None:
    """Main entry point for worker CLI."""
    setup_logging()

    parser = argparse.ArgumentParser(
        description="Start a worker to process tasks from queues",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    # Add driver arguments
    add_driver_args(parser)

    # Add worker-specific arguments
    parser.add_argument(
        "--queues",
        type=str,
        help=f"Comma-separated list of queue names to process (default: '{DEFAULT_QUEUE}')",
    )
    parser.add_argument(
        "--concurrency",
        type=int,
        help=f"Maximum number of concurrent tasks (default: {DEFAULT_CONCURRENCY})",
        default=DEFAULT_CONCURRENCY,
    )

    try:
        args = parser.parse_args()
        config = build_config(args)

        logger.info(
            f"Starting worker: driver={config.driver}, "
            f"queues={args.queues or DEFAULT_QUEUE}, concurrency={args.concurrency}"
        )

        asyncio.run(run_worker(args, config))
    except KeyboardInterrupt:
        logger.info("Interrupted by user")
        sys.exit(0)
    except Exception as e:
        logger.exception(f"Worker failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
