"""Unit tests for asynctasq.drivers.retry_utils module."""

import pytest

from asynctasq.drivers.retry_utils import calculate_retry_delay


class TestCalculateRetryDelay:
    """Test calculate_retry_delay function."""

    @pytest.mark.parametrize(
        "retry_strategy,base_delay,current_attempt,expected",
        [
            ("fixed", 60, 1, 60),
            ("fixed", 60, 2, 60),
            ("fixed", 60, 3, 60),
            ("fixed", 30, 1, 30),
            ("fixed", 30, 5, 30),
        ],
    )
    def test_fixed_strategy(self, retry_strategy, base_delay, current_attempt, expected):
        """Test fixed retry strategy."""
        result = calculate_retry_delay(retry_strategy, base_delay, current_attempt)
        assert result == expected

    @pytest.mark.parametrize(
        "retry_strategy,base_delay,current_attempt,expected",
        [
            ("exponential", 60, 1, 60),  # 60 * 2^0 = 60
            ("exponential", 60, 2, 120),  # 60 * 2^1 = 120
            ("exponential", 60, 3, 240),  # 60 * 2^2 = 240
            ("exponential", 30, 1, 30),  # 30 * 2^0 = 30
            ("exponential", 30, 2, 60),  # 30 * 2^1 = 60
            ("exponential", 30, 3, 120),  # 30 * 2^2 = 120
            ("exponential", 30, 4, 240),  # 30 * 2^3 = 240
        ],
    )
    def test_exponential_strategy(self, retry_strategy, base_delay, current_attempt, expected):
        """Test exponential retry strategy."""
        result = calculate_retry_delay(retry_strategy, base_delay, current_attempt)
        assert result == expected

    def test_invalid_strategy(self):
        """Test invalid retry strategy raises ValueError."""
        with pytest.raises(ValueError, match="Invalid retry strategy: invalid"):
            calculate_retry_delay("invalid", 60, 1)  # type: ignore

    @pytest.mark.parametrize("strategy", ["linear", "random", "", " FIXED ", "exponential_backoff"])
    def test_other_invalid_strategies(self, strategy):
        """Test other invalid retry strategies."""
        with pytest.raises(ValueError, match=f"Invalid retry strategy: {strategy}"):
            calculate_retry_delay(strategy, 60, 1)

    def test_edge_cases(self):
        """Test edge cases."""
        # Very large attempt numbers for exponential
        result = calculate_retry_delay("exponential", 1, 10)
        assert result == 1 * (2**9)  # 512

        # Zero base delay
        result = calculate_retry_delay("fixed", 0, 1)
        assert result == 0

        result = calculate_retry_delay("exponential", 0, 1)
        assert result == 0
