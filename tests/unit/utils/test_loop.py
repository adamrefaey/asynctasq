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

        # Mock asyncio.Runner context manager
        mock_runner_instance = MagicMock()
        mock_runner_instance.run.side_effect = ["success", None]  # coro result, then cleanup

        mock_runner = MagicMock()
        mock_runner.__enter__.return_value = mock_runner_instance
        mock_runner.__exit__.return_value = None

        with patch("uvloop.new_event_loop"):
            with patch("asyncio.Runner", return_value=mock_runner):
                result = run(test_coro())

                assert result == "success"
                # Runner.run should be called twice: once for coro, once for cleanup
                assert mock_runner_instance.run.call_count == 2
                mock_runner.__enter__.assert_called_once()
                mock_runner.__exit__.assert_called_once()

    def test_run_successful_without_uvloop(self):
        """Test successful run without uvloop."""

        async def test_coro():
            return "success"

        # Mock asyncio.Runner context manager
        mock_runner_instance = MagicMock()
        mock_runner_instance.run.side_effect = ["success", None]  # coro result, then cleanup

        mock_runner = MagicMock()
        mock_runner.__enter__.return_value = mock_runner_instance
        mock_runner.__exit__.return_value = None

        with patch("uvloop.new_event_loop", side_effect=ImportError()):
            with patch("asyncio.Runner", return_value=mock_runner):
                result = run(test_coro())

                assert result == "success"
                # Runner.run should be called twice: once for coro, once for cleanup
                assert mock_runner_instance.run.call_count == 2
                mock_runner.__enter__.assert_called_once()
                mock_runner.__exit__.assert_called_once()

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

        # Mock asyncio.Runner context manager
        mock_runner_instance = MagicMock()
        # First call succeeds, second call (cleanup) raises exception
        mock_runner_instance.run.side_effect = ["success", Exception("cleanup error")]

        mock_runner = MagicMock()
        mock_runner.__enter__.return_value = mock_runner_instance
        mock_runner.__exit__.return_value = None

        with patch("uvloop.new_event_loop"):
            with patch("asyncio.Runner", return_value=mock_runner):
                with patch("asynctasq.utils.loop.logger"):
                    result = run(test_coro())

                    assert result == "success"
                    # Runner.run should be called twice: once for coro, once for cleanup (which fails)
                    assert mock_runner_instance.run.call_count == 2
                    # Runner context manager still exits cleanly
                    mock_runner.__exit__.assert_called_once()

    def test_run_cleanup_timeout_in_cleanup(self):
        """Test run handles timeout in cleanup."""

        async def test_coro():
            return "success"

        # Mock asyncio.Runner context manager
        mock_runner_instance = MagicMock()
        # First call succeeds, second call (cleanup) times out
        mock_runner_instance.run.side_effect = ["success", TimeoutError()]

        mock_runner = MagicMock()
        mock_runner.__enter__.return_value = mock_runner_instance
        mock_runner.__exit__.return_value = None

        with patch("uvloop.new_event_loop"):
            with patch("asyncio.Runner", return_value=mock_runner):
                with patch("asynctasq.utils.loop.logger"):
                    result = run(test_coro())

                    assert result == "success"
                    # The warning is logged inside _cleanup_asynctasq, not in run()
                    # Runner.run should still be called twice
                    assert mock_runner_instance.run.call_count == 2

    def test_run_with_exception_in_coro(self):
        """Test run propagates exceptions from coroutine."""

        async def failing_coro():
            raise ValueError("Test error")

        # Mock asyncio.Runner context manager
        mock_runner_instance = MagicMock()
        # First call raises exception, cleanup may or may not happen depending on implementation
        mock_runner_instance.run.side_effect = [ValueError("Test error"), None]

        mock_runner = MagicMock()
        mock_runner.__enter__.return_value = mock_runner_instance
        mock_runner.__exit__.return_value = None

        with patch("uvloop.new_event_loop"):
            with patch("asyncio.Runner", return_value=mock_runner):
                with pytest.raises(ValueError, match="Test error"):
                    run(failing_coro())

    def test_run_sets_event_loop_correctly(self):
        """Test run uses asyncio.Runner which manages event loop automatically."""

        async def test_coro():
            return "success"

        # Mock asyncio.Runner context manager
        mock_runner_instance = MagicMock()
        mock_runner_instance.run.side_effect = ["success", None]

        mock_runner = MagicMock()
        mock_runner.__enter__.return_value = mock_runner_instance
        mock_runner.__exit__.return_value = None

        with patch("uvloop.new_event_loop"):
            with patch("asyncio.Runner", return_value=mock_runner):
                result = run(test_coro())

                assert result == "success"
                # Runner handles loop management internally, so we just verify it was used
                mock_runner.__enter__.assert_called_once()
                mock_runner.__exit__.assert_called_once()

    def test_run_debug_logging(self):
        """Test run logs appropriate debug messages."""

        async def test_coro():
            return "success"

        # Mock asyncio.Runner context manager
        mock_runner_instance = MagicMock()
        mock_runner_instance.run.side_effect = ["success", None]

        mock_runner = MagicMock()
        mock_runner.__enter__.return_value = mock_runner_instance
        mock_runner.__exit__.return_value = None

        with patch("uvloop.new_event_loop"):
            with patch("asyncio.Runner", return_value=mock_runner):
                with patch("asynctasq.utils.loop.logger") as mock_logger:
                    result = run(test_coro())

                    assert result == "success"
                    mock_logger.debug.assert_called_once_with("Using asyncio.Runner with uvloop")

    def test_run_fallback_logging(self):
        """Test run logs fallback to asyncio when uvloop unavailable."""
        import builtins

        async def test_coro():
            return "success"

        # Mock asyncio.Runner context manager
        mock_runner_instance = MagicMock()
        mock_runner_instance.run.side_effect = ["success", None]

        mock_runner = MagicMock()
        mock_runner.__enter__.return_value = mock_runner_instance
        mock_runner.__exit__.return_value = None

        # Patch builtins.__import__ to raise ImportError when importing uvloop
        original_import = builtins.__import__

        def mock_import(name, *args, **kwargs):
            if name == "uvloop":
                raise ImportError("uvloop not available")
            return original_import(name, *args, **kwargs)

        with patch("builtins.__import__", side_effect=mock_import):
            with patch("asyncio.Runner", return_value=mock_runner):
                with patch("asynctasq.utils.loop.logger") as mock_logger:
                    result = run(test_coro())

                    assert result == "success"
                    mock_logger.debug.assert_called_once_with(
                        "Using asyncio.Runner (uvloop not available)"
                    )
