"""Unit tests for CLI config utilities.

Testing Strategy:
- pytest 9.0.1 with asyncio_mode="auto" (no decorators needed)
- AAA pattern (Arrange, Act, Assert)
- Test config building from CLI arguments
- Mock Config.from_env() to avoid real environment dependencies
- Fast, isolated tests
"""

import argparse
from unittest.mock import MagicMock, patch

from pytest import main, mark

from asynctasq.cli.config import build_config, build_config_overrides


@mark.unit
class TestBuildConfigOverrides:
    """Test build_config_overrides() function."""

    def test_build_config_overrides_with_no_args(self) -> None:
        # Arrange
        args = argparse.Namespace()

        # Act
        result = build_config_overrides(args)

        # Assert
        assert result == {}

    def test_build_config_overrides_with_driver(self) -> None:
        # Arrange
        args = argparse.Namespace(driver="redis")

        # Act
        result = build_config_overrides(args)

        # Assert
        assert result == {"driver": "redis"}

    def test_build_config_overrides_with_redis_options(self) -> None:
        # Arrange
        args = argparse.Namespace(
            driver="redis",
            redis_url="redis://test:6379",
            redis_password="secret",
            redis_db=5,
            redis_max_connections=20,
        )

        # Act
        result = build_config_overrides(args)

        # Assert
        assert result == {
            "driver": "redis",
            "redis_url": "redis://test:6379",
            "redis_password": "secret",
            "redis_db": 5,
            "redis_max_connections": 20,
        }

    def test_build_config_overrides_with_sqs_options(self) -> None:
        # Arrange
        args = argparse.Namespace(
            driver="sqs",
            sqs_region="us-west-2",
            sqs_queue_url_prefix="https://sqs.us-west-2/",
            aws_access_key_id="key123",
            aws_secret_access_key="secret123",
        )

        # Act
        result = build_config_overrides(args)

        # Assert
        assert result == {
            "driver": "sqs",
            "sqs_region": "us-west-2",
            "sqs_queue_url_prefix": "https://sqs.us-west-2/",
            "aws_access_key_id": "key123",
            "aws_secret_access_key": "secret123",
        }

    def test_build_config_overrides_with_postgres_options(self) -> None:
        # Arrange
        args = argparse.Namespace(
            driver="postgres",
            postgres_dsn="postgresql://user:pass@localhost/db",
            postgres_queue_table="custom_queue",
            postgres_dead_letter_table="custom_dlq",
        )

        # Act
        result = build_config_overrides(args)

        # Assert
        assert result == {
            "driver": "postgres",
            "postgres_dsn": "postgresql://user:pass@localhost/db",
            "postgres_queue_table": "custom_queue",
            "postgres_dead_letter_table": "custom_dlq",
        }

    def test_build_config_overrides_ignores_none_values(self) -> None:
        # Arrange
        args = argparse.Namespace(
            driver="redis",
            redis_url="redis://test:6379",
            redis_password=None,
            redis_db=None,
            redis_max_connections=None,
        )

        # Act
        result = build_config_overrides(args)

        # Assert
        assert result == {
            "driver": "redis",
            "redis_url": "redis://test:6379",
        }

    def test_build_config_overrides_with_all_options(self) -> None:
        # Arrange
        args = argparse.Namespace(
            driver="postgres",
            redis_url="redis://test:6379",
            redis_password="secret",
            redis_db=3,
            redis_max_connections=15,
            sqs_region="us-east-1",
            sqs_queue_url_prefix="https://sqs.us-east-1/",
            aws_access_key_id="key",
            aws_secret_access_key="secret",
            postgres_dsn="postgresql://user:pass@localhost/db",
            postgres_queue_table="queue",
            postgres_dead_letter_table="dlq",
        )

        # Act
        result = build_config_overrides(args)

        # Assert
        assert len(result) == 12
        assert result["driver"] == "postgres"
        assert result["redis_url"] == "redis://test:6379"
        assert result["postgres_dsn"] == "postgresql://user:pass@localhost/db"

    def test_build_config_overrides_with_zero_values(self) -> None:
        # Arrange
        args = argparse.Namespace(
            driver="redis",
            redis_db=0,
            redis_max_connections=0,
        )

        # Act
        result = build_config_overrides(args)

        # Assert
        assert result == {
            "driver": "redis",
            "redis_db": 0,
            "redis_max_connections": 0,
        }

    def test_build_config_overrides_with_empty_strings(self) -> None:
        # Arrange
        args = argparse.Namespace(
            driver="redis",
            redis_url="",
            redis_password="",
        )

        # Act
        result = build_config_overrides(args)

        # Assert
        assert result == {
            "driver": "redis",
            "redis_url": "",
            "redis_password": "",
        }


@mark.unit
class TestBuildConfig:
    """Test build_config() function."""

    @patch("asynctasq.cli.config.Config.from_env")
    def test_build_config_calls_from_env_with_overrides(self, mock_from_env) -> None:
        # Arrange
        args = argparse.Namespace(driver="redis", redis_url="redis://test:6379")
        mock_config = MagicMock()
        mock_from_env.return_value = mock_config

        # Act
        result = build_config(args)

        # Assert
        mock_from_env.assert_called_once_with(
            driver="redis",
            redis_url="redis://test:6379",
        )
        assert result == mock_config

    @patch("asynctasq.cli.config.Config.from_env")
    def test_build_config_with_empty_args(self, mock_from_env) -> None:
        # Arrange
        args = argparse.Namespace()
        mock_config = MagicMock()
        mock_from_env.return_value = mock_config

        # Act
        result = build_config(args)

        # Assert
        mock_from_env.assert_called_once_with()
        assert result == mock_config

    @patch("asynctasq.cli.config.Config.from_env")
    def test_build_config_passes_all_overrides(self, mock_from_env) -> None:
        # Arrange
        args = argparse.Namespace(
            driver="postgres",
            postgres_dsn="postgresql://test",
            postgres_queue_table="queue",
            postgres_dead_letter_table="dlq",
        )
        mock_config = MagicMock()
        mock_from_env.return_value = mock_config

        # Act
        result = build_config(args)

        # Assert
        mock_from_env.assert_called_once_with(
            driver="postgres",
            postgres_dsn="postgresql://test",
            postgres_queue_table="queue",
            postgres_dead_letter_table="dlq",
        )
        assert result == mock_config


if __name__ == "__main__":
    main([__file__, "-s", "-m", "unit"])
