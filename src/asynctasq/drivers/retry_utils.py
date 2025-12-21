"""Shared retry utilities for queue drivers."""

from typing import Literal

RetryStrategy = Literal["fixed", "exponential"]


def calculate_retry_delay(
    retry_strategy: RetryStrategy,
    base_delay_seconds: int,
    current_attempt: int,
) -> int:
    """Calculate the retry delay based on the retry strategy.

    Args:
        retry_strategy: The retry strategy to use ("fixed" or "exponential")
        base_delay_seconds: The base delay in seconds
        current_attempt: The current attempt number (1-indexed)

    Returns:
        The calculated retry delay in seconds

    Examples:
        Fixed strategy (base_delay=60):
            - Attempt 1 fails -> retry after 60s
            - Attempt 2 fails -> retry after 60s
            - Attempt 3 fails -> retry after 60s

        Exponential strategy (base_delay=60):
            - Attempt 1 fails -> retry after 60s * 2^0 = 60s
            - Attempt 2 fails -> retry after 60s * 2^1 = 120s
            - Attempt 3 fails -> retry after 60s * 2^2 = 240s
    """
    if retry_strategy == "fixed":
        return base_delay_seconds
    elif retry_strategy == "exponential":
        # Exponential backoff: base * 2^(attempt-1)
        return base_delay_seconds * (2 ** (current_attempt - 1))
    else:
        raise ValueError(f"Invalid retry strategy: {retry_strategy}")
