"""Unit tests for console utilities."""

from unittest.mock import patch

from pytest import mark

from asynctasq.utils.console import console, print


@mark.unit
class TestConsole:
    """Test console utilities."""

    @patch("asynctasq.utils.console.rich_print")
    def test_print_calls_rich_print(self, mock_rich_print):
        """Test that print function calls rich_print."""
        args = ("Hello", "World")
        kwargs = {"style": "bold"}

        print(*args, **kwargs)

        mock_rich_print.assert_called_once_with(*args, **kwargs)

    def test_console_instance(self):
        """Test that console is a Rich Console instance."""
        assert console is not None
        assert hasattr(console, "print")
        assert hasattr(console, "log")
