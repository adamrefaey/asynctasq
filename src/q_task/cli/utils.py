"""CLI utility functions and constants."""

import logging

# Default values
DEFAULT_CONCURRENCY = 10
DEFAULT_QUEUE = "default"

logger = logging.getLogger(__name__)


def setup_logging() -> None:
    """Configure logging for the CLI."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )


def parse_queues(queues_str: str | None) -> list[str]:
    """Parse comma-separated queue names into a list."""
    if not queues_str:
        return [DEFAULT_QUEUE]
    queues = [q.strip() for q in queues_str.split(",") if q.strip()]
    return queues if queues else [DEFAULT_QUEUE]
