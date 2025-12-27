"""Unit tests for asynctasq.tasks.services.function_resolver module."""

import os
from pathlib import Path
import sys
import tempfile
from unittest.mock import MagicMock, patch

import pytest

from asynctasq.tasks.services.function_resolver import FunctionResolver


class TestFunctionResolver:
    """Test FunctionResolver class."""

    def setup_method(self):
        """Clear cache before each test."""
        FunctionResolver.clear_cache()

    def teardown_method(self):
        """Clean up after each test."""
        FunctionResolver.clear_cache()

    def test_get_module_regular_module(self):
        """Test get_module with regular module."""
        # Test with a standard library module
        module = FunctionResolver.get_module("os")
        assert module is not None
        assert hasattr(module, "path")

    def test_get_module_regular_module_from_file(self):
        """Test get_module loads regular module from file when not in path."""
        # Create a temporary Python file with a unique module name
        with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
            f.write("x = 42\n")
            temp_file = f.name

        try:
            # Use a module name that definitely doesn't exist
            module_name = f"definitely_not_importable_module_{id(self)}_{hash(temp_file)}"

            import builtins

            original_import = builtins.__import__
            import_called = []

            def mock_import(name, *args, **kwargs):
                import_called.append(name)
                try:
                    return original_import(name, *args, **kwargs)
                except ModuleNotFoundError:
                    import_called.append(f"failed: {name}")
                    raise

            with patch.object(builtins, "__import__", mock_import):
                module = FunctionResolver.get_module(module_name, temp_file)
                print(f"Import calls: {import_called}")
                assert module is not None
                assert hasattr(module, "x")
                assert module.x == 42
        finally:
            os.unlink(temp_file)

    def test_get_module_regular_module_from_file_cached(self):
        """Test get_module caches file-loaded modules."""
        # Create a temporary Python file
        with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
            f.write("CACHED_VAR = 'cached'\n")
            temp_file = f.name

        try:
            module_name = f"cached_module_{hash(temp_file)}"
            # Load first time
            module1 = FunctionResolver.get_module(module_name, temp_file)
            assert module1.CACHED_VAR == "cached"

            # Load second time - should use cache
            module2 = FunctionResolver.get_module(module_name, temp_file)
            assert module1 is module2  # Same instance from cache
        finally:
            os.unlink(temp_file)

    def test_get_module_regular_module_from_file_existing_in_sys_modules(self):
        """Test get_module uses module already in sys.modules."""
        # Create a temporary Python file
        with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
            f.write("SYS_MODULES_VAR = 'from sys.modules'\n")
            temp_file = f.name

        module_name = f"sys_modules_module_{hash(temp_file)}"
        try:
            # Manually add to sys.modules
            import types

            fake_module = types.ModuleType(module_name)
            fake_module.test_attr = "from sys.modules"  # type: ignore
            sys.modules[module_name] = fake_module

            # Should return the one from sys.modules
            module = FunctionResolver.get_module(module_name, temp_file)
            assert module is fake_module
            assert module.test_attr == "from sys.modules"  # type: ignore
        finally:
            sys.modules.pop(module_name, None)
            os.unlink(temp_file)

    @patch("importlib.util.spec_from_file_location")
    def test_get_module_regular_module_from_file_spec_failure(self, mock_spec_from_file):
        """Test get_module raises ImportError when spec creation fails."""
        mock_spec_from_file.return_value = None  # Spec is None

        # Create a temporary Python file
        with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
            f.write("SPEC_FAILURE_VAR = 'spec failed'\n")
            temp_file = f.name

        try:
            module_name = f"spec_failure_module_{hash(temp_file)}"
            with pytest.raises(ImportError, match="Failed to load spec"):
                FunctionResolver.get_module(module_name, temp_file)
        finally:
            os.unlink(temp_file)

    def test_get_module_main_without_file(self):
        """Test get_module with __main__ but no file raises ImportError."""
        with pytest.raises(
            ImportError, match="Cannot import from __main__ \\(missing module_file\\)"
        ):
            FunctionResolver.get_module("__main__")

    def test_get_module_main_nonexistent_file(self):
        """Test get_module with __main__ and nonexistent file raises FileNotFoundError."""
        with pytest.raises(FileNotFoundError, match="does not exist"):
            FunctionResolver.get_module("__main__", "/nonexistent/file.py")

    def test_get_module_main_cached(self):
        """Test get_module caches __main__ modules."""
        # Create a temporary Python file
        with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
            f.write("TEST_VAR = 'hello'\n")
            temp_file = f.name

        try:
            # First call should load and cache
            module1 = FunctionResolver.get_module("__main__", temp_file)

            # Second call should return cached version
            module2 = FunctionResolver.get_module("__main__", temp_file)

            # Should be the same object
            assert module1 is module2
            assert hasattr(module1, "TEST_VAR")
            assert module1.TEST_VAR == "hello"

        finally:
            Path(temp_file).unlink()

    def test_get_module_main_spec_failure(self):
        """Test get_module with spec creation failure."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
            temp_file = f.name

        try:
            with patch("importlib.util.spec_from_file_location", return_value=None):
                with pytest.raises(ImportError, match="Failed to load spec"):
                    FunctionResolver.get_module("__main__", temp_file)
        finally:
            Path(temp_file).unlink()

    def test_get_module_main_loader_failure(self):
        """Test get_module with loader failure."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
            temp_file = f.name

        try:
            mock_spec = MagicMock()
            mock_spec.loader = None

            with patch("importlib.util.spec_from_file_location", return_value=mock_spec):
                with pytest.raises(ImportError, match="Failed to load spec"):
                    FunctionResolver.get_module("__main__", temp_file)
        finally:
            Path(temp_file).unlink()

    def test_get_module_main_exec_runtime_error(self):
        """Test get_module with RuntimeError during exec."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
            f.write("# Test file\n")
            temp_file = f.name

        try:
            mock_spec = MagicMock()
            mock_loader = MagicMock()
            mock_loader.exec_module.side_effect = RuntimeError(
                "cannot be called from a running event loop"
            )
            mock_spec.loader = mock_loader

            with patch("importlib.util.spec_from_file_location", return_value=mock_spec):
                with pytest.raises(
                    RuntimeError, match="cannot be called from a running event loop"
                ):
                    FunctionResolver.get_module("__main__", temp_file)
        finally:
            Path(temp_file).unlink()

    def test_get_module_main_exec_general_error(self):
        """Test get_module with general exception during exec."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
            f.write("# Test file\n")
            temp_file = f.name

        try:
            mock_spec = MagicMock()
            mock_loader = MagicMock()
            mock_loader.exec_module.side_effect = ValueError("Some error")
            mock_spec.loader = mock_loader

            with patch("importlib.util.spec_from_file_location", return_value=mock_spec):
                with pytest.raises(ValueError, match="Some error"):
                    FunctionResolver.get_module("__main__", temp_file)
        finally:
            Path(temp_file).unlink()

    def test_get_module_main_existing_in_sys_modules(self):
        """Test get_module when module already exists in sys.modules."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
            f.write("TEST_VAR = 'existing'\n")
            temp_file = f.name

        internal_module_name = None
        try:
            # Simulate module already in sys.modules
            mock_module = MagicMock()
            mock_module.TEST_VAR = "existing"

            # Generate the internal module name that would be used
            cache_key = str(Path(temp_file).resolve())
            path_hash = __import__("hashlib").sha256(cache_key.encode()).hexdigest()[:16]
            internal_module_name = f"__asynctasq_main_{path_hash}__"

            sys.modules[internal_module_name] = mock_module

            module = FunctionResolver.get_module("__main__", temp_file)

            assert module is mock_module

        finally:
            Path(temp_file).unlink()
            # Clean up sys.modules
            if internal_module_name:
                sys.modules.pop(internal_module_name, None)

    def test_get_function_reference_regular_module(self):
        """Test get_function_reference with regular module."""
        func_ref = FunctionResolver.get_function_reference("os", "path")
        assert func_ref is not None

    def test_get_function_reference_main_module(self):
        """Test get_function_reference with __main__ module."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
            f.write("def test_func():\n    return 'test'\n")
            temp_file = f.name

        try:
            func_ref = FunctionResolver.get_function_reference("__main__", "test_func", temp_file)
            assert callable(func_ref)
            assert func_ref() == "test"
        finally:
            Path(temp_file).unlink()

    def test_get_module_regular_module_from_file_spec_none(self):
        """Test get_module with regular module from file when spec is None."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
            f.write("def test_func():\n    return 'test'\n")
            temp_file = f.name

        try:
            with patch(
                "builtins.__import__",
                side_effect=ModuleNotFoundError("No module named 'test_module'"),
            ):
                with patch("importlib.util.spec_from_file_location", return_value=None):
                    with pytest.raises(ImportError, match="Failed to load spec"):
                        FunctionResolver.get_module("test_module", module_file=temp_file)
        finally:
            Path(temp_file).unlink()

    def test_get_module_regular_module_from_file_loader_none(self):
        """Test get_module with regular module from file when spec.loader is None."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
            f.write("def test_func():\n    return 'test'\n")
            temp_file = f.name

        try:
            mock_spec = MagicMock()
            mock_spec.loader = None
            with patch(
                "builtins.__import__",
                side_effect=ModuleNotFoundError("No module named 'test_module'"),
            ):
                with patch("importlib.util.spec_from_file_location", return_value=mock_spec):
                    with pytest.raises(ImportError, match="Failed to load spec"):
                        FunctionResolver.get_module("test_module", module_file=temp_file)
        finally:
            Path(temp_file).unlink()

    def test_get_module_regular_module_from_file_exec_module_not_found_error(self):
        """Test get_module with regular module from file when exec_module raises ModuleNotFoundError."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
            f.write("def test_func():\n    return 'test'\n")
            temp_file = f.name

        try:
            mock_spec = MagicMock()
            mock_loader = MagicMock()
            mock_spec.loader = mock_loader
            mock_loader.exec_module.side_effect = ModuleNotFoundError("missing_module")

            with patch(
                "builtins.__import__",
                side_effect=ModuleNotFoundError("No module named 'test_module'"),
            ):
                with patch("importlib.util.spec_from_file_location", return_value=mock_spec):
                    with patch("importlib.util.module_from_spec") as mock_module_from_spec:
                        mock_module = MagicMock()
                        mock_module_from_spec.return_value = mock_module
                        with pytest.raises(ImportError, match="has missing dependencies"):
                            FunctionResolver.get_module("test_module", module_file=temp_file)
        finally:
            Path(temp_file).unlink()

    def test_get_module_regular_module_from_file_exec_module_general_error(self):
        """Test get_module with regular module from file when exec_module raises general Exception."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
            f.write("def test_func():\n    return 'test'\n")
            temp_file = f.name

        try:
            mock_spec = MagicMock()
            mock_loader = MagicMock()
            mock_spec.loader = mock_loader
            mock_loader.exec_module.side_effect = ValueError("some error")

            with patch(
                "builtins.__import__",
                side_effect=ModuleNotFoundError("No module named 'test_module'"),
            ):
                with patch("importlib.util.spec_from_file_location", return_value=mock_spec):
                    with patch("importlib.util.module_from_spec") as mock_module_from_spec:
                        mock_module = MagicMock()
                        mock_module_from_spec.return_value = mock_module
                        with pytest.raises(ValueError, match="some error"):
                            FunctionResolver.get_module("test_module", module_file=temp_file)
        finally:
            Path(temp_file).unlink()

    def test_get_module_regular_module_no_file_reraise_error(self):
        """Test get_module with regular module when __import__ fails and no module_file provided."""
        with patch(
            "builtins.__import__",
            side_effect=ModuleNotFoundError("No module named 'nonexistent_module'"),
        ):
            with pytest.raises(ModuleNotFoundError, match="No module named 'nonexistent_module'"):
                FunctionResolver.get_module("nonexistent_module", module_file=None)

    def test_clear_cache(self):
        """Test clear_cache method."""
        # Add something to cache
        FunctionResolver._module_cache["test"] = "value"

        FunctionResolver.clear_cache()

        assert len(FunctionResolver._module_cache) == 0
