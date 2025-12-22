"""Unit tests for type_guards module.

Testing Strategy:
- pytest 9.0.1 with asyncio_mode="auto"
- Test all type guard functions with various inputs
- Test edge cases including TypeError handling
- Mock imports to avoid circular dependencies
"""

from pytest import main, mark

from asynctasq.tasks.core.base_task import BaseTask
from asynctasq.tasks.types.function_task import FunctionTask
from asynctasq.tasks.utils.type_guards import is_function_task_class, is_function_task_instance


@mark.unit
class TestIsFunctionTaskInstance:
    """Test is_function_task_instance type guard."""

    def test_returns_true_for_function_task_instance(self) -> None:
        # Arrange
        def sample_func() -> int:
            return 42

        task = FunctionTask(sample_func)

        # Act
        result = is_function_task_instance(task)

        # Assert
        assert result is True

    def test_returns_false_for_base_task_instance(self) -> None:
        # Arrange
        class CustomTask(BaseTask[int]):
            async def run(self) -> int:
                return 42

        task = CustomTask()

        # Act
        result = is_function_task_instance(task)

        # Assert
        assert result is False

    def test_returns_false_for_non_task_object(self) -> None:
        # Arrange
        non_task = "not a task"

        # Act
        result = is_function_task_instance(non_task)  # type: ignore[arg-type]

        # Assert
        assert result is False


@mark.unit
class TestIsFunctionTaskClass:
    """Test is_function_task_class type guard."""

    def test_returns_true_for_function_task_class(self) -> None:
        # Arrange / Act
        result = is_function_task_class(FunctionTask)

        # Assert
        assert result is True

    def test_returns_false_for_base_task_class(self) -> None:
        # Arrange / Act
        result = is_function_task_class(BaseTask)

        # Assert
        assert result is False

    def test_returns_false_for_other_task_subclass(self) -> None:
        # Arrange
        class CustomTask(BaseTask[int]):
            async def run(self) -> int:
                return 42

        # Act
        result = is_function_task_class(CustomTask)

        # Assert
        assert result is False

    def test_returns_false_for_non_class_object(self) -> None:
        # Arrange
        non_class = "not a class"

        # Act
        result = is_function_task_class(non_class)  # type: ignore[arg-type]

        # Assert
        assert result is False

    def test_returns_false_for_none(self) -> None:
        # Arrange / Act
        result = is_function_task_class(None)  # type: ignore[arg-type]

        # Assert
        assert result is False

    def test_returns_false_for_integer(self) -> None:
        # Arrange / Act
        result = is_function_task_class(42)  # type: ignore[arg-type]

        # Assert
        assert result is False

    def test_returns_false_for_dict(self) -> None:
        # Arrange / Act
        result = is_function_task_class({"key": "value"})  # type: ignore[arg-type]

        # Assert
        assert result is False

    def test_returns_false_for_list(self) -> None:
        # Arrange / Act
        result = is_function_task_class([1, 2, 3])  # type: ignore[arg-type]

        # Assert
        assert result is False


if __name__ == "__main__":
    main([__file__, "-s", "-m", "unit"])
