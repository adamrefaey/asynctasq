"""Tests for asynctasq.utils.loop module."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from asynctasq.utils.loop import _cleanup_asynctasq, run


class TestCleanupAsyncTasq:
    """Test _cleanup_asynctasq function."""

    @pytest.mark.asyncio
    async def test_cleanup_successful(self):
        """Test successful cleanup of AsyncTasQ resources."""
        with patch("asynctasq.core.dispatcher.cleanup", new_callable=AsyncMock) as mock_cleanup:
            await _cleanup_asynctasq()
            mock_cleanup.assert_called_once()

    @pytest.mark.asyncio
    async def test_cleanup_timeout_error(self):
        """Test cleanup with timeout error."""
        with patch("asynctasq.core.dispatcher.cleanup", side_effect=TimeoutError()):
            with patch("asynctasq.utils.loop.logger") as mock_logger:
                await _cleanup_asynctasq()
                mock_logger.warning.assert_called_once_with("AsyncTasQ cleanup timed out")

    @pytest.mark.asyncio
    async def test_cleanup_dispatcher_exception(self):
        """Test cleanup with dispatcher exception."""
        with patch("asynctasq.core.dispatcher.cleanup", side_effect=Exception("Test error")):
            # Should not raise
            await _cleanup_asynctasq()

    @pytest.mark.asyncio
    async def test_cleanup_sqlalchemy_engine(self):
        """Test cleanup of SQLAlchemy engine."""
        mock_engine = AsyncMock()
        mock_config = MagicMock()
        mock_config.sqlalchemy_engine = mock_engine

        with patch("asynctasq.config.Config.get", return_value=mock_config):
            # Patch isinstance specifically for the _cleanup_asynctasq function
            with patch("asynctasq.utils.loop.isinstance", return_value=True):
                await _cleanup_asynctasq()
                mock_engine.dispose.assert_called_once()

    @pytest.mark.asyncio
    async def test_cleanup_sqlalchemy_engine_exception(self):
        """Test cleanup of SQLAlchemy engine with exception."""
        mock_engine = AsyncMock()
        mock_engine.dispose.side_effect = Exception("Dispose error")
        mock_config = MagicMock()
        mock_config.sqlalchemy_engine = mock_engine

        with patch("asynctasq.config.Config.get", return_value=mock_config):
            with patch("asynctasq.utils.loop.isinstance", return_value=True):
                # Should not raise
                await _cleanup_asynctasq()

    @pytest.mark.asyncio
    async def test_cleanup_sqlalchemy_no_engine(self):
        """Test cleanup when no SQLAlchemy engine is configured."""
        mock_config = MagicMock()
        mock_config.sqlalchemy_engine = None

        with patch("asynctasq.config.Config.get", return_value=mock_config):
            await _cleanup_asynctasq()

    @pytest.mark.asyncio
    async def test_cleanup_sqlalchemy_import_error(self):
        """Test cleanup with SQLAlchemy import error."""
        with patch("asynctasq.config.Config.get", side_effect=ImportError()):
            await _cleanup_asynctasq()

    @pytest.mark.asyncio
    async def test_cleanup_sqlalchemy_config_exception(self):
        """Test cleanup with config exception."""
        with patch("asynctasq.config.Config.get", side_effect=Exception("Config error")):
            await _cleanup_asynctasq()


class TestRunFunction:
    """Test run function."""

    def test_run_successful_with_uvloop(self):
        """Test successful run with uvloop available."""

        async def test_coro():
            return "success"

        with patch("uvloop.new_event_loop") as mock_uvloop_new:
            with patch("asyncio.set_event_loop"):
                mock_loop = MagicMock()
                mock_uvloop_new.return_value = mock_loop
                mock_loop.run_until_complete.side_effect = ["success", None, None, None]

                result = run(test_coro())

                assert result == "success"
                mock_uvloop_new.assert_called_once()
                assert (
                    mock_loop.run_until_complete.call_count == 4
                )  # coro + cleanup + shutdown_asyncgens + shutdown_default_executor
                mock_loop.close.assert_called_once()
                mock_loop.shutdown_asyncgens.assert_called_once()
                mock_loop.shutdown_default_executor.assert_called_once()

    def test_run_successful_without_uvloop(self):
        """Test successful run without uvloop."""

        async def test_coro():
            return "success"

        with patch("uvloop.new_event_loop", side_effect=ImportError()):
            with patch("asyncio.new_event_loop") as mock_asyncio_new:
                with patch("asyncio.set_event_loop"):
                    mock_loop = MagicMock()
                    mock_asyncio_new.return_value = mock_loop
                    mock_loop.run_until_complete.side_effect = ["success", None, None, None]

                    result = run(test_coro())

                    assert result == "success"
                    mock_asyncio_new.assert_called_once()
                    assert mock_loop.run_until_complete.call_count == 4
                    mock_loop.close.assert_called_once()

    def test_run_with_running_loop_raises_error(self):
        """Test run raises error when called from running loop."""

        async def test_coro():
            return "test"

        # Simulate a running loop
        with patch("asyncio.get_running_loop", return_value=MagicMock()):
            with pytest.raises(RuntimeError, match="cannot be called from a running event loop"):
                run(test_coro())

    def test_run_cleanup_exception_handling(self):
        """Test run handles cleanup exceptions gracefully."""

        async def test_coro():
            return "success"

        with patch("uvloop.new_event_loop") as mock_uvloop_new:
            with patch("asyncio.set_event_loop"):
                mock_loop = MagicMock()
                mock_uvloop_new.return_value = mock_loop
                mock_loop.run_until_complete.side_effect = [
                    "success",  # coro result
                    Exception("cleanup error"),  # cleanup failure
                    Exception("asyncgens error"),  # shutdown_asyncgens failure
                    Exception("executor error"),  # shutdown_default_executor failure
                ]

                result = run(test_coro())

                assert result == "success"
                assert mock_loop.run_until_complete.call_count == 4
                mock_loop.close.assert_called_once()

    def test_run_cleanup_timeout_in_cleanup(self):
        """Test run handles timeout in cleanup."""

        async def test_coro():
            return "success"

        with patch("uvloop.new_event_loop") as mock_uvloop_new:
            with patch("asyncio.set_event_loop"):
                mock_loop = MagicMock()
                mock_uvloop_new.return_value = mock_loop
                mock_loop.run_until_complete.side_effect = [
                    "success",  # coro result
                    TimeoutError(),  # cleanup timeout
                    None,  # shutdown_asyncgens
                    None,  # shutdown_default_executor
                ]

                with patch("asynctasq.utils.loop.logger"):
                    result = run(test_coro())

                    assert result == "success"
                    # The warning is logged inside _cleanup_asynctasq, not in run()
                    # So we don't expect it to be called here

    def test_run_with_exception_in_coro(self):
        """Test run propagates exceptions from coroutine."""

        async def failing_coro():
            raise ValueError("Test error")

        with patch("uvloop.new_event_loop") as mock_uvloop_new:
            with patch("asyncio.set_event_loop"):
                mock_loop = MagicMock()
                mock_uvloop_new.return_value = mock_loop
                mock_loop.run_until_complete.side_effect = [
                    ValueError("Test error"),  # coro raises
                    None,  # cleanup
                    None,  # shutdown_asyncgens
                    None,  # shutdown_default_executor
                ]

                with pytest.raises(ValueError, match="Test error"):
                    run(failing_coro())

    def test_run_sets_event_loop_correctly(self):
        """Test run sets and resets event loop correctly."""

        async def test_coro():
            return "success"

        with patch("uvloop.new_event_loop") as mock_uvloop_new:
            with patch("asyncio.set_event_loop") as mock_set_loop:
                mock_loop = MagicMock()
                mock_uvloop_new.return_value = mock_loop
                mock_loop.run_until_complete.side_effect = ["success", None, None, None]

                result = run(test_coro())

                assert result == "success"
                # Should set loop initially and reset to None at end
                assert mock_set_loop.call_count == 2
                mock_set_loop.assert_any_call(mock_loop)
                mock_set_loop.assert_any_call(None)

    def test_run_debug_logging(self):
        """Test run logs appropriate debug messages."""

        async def test_coro():
            return "success"

        with patch("uvloop.new_event_loop") as mock_uvloop_new:
            with patch("asyncio.set_event_loop"):
                with patch("asynctasq.utils.loop.logger") as mock_logger:
                    mock_loop = MagicMock()
                    mock_uvloop_new.return_value = mock_loop
                    mock_loop.run_until_complete.side_effect = ["success", None, None, None]

                    result = run(test_coro())

                    assert result == "success"
                    mock_logger.debug.assert_called_once_with("Using uvloop event loop")

    def test_run_fallback_logging(self):
        """Test run logs fallback to asyncio when uvloop unavailable."""

        async def test_coro():
            return "success"

        with patch("uvloop.new_event_loop", side_effect=ImportError()):
            with patch("asyncio.new_event_loop") as mock_asyncio_new:
                with patch("asyncio.set_event_loop"):
                    with patch("asynctasq.utils.loop.logger") as mock_logger:
                        mock_loop = MagicMock()
                        mock_asyncio_new.return_value = mock_loop
                        mock_loop.run_until_complete.side_effect = ["success", None, None, None]

                        result = run(test_coro())

                        assert result == "success"
                        mock_logger.debug.assert_called_once_with(
                            "Using asyncio event loop (uvloop not available)"
                        )
