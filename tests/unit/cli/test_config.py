"""Unit tests for CLI config utilities.

Testing Strategy:
- pytest 9.0.1 with asyncio_mode="auto" (no decorators needed)
- AAA pattern (Arrange, Act, Assert)
- Test config building from CLI arguments
- Mock Config() to avoid real dependencies
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
        from asynctasq.config import RedisConfig

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
        assert result["driver"] == "redis"
        assert isinstance(result["redis"], RedisConfig)
        assert result["redis"].url == "redis://test:6379"
        assert result["redis"].password == "secret"
        assert result["redis"].db == 5
        assert result["redis"].max_connections == 20

    def test_build_config_overrides_with_sqs_options(self) -> None:
        # Arrange
        from asynctasq.config import SQSConfig

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
        assert result["driver"] == "sqs"
        assert isinstance(result["sqs"], SQSConfig)
        assert result["sqs"].region == "us-west-2"
        assert result["sqs"].queue_url_prefix == "https://sqs.us-west-2/"
        assert result["sqs"].aws_access_key_id == "key123"
        assert result["sqs"].aws_secret_access_key == "secret123"

    def test_build_config_overrides_ignores_none_values(self) -> None:
        # Arrange
        from asynctasq.config import RedisConfig

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
        assert result["driver"] == "redis"
        assert isinstance(result["redis"], RedisConfig)
        assert result["redis"].url == "redis://test:6379"
        # None values are not passed to RedisConfig, so they use defaults
        assert result["redis"].password is None  # default
        assert result["redis"].db == 0  # default
        assert result["redis"].max_connections == 100  # default

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

        # Assert - should have driver, postgres, redis, and sqs config objects
        assert len(result) == 4
        assert result["driver"] == "postgres"
        assert "postgres" in result
        assert "redis" in result
        assert "sqs" in result

    def test_build_config_overrides_with_zero_values(self) -> None:
        # Arrange - test that zero is preserved for db (valid) but max_connections must be > 0
        from asynctasq.config import RedisConfig

        args = argparse.Namespace(
            driver="redis",
            redis_db=0,  # 0 is valid for db
            redis_max_connections=1,  # Must be > 0
        )

        # Act
        result = build_config_overrides(args)

        # Assert
        assert result["driver"] == "redis"
        assert isinstance(result["redis"], RedisConfig)
        assert result["redis"].db == 0  # Zero value is preserved
        assert result["redis"].max_connections == 1

    def test_build_config_overrides_with_empty_strings(self) -> None:
        # Arrange
        from asynctasq.config import RedisConfig

        args = argparse.Namespace(
            driver="redis",
            redis_url="",
            redis_password="",
        )

        # Act
        result = build_config_overrides(args)

        # Assert
        assert result["driver"] == "redis"
        assert isinstance(result["redis"], RedisConfig)
        assert result["redis"].url == ""
        assert result["redis"].password == ""

    def test_build_config_overrides_with_mysql_options(self) -> None:
        # Arrange
        from asynctasq.config import MySQLConfig

        args = argparse.Namespace(
            driver="mysql",
            mysql_dsn="mysql://user:pass@localhost/db",
            mysql_queue_table="custom_queue",
            mysql_dead_letter_table="custom_dlq",
            mysql_max_attempts=3,
            mysql_min_pool_size=1,
            mysql_max_pool_size=10,
        )

        # Act
        result = build_config_overrides(args)

        # Assert
        assert result["driver"] == "mysql"
        assert isinstance(result["mysql"], MySQLConfig)
        assert result["mysql"].dsn == "mysql://user:pass@localhost/db"
        assert result["mysql"].queue_table == "custom_queue"
        assert result["mysql"].dead_letter_table == "custom_dlq"
        assert result["mysql"].max_attempts == 3
        assert result["mysql"].min_pool_size == 1
        assert result["mysql"].max_pool_size == 10

    def test_build_config_overrides_with_postgres_options_missing_attributes(self) -> None:
        # Arrange - test hasattr checks when postgres attributes are missing
        from asynctasq.config import PostgresConfig

        # Create args object without postgres attributes
        args = argparse.Namespace(
            driver="postgres",
            postgres_dsn="postgresql://user:pass@localhost/db",
            # Note: postgres_queue_table, postgres_dead_letter_table, postgres_max_attempts are missing
        )

        # Act
        result = build_config_overrides(args)

        # Assert
        assert result["driver"] == "postgres"
        assert isinstance(result["postgres"], PostgresConfig)
        assert result["postgres"].dsn == "postgresql://user:pass@localhost/db"
        # Other postgres attributes should use defaults since hasattr returns False
        assert result["postgres"].queue_table == "task_queue"
        assert result["postgres"].dead_letter_table == "dead_letter_queue"
        assert result["postgres"].max_attempts == 3

    def test_build_config_overrides_with_mysql_partial_options(self) -> None:
        # Arrange - test mysql options without driver to ensure hasattr checks are covered
        from asynctasq.config import MySQLConfig

        args = argparse.Namespace(
            mysql_dsn="mysql://user:pass@localhost/db",
            mysql_queue_table="custom_queue",
            # Don't set all mysql attributes to test partial coverage
        )

        # Act
        result = build_config_overrides(args)

        # Assert
        assert "mysql" in result
        assert isinstance(result["mysql"], MySQLConfig)
        assert result["mysql"].dsn == "mysql://user:pass@localhost/db"
        assert result["mysql"].queue_table == "custom_queue"
        # Others should use defaults
        assert result["mysql"].dead_letter_table == "dead_letter_queue"
        assert result["mysql"].max_attempts == 3

    def test_build_config_overrides_with_rabbitmq_options(self) -> None:
        # Arrange
        from asynctasq.config import RabbitMQConfig

        args = argparse.Namespace(
            driver="rabbitmq",
            rabbitmq_url="amqp://guest:guest@localhost:5672/",
            rabbitmq_exchange_name="custom_exchange",
            rabbitmq_prefetch_count=10,
        )

        # Act
        result = build_config_overrides(args)

        # Assert
        assert result["driver"] == "rabbitmq"
        assert isinstance(result["rabbitmq"], RabbitMQConfig)
        assert result["rabbitmq"].url == "amqp://guest:guest@localhost:5672/"
        assert result["rabbitmq"].exchange_name == "custom_exchange"
        assert result["rabbitmq"].prefetch_count == 10

    def test_build_config_overrides_with_events_options(self) -> None:
        # Arrange
        from asynctasq.config import EventsConfig

        args = argparse.Namespace(
            events_redis_url="redis://events:6379",
            events_channel="custom_channel",
            events_enable_event_emitter_redis=True,
        )

        # Act
        result = build_config_overrides(args)

        # Assert
        assert isinstance(result["events"], EventsConfig)
        assert result["events"].redis_url == "redis://events:6379"
        assert result["events"].channel == "custom_channel"
        assert result["events"].enable_event_emitter_redis is True

    def test_build_config_overrides_with_task_defaults_options(self) -> None:
        # Arrange
        from asynctasq.config import TaskDefaultsConfig

        args = argparse.Namespace(
            task_defaults_queue="custom_queue",
            task_defaults_max_attempts=5,
            task_defaults_retry_strategy="exponential",
            task_defaults_retry_delay=30,
        )

        # Act
        result = build_config_overrides(args)

        # Assert
        assert isinstance(result["task_defaults"], TaskDefaultsConfig)
        assert result["task_defaults"].queue == "custom_queue"
        assert result["task_defaults"].max_attempts == 5
        assert result["task_defaults"].retry_strategy == "exponential"
        assert result["task_defaults"].retry_delay == 30

    def test_build_config_overrides_with_process_pool_options(self) -> None:
        # Arrange
        from asynctasq.config import ProcessPoolConfig

        args = argparse.Namespace(
            process_pool_size=4,
            process_pool_max_tasks_per_child=100,
        )

        # Act
        result = build_config_overrides(args)

        # Assert
        assert isinstance(result["process_pool"], ProcessPoolConfig)
        assert result["process_pool"].size == 4
        assert result["process_pool"].max_tasks_per_child == 100

    def test_build_config_overrides_with_repository_options(self) -> None:
        # Arrange
        from asynctasq.config import RepositoryConfig

        args = argparse.Namespace(
            repository_keep_completed_tasks=True,
        )

        # Act
        result = build_config_overrides(args)

        # Assert
        assert isinstance(result["repository"], RepositoryConfig)
        assert result["repository"].keep_completed_tasks is True

    def test_build_config_overrides_handles_missing_attributes(self) -> None:
        # Arrange - test that hasattr checks work when attributes don't exist
        args = argparse.Namespace()
        # Don't add any attributes that are checked with hasattr

        # Act
        result = build_config_overrides(args)

        # Assert - should return empty dict since no attributes exist
        assert result == {}

    def test_build_config_overrides_with_partial_attributes(self) -> None:
        # Arrange - test when some attributes exist but not all
        from asynctasq.config import RedisConfig

        args = argparse.Namespace()
        # Add only some redis attributes
        args.redis_url = "redis://test:6379"
        args.redis_db = 5
        # Don't add redis_password, redis_max_connections

        # Act
        result = build_config_overrides(args)

        # Assert - should include redis config with only the provided attributes
        assert "redis" in result
        assert isinstance(result["redis"], RedisConfig)
        assert result["redis"].url == "redis://test:6379"
        assert result["redis"].db == 5
        # None values should use defaults
        assert result["redis"].password is None
        assert result["redis"].max_connections == 100


@mark.unit
class TestBuildConfig:
    """Test build_config() function."""

    @patch("asynctasq.cli.config.Config")
    def test_build_config_calls_config_with_overrides(self, mock_config_class) -> None:
        # Arrange
        from asynctasq.config import RedisConfig

        args = argparse.Namespace(driver="redis", redis_url="redis://test:6379")
        mock_config = MagicMock()
        mock_config_class.return_value = mock_config

        # Act
        result = build_config(args)

        # Assert
        assert mock_config_class.call_count == 1
        call_kwargs = mock_config_class.call_args.kwargs
        assert call_kwargs["driver"] == "redis"
        assert isinstance(call_kwargs["redis"], RedisConfig)
        assert call_kwargs["redis"].url == "redis://test:6379"
        assert result == mock_config

    @patch("asynctasq.cli.config.Config")
    def test_build_config_with_empty_args(self, mock_config_class) -> None:
        # Arrange
        args = argparse.Namespace()
        mock_config = MagicMock()
        mock_config_class.return_value = mock_config

        # Act
        result = build_config(args)

        # Assert
        mock_config_class.assert_called_once_with()
        assert result == mock_config

    @patch("asynctasq.cli.config.Config")
    def test_build_config_passes_all_overrides(self, mock_config_class) -> None:
        # Arrange
        from asynctasq.config import PostgresConfig

        args = argparse.Namespace(
            driver="postgres",
            postgres_dsn="postgresql://test",
            postgres_queue_table="queue",
            postgres_dead_letter_table="dlq",
        )
        mock_config = MagicMock()
        mock_config_class.return_value = mock_config

        # Act
        result = build_config(args)

        # Assert
        assert mock_config_class.call_count == 1
        call_kwargs = mock_config_class.call_args.kwargs
        assert call_kwargs["driver"] == "postgres"
        assert isinstance(call_kwargs["postgres"], PostgresConfig)
        assert call_kwargs["postgres"].dsn == "postgresql://test"
        assert call_kwargs["postgres"].queue_table == "queue"
        assert call_kwargs["postgres"].dead_letter_table == "dlq"
        assert result == mock_config


if __name__ == "__main__":
    main([__file__, "-s", "-m", "unit"])
