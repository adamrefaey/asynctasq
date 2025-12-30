"""Unit tests for CLI utilities.

Testing Strategy:
- pytest 9.0.1 with asyncio_mode="auto" (no decorators needed)
- AAA pattern (Arrange, Act, Assert)
- Test utility functions and constants
- Fast, isolated tests
"""

import logging
from unittest.mock import patch

from pytest import main, mark

from asynctasq.cli.utils import DEFAULT_CONCURRENCY, DEFAULT_QUEUE, parse_queues, setup_logging


@mark.unit
class TestConstants:
    """Test CLI constants."""

    def test_default_concurrency_value(self) -> None:
        # Assert
        assert DEFAULT_CONCURRENCY == 10
        assert isinstance(DEFAULT_CONCURRENCY, int)

    def test_default_queue_value(self) -> None:
        # Assert
        assert DEFAULT_QUEUE == "default"
        assert isinstance(DEFAULT_QUEUE, str)


@mark.unit
class TestSetupLogging:
    """Test setup_logging() function."""

    @patch("asynctasq.cli.utils.logging.basicConfig")
    def test_setup_logging_configures_basic_config(self, mock_basic_config) -> None:
        # Act
        setup_logging()

        # Assert - Verify Rich logging handler is configured
        mock_basic_config.assert_called_once()
        call_kwargs = mock_basic_config.call_args.kwargs
        assert call_kwargs["level"] == logging.INFO
        assert call_kwargs["format"] == "%(message)s"
        assert call_kwargs["datefmt"] == "[%X]"
        assert len(call_kwargs["handlers"]) == 1
        # Verify it's a RichHandler (check class name since it's mocked)
        assert "RichHandler" in str(type(call_kwargs["handlers"][0]))

    def test_setup_logging_can_be_called_multiple_times(self) -> None:
        # Act & Assert - should not raise
        setup_logging()
        setup_logging()
        setup_logging()


@mark.unit
class TestParseQueues:
    """Test parse_queues() function."""

    def test_parse_queues_with_none_returns_default(self) -> None:
        # Act
        result = parse_queues(None)

        # Assert
        assert result == [DEFAULT_QUEUE]

    def test_parse_queues_with_empty_string_returns_default(self) -> None:
        # Act
        result = parse_queues("")

        # Assert
        assert result == [DEFAULT_QUEUE]

    def test_parse_queues_with_single_queue(self) -> None:
        # Act
        result = parse_queues("high")

        # Assert
        assert result == ["high"]

    def test_parse_queues_with_multiple_queues(self) -> None:
        # Act
        result = parse_queues("high,medium,low")

        # Assert
        assert result == ["high", "medium", "low"]

    def test_parse_queues_strips_whitespace(self) -> None:
        # Act
        result = parse_queues(" high , medium , low ")

        # Assert
        assert result == ["high", "medium", "low"]

    def test_parse_queues_with_empty_queue_names_filters_them(self) -> None:
        # Act
        result = parse_queues("high,,low, ,medium")

        # Assert
        assert result == ["high", "low", "medium"]

    def test_parse_queues_with_only_whitespace_returns_default(self) -> None:
        # Act
        result = parse_queues("   ,  ,  ")

        # Assert
        assert result == [DEFAULT_QUEUE]

    def test_parse_queues_with_special_characters(self) -> None:
        # Act
        result = parse_queues("queue-1,queue_2,queue.3")

        # Assert
        assert result == ["queue-1", "queue_2", "queue.3"]

    def test_parse_queues_preserves_order(self) -> None:
        # Act
        result = parse_queues("first,second,third")

        # Assert
        assert result == ["first", "second", "third"]

    def test_parse_queues_with_many_queues(self) -> None:
        # Act
        queues = ",".join([f"queue{i}" for i in range(100)])
        result = parse_queues(queues)

        # Assert
        assert len(result) == 100
        assert result[0] == "queue0"
        assert result[-1] == "queue99"


if __name__ == "__main__":
    main([__file__, "-s", "-m", "unit"])
