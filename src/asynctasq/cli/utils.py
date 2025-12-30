"""CLI utility functions and constants."""

import logging

from rich.console import Console
from rich.logging import RichHandler

# Default values
DEFAULT_CONCURRENCY = 10
DEFAULT_QUEUE = "default"

logger = logging.getLogger(__name__)

# Global Rich console instance for beautiful output
console = Console()


def setup_logging() -> None:
    """Configure beautiful logging for the CLI using Rich.

    Sets up Rich's logging handler with:
    - Colorized output with syntax highlighting
    - Clean, readable format optimized for development
    - Proper handling of tracebacks and exceptions
    - Emoji and icons for better visual feedback
    """
    logging.basicConfig(
        level=logging.INFO,
        format="%(message)s",
        datefmt="[%X]",
        handlers=[
            RichHandler(
                console=console,
                rich_tracebacks=True,
                tracebacks_show_locals=True,
                show_path=False,
                markup=True,
                log_time_format="[%X]",
            )
        ],
    )


def parse_queues(queues_str: str | None) -> list[str]:
    """Parse comma-separated queue names into a list."""
    if not queues_str:
        return [DEFAULT_QUEUE]
    queues = [q.strip() for q in queues_str.split(",") if q.strip()]
    return queues if queues else [DEFAULT_QUEUE]
