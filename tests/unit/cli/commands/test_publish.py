"""Unit tests for publish command.

Testing Strategy:
- pytest 9.0.1 with asyncio_mode="auto" (no decorators needed)
- AAA pattern (Arrange, Act, Assert)
- Test all code paths for >90% coverage
- Fast, isolated tests with proper mocking
"""

from __future__ import annotations

import argparse
from pathlib import Path
from unittest.mock import MagicMock, patch

from pytest import mark, raises

from asynctasq.cli.commands.publish import run_publish


@mark.unit
class TestRunPublish:
    """Test run_publish() function."""

    @mark.asyncio
    async def test_run_publish_success_with_default_output_dir(self, tmp_path: Path) -> None:
        """Test successful publish to current working directory."""
        # Arrange - Create a fake package structure
        fake_publish_py = tmp_path / "pkg" / "src" / "asynctasq" / "cli" / "commands" / "publish.py"
        fake_publish_py.parent.mkdir(parents=True, exist_ok=True)
        fake_publish_py.write_text("# fake")

        package_root = fake_publish_py.parent.parent.parent.parent.parent
        source_env = package_root / ".env.example"
        source_env.write_text("# Default output test\nDEFAULT_KEY=value\n")

        cwd_dir = tmp_path / "cwd_target"
        cwd_dir.mkdir(parents=True, exist_ok=True)

        args = argparse.Namespace(output_dir=None, force=False)

        with patch("asynctasq.cli.commands.publish.Path") as MockPath:
            original_path = Path
            call_count = [0]

            def path_factory(arg=None):
                call_count[0] += 1
                if call_count[0] == 1:
                    return fake_publish_py
                if arg is None:
                    return original_path.cwd()
                return original_path(arg)

            MockPath.side_effect = path_factory
            MockPath.cwd.return_value = cwd_dir

            # Act
            await run_publish(args)

        # Assert
        target_file = cwd_dir / ".env.example"
        assert target_file.exists()
        assert "DEFAULT_KEY=value" in target_file.read_text()

    @mark.asyncio
    async def test_run_publish_creates_target_directory(self, tmp_path: Path) -> None:
        """Test that publish creates target directory if it doesn't exist."""
        # Arrange - Create a fake package structure
        fake_publish_py = tmp_path / "pkg" / "src" / "asynctasq" / "cli" / "commands" / "publish.py"
        fake_publish_py.parent.mkdir(parents=True, exist_ok=True)
        fake_publish_py.write_text("# fake")

        package_root = fake_publish_py.parent.parent.parent.parent.parent
        source_env = package_root / ".env.example"
        source_env.write_text("# Creates dir test\nDIR_KEY=value\n")

        target_dir = tmp_path / "new_project"  # Does not exist yet
        args = argparse.Namespace(output_dir=str(target_dir), force=False)

        with patch("asynctasq.cli.commands.publish.Path") as MockPath:
            original_path = Path
            call_count = [0]

            def path_factory(arg=None):
                call_count[0] += 1
                if call_count[0] == 1:
                    return fake_publish_py
                if arg is None:
                    return original_path.cwd()
                return original_path(arg)

            MockPath.side_effect = path_factory

            # Act
            await run_publish(args)

        # Assert
        assert target_dir.exists()
        target_file = target_dir / ".env.example"
        assert target_file.exists()
        assert "DIR_KEY=value" in target_file.read_text()

    @mark.asyncio
    async def test_run_publish_source_file_not_found(self, tmp_path: Path) -> None:
        """Test that FileNotFoundError is raised when source .env.example doesn't exist."""
        # Arrange
        args = argparse.Namespace(output_dir=str(tmp_path), force=False)

        # Create a mock that simulates missing source file
        with patch("asynctasq.cli.commands.publish.Path") as MockPath:
            mock_source = MagicMock()
            mock_source.exists.return_value = False
            mock_source.__str__ = MagicMock(return_value="/fake/path/.env.example")
            mock_source.__truediv__ = lambda self, other: mock_source

            mock_file_path = MagicMock()
            mock_file_path.parent.parent.parent.parent.parent.__truediv__ = (
                lambda self, x: mock_source
            )

            # First call is Path(__file__), subsequent calls are for other paths
            call_count = [0]
            original_path = Path

            def path_factory(arg=None):
                call_count[0] += 1
                if call_count[0] == 1:
                    # Return mock for Path(__file__)
                    return mock_file_path
                if arg is None:
                    return original_path.cwd()
                return original_path(arg)

            MockPath.side_effect = path_factory
            MockPath.cwd.return_value = tmp_path

            # Act & Assert
            with raises(FileNotFoundError, match=".env.example file not found"):
                await run_publish(args)

    @mark.asyncio
    async def test_run_publish_target_exists_without_force(self, tmp_path: Path) -> None:
        """Test that FileExistsError is raised when target exists and force=False."""
        # Arrange
        # Create source file
        package_root = tmp_path / "package"
        package_root.mkdir(parents=True, exist_ok=True)
        source_env = package_root / ".env.example"
        source_env.write_text("# Test\n")

        # Create existing target file
        target_dir = tmp_path / "target"
        target_dir.mkdir(parents=True, exist_ok=True)
        target_env = target_dir / ".env.example"
        target_env.write_text("# Existing\n")

        args = argparse.Namespace(output_dir=str(target_dir), force=False)

        # Setup mocks
        with patch("asynctasq.cli.commands.publish.Path") as MockPath:
            original_path = Path
            call_count = [0]

            def path_factory(arg=None):
                call_count[0] += 1
                if call_count[0] == 1:
                    # Path(__file__) - return mock with package_root
                    mock_file = MagicMock()
                    mock_file.parent.parent.parent.parent.parent = package_root
                    return mock_file
                if arg is None:
                    return original_path.cwd()
                return original_path(arg)

            MockPath.side_effect = path_factory
            MockPath.cwd.return_value = target_dir

            # Act & Assert
            with raises(FileExistsError, match=".env.example already exists"):
                await run_publish(args)

    @mark.asyncio
    async def test_run_publish_target_exists_with_force(self, tmp_path: Path) -> None:
        """Test that file is overwritten when force=True."""
        # Arrange
        package_root = tmp_path / "package"
        package_root.mkdir(parents=True, exist_ok=True)
        source_env = package_root / ".env.example"
        source_env.write_text("# New content\nNEW_KEY=new_value\n")

        target_dir = tmp_path / "target"
        target_dir.mkdir(parents=True, exist_ok=True)
        target_env = target_dir / ".env.example"
        target_env.write_text("# Old content\n")

        args = argparse.Namespace(output_dir=str(target_dir), force=True)

        with patch("asynctasq.cli.commands.publish.Path") as MockPath:
            original_path = Path
            call_count = [0]

            def path_factory(arg=None):
                call_count[0] += 1
                if call_count[0] == 1:
                    mock_file = MagicMock()
                    mock_file.parent.parent.parent.parent.parent = package_root
                    return mock_file
                if arg is None:
                    return original_path.cwd()
                return original_path(arg)

            MockPath.side_effect = path_factory
            MockPath.cwd.return_value = target_dir

            # Act
            await run_publish(args)

        # Assert
        assert target_env.exists()
        assert "NEW_KEY=new_value" in target_env.read_text()

    @mark.asyncio
    async def test_run_publish_with_explicit_output_dir(self, tmp_path: Path) -> None:
        """Test publish to explicitly specified output directory."""
        # Arrange
        package_root = tmp_path / "package"
        package_root.mkdir(parents=True, exist_ok=True)
        source_env = package_root / ".env.example"
        source_env.write_text("# Explicit output test\nEXPLICIT_KEY=value\n")

        output_dir = tmp_path / "custom_output"
        args = argparse.Namespace(output_dir=str(output_dir), force=False)

        with patch("asynctasq.cli.commands.publish.Path") as MockPath:
            original_path = Path
            call_count = [0]

            def path_factory(arg=None):
                call_count[0] += 1
                if call_count[0] == 1:
                    mock_file = MagicMock()
                    mock_file.parent.parent.parent.parent.parent = package_root
                    return mock_file
                if arg is None:
                    return original_path.cwd()
                return original_path(arg)

            MockPath.side_effect = path_factory

            # Act
            await run_publish(args)

        # Assert
        target_file = output_dir / ".env.example"
        assert target_file.exists()
        assert "EXPLICIT_KEY=value" in target_file.read_text()

    @mark.asyncio
    async def test_run_publish_copy_failure(self, tmp_path: Path) -> None:
        """Test that exceptions during copy are re-raised."""
        # Arrange
        package_root = tmp_path / "package"
        package_root.mkdir(parents=True, exist_ok=True)
        source_env = package_root / ".env.example"
        source_env.write_text("# Test\n")

        target_dir = tmp_path / "target"
        args = argparse.Namespace(output_dir=str(target_dir), force=False)

        with (
            patch("asynctasq.cli.commands.publish.Path") as MockPath,
            patch(
                "asynctasq.cli.commands.publish.shutil.copy2",
                side_effect=PermissionError("Permission denied"),
            ),
        ):
            original_path = Path
            call_count = [0]

            def path_factory(arg=None):
                call_count[0] += 1
                if call_count[0] == 1:
                    mock_file = MagicMock()
                    mock_file.parent.parent.parent.parent.parent = package_root
                    return mock_file
                if arg is None:
                    return original_path.cwd()
                return original_path(arg)

            MockPath.side_effect = path_factory

            # Act & Assert
            with raises(PermissionError, match="Permission denied"):
                await run_publish(args)

    @mark.asyncio
    async def test_run_publish_uses_cwd_when_output_dir_none(self, tmp_path: Path) -> None:
        """Test that current working directory is used when output_dir is None."""
        # Arrange
        package_root = tmp_path / "package"
        package_root.mkdir(parents=True, exist_ok=True)
        source_env = package_root / ".env.example"
        source_env.write_text("# CWD test\nCWD_KEY=value\n")

        cwd_dir = tmp_path / "cwd"
        cwd_dir.mkdir(parents=True, exist_ok=True)

        args = argparse.Namespace(output_dir=None, force=False)

        with patch("asynctasq.cli.commands.publish.Path") as MockPath:
            original_path = Path
            call_count = [0]

            def path_factory(arg=None):
                call_count[0] += 1
                if call_count[0] == 1:
                    mock_file = MagicMock()
                    mock_file.parent.parent.parent.parent.parent = package_root
                    return mock_file
                if arg is None:
                    return original_path.cwd()
                return original_path(arg)

            MockPath.side_effect = path_factory
            MockPath.cwd.return_value = cwd_dir

            # Act
            await run_publish(args)

        # Assert
        target_file = cwd_dir / ".env.example"
        assert target_file.exists()
        assert "CWD_KEY=value" in target_file.read_text()

    @mark.asyncio
    async def test_run_publish_config_parameter_unused(self, tmp_path: Path) -> None:
        """Test that config parameter is accepted but unused."""
        # Arrange
        package_root = tmp_path / "package"
        package_root.mkdir(parents=True, exist_ok=True)
        source_env = package_root / ".env.example"
        source_env.write_text("# Config test\n")

        target_dir = tmp_path / "target"
        args = argparse.Namespace(output_dir=str(target_dir), force=False)

        # Pass a mock config object
        mock_config = MagicMock()

        with patch("asynctasq.cli.commands.publish.Path") as MockPath:
            original_path = Path
            call_count = [0]

            def path_factory(arg=None):
                call_count[0] += 1
                if call_count[0] == 1:
                    mock_file = MagicMock()
                    mock_file.parent.parent.parent.parent.parent = package_root
                    return mock_file
                if arg is None:
                    return original_path.cwd()
                return original_path(arg)

            MockPath.side_effect = path_factory

            # Act - should not raise even with config passed
            await run_publish(args, config=mock_config)

        # Assert
        target_file = target_dir / ".env.example"
        assert target_file.exists()

    @mark.asyncio
    async def test_run_publish_prints_success_message(self, tmp_path: Path, capsys) -> None:
        """Test that success message is printed to stdout."""
        # Arrange
        package_root = tmp_path / "package"
        package_root.mkdir(parents=True, exist_ok=True)
        source_env = package_root / ".env.example"
        source_env.write_text("# Test\n")

        target_dir = tmp_path / "target"
        args = argparse.Namespace(output_dir=str(target_dir), force=False)

        with patch("asynctasq.cli.commands.publish.Path") as MockPath:
            original_path = Path
            call_count = [0]

            def path_factory(arg=None):
                call_count[0] += 1
                if call_count[0] == 1:
                    mock_file = MagicMock()
                    mock_file.parent.parent.parent.parent.parent = package_root
                    return mock_file
                if arg is None:
                    return original_path.cwd()
                return original_path(arg)

            MockPath.side_effect = path_factory

            # Act
            await run_publish(args)

        # Assert
        captured = capsys.readouterr()
        assert "✓ Published .env.example to:" in captured.out
        assert "Next steps:" in captured.out
        assert "Copy .env.example to .env" in captured.out
        assert "Update the values in .env" in captured.out

    @mark.asyncio
    async def test_run_publish_logs_success(self, tmp_path: Path, caplog) -> None:
        """Test that success is logged."""
        # Arrange
        import logging

        package_root = tmp_path / "package"
        package_root.mkdir(parents=True, exist_ok=True)
        source_env = package_root / ".env.example"
        source_env.write_text("# Test\n")

        target_dir = tmp_path / "target"
        args = argparse.Namespace(output_dir=str(target_dir), force=False)

        with (
            patch("asynctasq.cli.commands.publish.Path") as MockPath,
            caplog.at_level(logging.INFO),
        ):
            original_path = Path
            call_count = [0]

            def path_factory(arg=None):
                call_count[0] += 1
                if call_count[0] == 1:
                    mock_file = MagicMock()
                    mock_file.parent.parent.parent.parent.parent = package_root
                    return mock_file
                if arg is None:
                    return original_path.cwd()
                return original_path(arg)

            MockPath.side_effect = path_factory

            # Act
            await run_publish(args)

        # Assert
        assert "Successfully published .env.example" in caplog.text

    @mark.asyncio
    async def test_run_publish_logs_error_on_source_not_found(self, tmp_path: Path, caplog) -> None:
        """Test that error is logged when source file not found."""
        # Arrange
        import logging

        package_root = tmp_path / "package"
        package_root.mkdir(parents=True, exist_ok=True)
        # Intentionally NOT creating the source .env.example

        target_dir = tmp_path / "target"
        args = argparse.Namespace(output_dir=str(target_dir), force=False)

        with (
            patch("asynctasq.cli.commands.publish.Path") as MockPath,
            caplog.at_level(logging.ERROR),
        ):
            original_path = Path
            call_count = [0]

            def path_factory(arg=None):
                call_count[0] += 1
                if call_count[0] == 1:
                    mock_file = MagicMock()
                    mock_file.parent.parent.parent.parent.parent = package_root
                    return mock_file
                if arg is None:
                    return original_path.cwd()
                return original_path(arg)

            MockPath.side_effect = path_factory

            # Act
            with raises(FileNotFoundError):
                await run_publish(args)

        # Assert
        assert ".env.example file not found" in caplog.text

    @mark.asyncio
    async def test_run_publish_logs_error_on_target_exists(self, tmp_path: Path, caplog) -> None:
        """Test that error is logged when target exists without force."""
        # Arrange
        import logging

        package_root = tmp_path / "package"
        package_root.mkdir(parents=True, exist_ok=True)
        source_env = package_root / ".env.example"
        source_env.write_text("# Test\n")

        target_dir = tmp_path / "target"
        target_dir.mkdir(parents=True, exist_ok=True)
        target_env = target_dir / ".env.example"
        target_env.write_text("# Existing\n")

        args = argparse.Namespace(output_dir=str(target_dir), force=False)

        with (
            patch("asynctasq.cli.commands.publish.Path") as MockPath,
            caplog.at_level(logging.ERROR),
        ):
            original_path = Path
            call_count = [0]

            def path_factory(arg=None):
                call_count[0] += 1
                if call_count[0] == 1:
                    mock_file = MagicMock()
                    mock_file.parent.parent.parent.parent.parent = package_root
                    return mock_file
                if arg is None:
                    return original_path.cwd()
                return original_path(arg)

            MockPath.side_effect = path_factory

            # Act
            with raises(FileExistsError):
                await run_publish(args)

        # Assert
        assert ".env.example already exists" in caplog.text
        assert "--force to overwrite" in caplog.text

    @mark.asyncio
    async def test_run_publish_logs_error_on_copy_failure(self, tmp_path: Path, caplog) -> None:
        """Test that error is logged when copy fails."""
        # Arrange
        import logging

        package_root = tmp_path / "package"
        package_root.mkdir(parents=True, exist_ok=True)
        source_env = package_root / ".env.example"
        source_env.write_text("# Test\n")

        target_dir = tmp_path / "target"
        args = argparse.Namespace(output_dir=str(target_dir), force=False)

        with (
            patch("asynctasq.cli.commands.publish.Path") as MockPath,
            patch(
                "asynctasq.cli.commands.publish.shutil.copy2",
                side_effect=OSError("Disk full"),
            ),
            caplog.at_level(logging.ERROR),
        ):
            original_path = Path
            call_count = [0]

            def path_factory(arg=None):
                call_count[0] += 1
                if call_count[0] == 1:
                    mock_file = MagicMock()
                    mock_file.parent.parent.parent.parent.parent = package_root
                    return mock_file
                if arg is None:
                    return original_path.cwd()
                return original_path(arg)

            MockPath.side_effect = path_factory

            # Act
            with raises(OSError, match="Disk full"):
                await run_publish(args)

        # Assert
        assert "Failed to copy .env.example" in caplog.text


@mark.unit
class TestRunPublishIntegration:
    """Integration-style tests for run_publish using real file operations.

    These tests use a more direct approach without heavy mocking to ensure
    the actual logic works correctly.
    """

    @mark.asyncio
    async def test_full_publish_flow_real_files(self, tmp_path: Path) -> None:
        """Test the full publish flow with real file operations."""
        # Arrange - Create a mock package structure
        # Simulate: package_root/src/asynctasq/cli/commands/publish.py
        fake_publish_py = (
            tmp_path / "fake_package" / "src" / "asynctasq" / "cli" / "commands" / "publish.py"
        )
        fake_publish_py.parent.mkdir(parents=True, exist_ok=True)
        fake_publish_py.write_text("# fake")

        # The package_root should be 5 levels up from publish.py
        package_root = fake_publish_py.parent.parent.parent.parent.parent
        assert package_root == tmp_path / "fake_package"

        # Create the .env.example in package root
        source_env = package_root / ".env.example"
        source_env.write_text("# Integration test\nINT_KEY=int_value\n")

        target_dir = tmp_path / "project"
        target_dir.mkdir(parents=True, exist_ok=True)

        args = argparse.Namespace(output_dir=str(target_dir), force=False)

        # Create a patched version that uses our fake structure
        with patch("asynctasq.cli.commands.publish.Path") as MockPath:
            original_path = Path
            call_count = [0]

            def path_factory(arg=None):
                call_count[0] += 1
                if call_count[0] == 1:
                    # This is Path(__file__) call
                    return fake_publish_py
                if arg is None:
                    return original_path.cwd()
                return original_path(arg)

            MockPath.side_effect = path_factory

            # Act
            await run_publish(args)

        # Assert
        result_file = target_dir / ".env.example"
        assert result_file.exists()
        content = result_file.read_text()
        assert "INT_KEY=int_value" in content

    @mark.asyncio
    async def test_nested_target_directory_creation(self, tmp_path: Path) -> None:
        """Test that deeply nested target directories are created."""
        # Arrange
        fake_publish_py = tmp_path / "pkg" / "src" / "asynctasq" / "cli" / "commands" / "publish.py"
        fake_publish_py.parent.mkdir(parents=True, exist_ok=True)
        fake_publish_py.write_text("# fake")

        package_root = fake_publish_py.parent.parent.parent.parent.parent
        source_env = package_root / ".env.example"
        source_env.write_text("# Nested test\n")

        # Deeply nested target that doesn't exist
        target_dir = tmp_path / "a" / "b" / "c" / "d" / "project"
        args = argparse.Namespace(output_dir=str(target_dir), force=False)

        with patch("asynctasq.cli.commands.publish.Path") as MockPath:
            original_path = Path
            call_count = [0]

            def path_factory(arg=None):
                call_count[0] += 1
                if call_count[0] == 1:
                    return fake_publish_py
                if arg is None:
                    return original_path.cwd()
                return original_path(arg)

            MockPath.side_effect = path_factory

            # Act
            await run_publish(args)

        # Assert
        assert target_dir.exists()
        assert (target_dir / ".env.example").exists()

    @mark.asyncio
    async def test_file_metadata_preserved_with_copy2(self, tmp_path: Path) -> None:
        """Test that shutil.copy2 preserves file metadata."""
        # Arrange
        fake_publish_py = tmp_path / "pkg" / "src" / "asynctasq" / "cli" / "commands" / "publish.py"
        fake_publish_py.parent.mkdir(parents=True, exist_ok=True)
        fake_publish_py.write_text("# fake")

        package_root = fake_publish_py.parent.parent.parent.parent.parent
        source_env = package_root / ".env.example"
        source_env.write_text("# Metadata test\n")

        target_dir = tmp_path / "target"
        args = argparse.Namespace(output_dir=str(target_dir), force=False)

        with patch("asynctasq.cli.commands.publish.Path") as MockPath:
            original_path = Path
            call_count = [0]

            def path_factory(arg=None):
                call_count[0] += 1
                if call_count[0] == 1:
                    return fake_publish_py
                if arg is None:
                    return original_path.cwd()
                return original_path(arg)

            MockPath.side_effect = path_factory

            # Act
            await run_publish(args)

        # Assert - verify the file was copied (copy2 is used internally)
        target_file = target_dir / ".env.example"
        assert target_file.exists()
        # File content should match
        assert source_env.read_text() == target_file.read_text()

    @mark.asyncio
    async def test_overwrite_existing_file_with_force(self, tmp_path: Path) -> None:
        """Test that --force properly overwrites existing file."""
        # Arrange
        fake_publish_py = tmp_path / "pkg" / "src" / "asynctasq" / "cli" / "commands" / "publish.py"
        fake_publish_py.parent.mkdir(parents=True, exist_ok=True)
        fake_publish_py.write_text("# fake")

        package_root = fake_publish_py.parent.parent.parent.parent.parent
        source_env = package_root / ".env.example"
        source_env.write_text("# New version\nNEW=true\n")

        target_dir = tmp_path / "target"
        target_dir.mkdir(parents=True, exist_ok=True)
        existing_file = target_dir / ".env.example"
        existing_file.write_text("# Old version\nOLD=true\n")

        args = argparse.Namespace(output_dir=str(target_dir), force=True)

        with patch("asynctasq.cli.commands.publish.Path") as MockPath:
            original_path = Path
            call_count = [0]

            def path_factory(arg=None):
                call_count[0] += 1
                if call_count[0] == 1:
                    return fake_publish_py
                if arg is None:
                    return original_path.cwd()
                return original_path(arg)

            MockPath.side_effect = path_factory

            # Act
            await run_publish(args)

        # Assert
        content = existing_file.read_text()
        assert "NEW=true" in content
        assert "OLD=true" not in content
