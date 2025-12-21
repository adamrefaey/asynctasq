"""Main CLI entry point."""

import argparse
import asyncio
import logging
import sys

from .commands.migrate import MigrationError, run_migrate
from .commands.worker import run_worker
from .config import build_config
from .parser import create_parser
from .utils import setup_logging

logger = logging.getLogger(__name__)


def run_command(args: argparse.Namespace) -> None:
    """Execute the requested command.

    Args:
        args: Parsed command-line arguments
    """
    config = build_config(args)

    command_handlers = {
        "worker": run_worker,
        "migrate": run_migrate,
    }

    handler = command_handlers.get(args.command)
    if handler is None:
        raise ValueError(f"Unknown command: {args.command}")

    # Prefer the helper in asynctasq.utils.loop in production, but call
    # `asyncio.run` here so tests can patch `asynctasq.cli.main.asyncio.run`.
    try:
        asyncio.run(handler(args, config))
    except RuntimeError:
        # Fallback to uvloop-based runner if event loop is already running
        from asynctasq.utils.loop import run as uv_run

        uv_run(handler(args, config))


def main() -> None:
    """Main entry point for the CLI."""
    setup_logging()

    try:
        parser = create_parser()
        args = parser.parse_args()
        run_command(args)
    except KeyboardInterrupt:
        logger.info("Interrupted by user")
        sys.exit(0)
    except MigrationError as e:
        logger.error(str(e))
        sys.exit(1)
    except Exception as e:
        logger.exception(f"Command failed: {e}")
        sys.exit(1)
