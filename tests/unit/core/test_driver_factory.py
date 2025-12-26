"""Unit tests for DriverFactory.

Testing Strategy:
- pytest 9.0.1 with asyncio_mode="auto" (no decorators needed)
- AAA pattern (Arrange, Act, Assert)
- Test behavior over implementation details
- Mock driver instantiation to avoid real connections
- Fast, isolated tests
"""

from typing import Any, get_args
from unittest.mock import MagicMock, patch

from pytest import main, mark, raises

from asynctasq.config import (
    Config,
    MySQLConfig,
    PostgresConfig,
    RabbitMQConfig,
    RedisConfig,
    RepositoryConfig,
    SQSConfig,
    TaskDefaultsConfig,
)
from asynctasq.core.driver_factory import DriverFactory
from asynctasq.drivers import DriverType
from asynctasq.drivers.mysql_driver import MySQLDriver
from asynctasq.drivers.postgres_driver import PostgresDriver
from asynctasq.drivers.rabbitmq_driver import RabbitMQDriver
from asynctasq.drivers.redis_driver import RedisDriver
from asynctasq.drivers.sqs_driver import SQSDriver


@mark.unit
class TestDriverFactoryCreateFromConfig:
    """Test DriverFactory.create_from_config() method."""

    @patch("asynctasq.drivers.redis_driver.RedisDriver")
    def test_create_from_config_with_redis_driver(self, mock_redis: MagicMock) -> None:
        # Arrange
        config = Config(
            driver="redis",
            redis=RedisConfig(
                url="redis://test:6379",
                password="secret123",
                db=5,
                max_connections=20,
            ),
        )
        mock_instance = MagicMock(spec=RedisDriver)
        mock_redis.return_value = mock_instance

        # Act
        result = DriverFactory.create_from_config(config)

        # Assert
        mock_redis.assert_called_once_with(
            url="redis://test:6379",
            password="secret123",
            db=5,
            max_connections=20,
            keep_completed_tasks=False,
        )
        assert result == mock_instance

    @patch("asynctasq.drivers.sqs_driver.SQSDriver")
    def test_create_from_config_with_sqs_driver(self, mock_sqs: MagicMock) -> None:
        # Arrange
        config = Config(
            driver="sqs",
            sqs=SQSConfig(
                region="us-west-2",
                queue_url_prefix="https://sqs.us-west-2.amazonaws.com/123456789/",
                aws_access_key_id="test_key_id",
                aws_secret_access_key="test_secret_key",
            ),
        )
        mock_instance = MagicMock(spec=SQSDriver)
        mock_sqs.return_value = mock_instance

        # Act
        result = DriverFactory.create_from_config(config)

        # Assert
        mock_sqs.assert_called_once_with(
            region_name="us-west-2",
            queue_url_prefix="https://sqs.us-west-2.amazonaws.com/123456789/",
            aws_access_key_id="test_key_id",
            aws_secret_access_key="test_secret_key",
            endpoint_url=None,
        )
        assert result == mock_instance

    @patch("asynctasq.drivers.postgres_driver.PostgresDriver")
    def test_create_from_config_with_postgres_driver(self, mock_postgres: MagicMock) -> None:
        # Arrange
        config = Config(
            driver="postgres",
            postgres=PostgresConfig(
                dsn="postgresql://user:pass@testdb:5432/taskdb",
                queue_table="custom_queue",
                dead_letter_table="custom_dlq",
                max_attempts=5,
                min_pool_size=5,
                max_pool_size=20,
            ),
            task_defaults=TaskDefaultsConfig(
                retry_strategy="exponential",
                retry_delay=120,
                visibility_timeout=600,
            ),
        )
        mock_instance = MagicMock(spec=PostgresDriver)
        mock_postgres.return_value = mock_instance

        # Act
        result = DriverFactory.create_from_config(config)

        # Assert
        mock_postgres.assert_called_once_with(
            dsn="postgresql://user:pass@testdb:5432/taskdb",
            queue_table="custom_queue",
            dead_letter_table="custom_dlq",
            max_attempts=5,
            retry_delay_seconds=120,
            visibility_timeout_seconds=600,
            min_pool_size=5,
            max_pool_size=20,
            keep_completed_tasks=False,
        )
        assert result == mock_instance

    @patch("asynctasq.drivers.mysql_driver.MySQLDriver")
    def test_create_from_config_with_mysql_driver(self, mock_mysql: MagicMock) -> None:
        # Arrange
        config = Config(
            driver="mysql",
            mysql=MySQLConfig(
                dsn="mysql://user:pass@testdb:3306/taskdb",
                queue_table="custom_queue",
                dead_letter_table="custom_dlq",
                max_attempts=5,
                min_pool_size=5,
                max_pool_size=20,
            ),
            task_defaults=TaskDefaultsConfig(
                retry_strategy="exponential",
                retry_delay=120,
                visibility_timeout=600,
            ),
        )
        mock_instance = MagicMock(spec=MySQLDriver)
        mock_mysql.return_value = mock_instance

        # Act
        result = DriverFactory.create_from_config(config)

        # Assert
        mock_mysql.assert_called_once_with(
            dsn="mysql://user:pass@testdb:3306/taskdb",
            queue_table="custom_queue",
            dead_letter_table="custom_dlq",
            max_attempts=5,
            retry_delay_seconds=120,
            visibility_timeout_seconds=600,
            min_pool_size=5,
            max_pool_size=20,
            keep_completed_tasks=False,
        )
        assert result == mock_instance

    @patch("asynctasq.drivers.postgres_driver.PostgresDriver")
    @patch("asynctasq.drivers.redis_driver.RedisDriver")
    def test_create_from_config_with_driver_type_override(
        self, mock_redis: MagicMock, mock_postgres: MagicMock
    ) -> None:
        # Arrange
        config = Config(
            driver="redis",
            redis=RedisConfig(),
        )  # Config says redis
        mock_instance = MagicMock(spec=PostgresDriver)
        mock_postgres.return_value = mock_instance

        # Act - override with postgres driver
        result = DriverFactory.create_from_config(config, driver_type="postgres")

        # Assert
        mock_postgres.assert_called_once()
        mock_redis.assert_not_called()  # Redis should not be called
        assert result == mock_instance

    @patch("asynctasq.drivers.postgres_driver.PostgresDriver")
    @patch("asynctasq.drivers.sqs_driver.SQSDriver")
    def test_create_from_config_override_sqs_with_postgres(
        self, mock_sqs: MagicMock, mock_postgres: MagicMock
    ) -> None:
        # Arrange
        config = Config(
            driver="sqs",
            sqs=SQSConfig(),
            postgres=PostgresConfig(
                dsn="postgresql://override:pass@localhost/db",
            ),
        )
        mock_instance = MagicMock(spec=PostgresDriver)
        mock_postgres.return_value = mock_instance

        # Act
        result = DriverFactory.create_from_config(config, driver_type="postgres")

        # Assert
        mock_postgres.assert_called_once()
        mock_sqs.assert_not_called()
        assert result == mock_instance

    @patch("asynctasq.drivers.mysql_driver.MySQLDriver")
    @patch("asynctasq.drivers.postgres_driver.PostgresDriver")
    def test_create_from_config_override_postgres_with_mysql(
        self, mock_postgres: MagicMock, mock_mysql: MagicMock
    ) -> None:
        # Arrange
        config = Config(
            driver="postgres",
            postgres=PostgresConfig(),
            mysql=MySQLConfig(
                dsn="mysql://override:pass@localhost:3306/db",
            ),
        )
        mock_instance = MagicMock(spec=MySQLDriver)
        mock_mysql.return_value = mock_instance

        # Act
        result = DriverFactory.create_from_config(config, driver_type="mysql")

        # Assert
        mock_mysql.assert_called_once()
        mock_postgres.assert_not_called()
        assert result == mock_instance

    @patch("asynctasq.drivers.mysql_driver.MySQLDriver")
    @patch("asynctasq.drivers.redis_driver.RedisDriver")
    def test_create_from_config_override_mysql_with_redis(
        self, mock_redis: MagicMock, mock_mysql: MagicMock
    ) -> None:
        # Arrange
        config = Config(
            driver="mysql",
            mysql=MySQLConfig(),
            redis=RedisConfig(
                url="redis://override:6379",
            ),
        )
        mock_instance = MagicMock(spec=RedisDriver)
        mock_redis.return_value = mock_instance

        # Act
        result = DriverFactory.create_from_config(config, driver_type="redis")

        # Assert
        mock_redis.assert_called_once()
        mock_mysql.assert_not_called()
        assert result == mock_instance

    @patch("asynctasq.drivers.rabbitmq_driver.RabbitMQDriver")
    def test_create_from_config_with_rabbitmq_driver(self, mock_rabbitmq: MagicMock) -> None:
        # Arrange
        config = Config(
            driver="rabbitmq",
            rabbitmq=RabbitMQConfig(
                url="amqp://user:pass@rabbitmq:5672/vhost",
                exchange_name="test_exchange",
                prefetch_count=10,
            ),
        )
        mock_instance = MagicMock(spec=RabbitMQDriver)
        mock_rabbitmq.return_value = mock_instance

        # Act
        result = DriverFactory.create_from_config(config)

        # Assert
        mock_rabbitmq.assert_called_once_with(
            url="amqp://user:pass@rabbitmq:5672/vhost",
            exchange_name="test_exchange",
            prefetch_count=10,
            keep_completed_tasks=False,
        )
        assert result == mock_instance


@mark.unit
class TestDriverFactoryCreate:
    """Test DriverFactory.create() method with different driver types."""

    @patch("asynctasq.drivers.redis_driver.RedisDriver")
    def test_create_redis_driver_with_defaults(self, mock_redis: MagicMock) -> None:
        # Arrange
        mock_instance = MagicMock(spec=RedisDriver)
        mock_redis.return_value = mock_instance
        config = Config()

        # Act
        result = DriverFactory.create("redis", config)

        # Assert
        mock_redis.assert_called_once_with(
            url="redis://localhost:6379",
            password=None,
            db=0,
            max_connections=100,
            keep_completed_tasks=False,
        )
        assert result == mock_instance

    @patch("asynctasq.drivers.redis_driver.RedisDriver")
    def test_create_redis_driver_with_custom_params(self, mock_redis: MagicMock) -> None:
        # Arrange
        mock_instance = MagicMock(spec=RedisDriver)
        mock_redis.return_value = mock_instance
        config = Config(
            redis=RedisConfig(
                url="redis://custom.host:6380",
                password="custom_pass",
                db=3,
                max_connections=50,
            )
        )

        # Act
        result = DriverFactory.create("redis", config)

        # Assert
        mock_redis.assert_called_once_with(
            url="redis://custom.host:6380",
            password="custom_pass",
            db=3,
            max_connections=50,
            keep_completed_tasks=False,
        )
        assert result == mock_instance

    @patch("asynctasq.drivers.sqs_driver.SQSDriver")
    def test_create_sqs_driver_with_defaults(self, mock_sqs: MagicMock) -> None:
        # Arrange
        mock_instance = MagicMock(spec=SQSDriver)
        mock_sqs.return_value = mock_instance
        config = Config()

        # Act
        result = DriverFactory.create("sqs", config)

        # Assert
        mock_sqs.assert_called_once_with(
            region_name="us-east-1",
            queue_url_prefix=None,
            aws_access_key_id=None,
            aws_secret_access_key=None,
            endpoint_url=None,
        )
        assert result == mock_instance

    @patch("asynctasq.drivers.sqs_driver.SQSDriver")
    def test_create_sqs_driver_with_custom_params(self, mock_sqs: MagicMock) -> None:
        # Arrange
        mock_instance = MagicMock(spec=SQSDriver)
        mock_sqs.return_value = mock_instance
        config = Config(
            sqs=SQSConfig(
                region="eu-west-1",
                queue_url_prefix="https://sqs.eu-west-1.amazonaws.com/987654321/",
                aws_access_key_id="custom_key",
                aws_secret_access_key="custom_secret",
            )
        )

        # Act
        result = DriverFactory.create("sqs", config)

        # Assert
        mock_sqs.assert_called_once_with(
            region_name="eu-west-1",
            queue_url_prefix="https://sqs.eu-west-1.amazonaws.com/987654321/",
            aws_access_key_id="custom_key",
            aws_secret_access_key="custom_secret",
            endpoint_url=None,
        )
        assert result == mock_instance

    @patch("asynctasq.drivers.postgres_driver.PostgresDriver")
    def test_create_postgres_driver_with_defaults(self, mock_postgres: MagicMock) -> None:
        # Arrange
        mock_instance = MagicMock(spec=PostgresDriver)
        mock_postgres.return_value = mock_instance
        config = Config()

        # Act
        result = DriverFactory.create("postgres", config)

        # Assert
        mock_postgres.assert_called_once_with(
            dsn="postgresql://test:test@localhost:5432/test_db",
            queue_table="task_queue",
            dead_letter_table="dead_letter_queue",
            max_attempts=3,
            retry_delay_seconds=60,
            visibility_timeout_seconds=300,
            min_pool_size=10,
            max_pool_size=10,
            keep_completed_tasks=False,
        )
        assert result == mock_instance

    @patch("asynctasq.drivers.postgres_driver.PostgresDriver")
    def test_create_postgres_driver_with_custom_params(self, mock_postgres: MagicMock) -> None:
        # Arrange
        mock_instance = MagicMock(spec=PostgresDriver)
        mock_postgres.return_value = mock_instance
        config = Config(
            postgres=PostgresConfig(
                dsn="postgresql://admin:secret@db.example.com:5432/prod",
                queue_table="production_queue",
                dead_letter_table="production_dlq",
                max_attempts=10,
                min_pool_size=20,
                max_pool_size=100,
            ),
            task_defaults=TaskDefaultsConfig(
                retry_delay=300,
                visibility_timeout=1800,
            ),
        )

        # Act
        result = DriverFactory.create("postgres", config)

        # Assert
        mock_postgres.assert_called_once_with(
            dsn="postgresql://admin:secret@db.example.com:5432/prod",
            queue_table="production_queue",
            dead_letter_table="production_dlq",
            max_attempts=10,
            retry_delay_seconds=300,
            visibility_timeout_seconds=1800,
            min_pool_size=20,
            max_pool_size=100,
            keep_completed_tasks=False,
        )
        assert result == mock_instance

    @patch("asynctasq.drivers.mysql_driver.MySQLDriver")
    def test_create_mysql_driver_with_defaults(self, mock_mysql: MagicMock) -> None:
        # Arrange
        mock_instance = MagicMock(spec=MySQLDriver)
        mock_mysql.return_value = mock_instance
        config = Config()

        # Act
        result = DriverFactory.create("mysql", config)

        # Assert
        mock_mysql.assert_called_once_with(
            dsn="mysql://test:test@localhost:3306/test_db",
            queue_table="task_queue",
            dead_letter_table="dead_letter_queue",
            max_attempts=3,
            retry_delay_seconds=60,
            visibility_timeout_seconds=300,
            min_pool_size=10,
            max_pool_size=10,
            keep_completed_tasks=False,
        )
        assert result == mock_instance

    @patch("asynctasq.drivers.mysql_driver.MySQLDriver")
    def test_create_mysql_driver_with_custom_params(self, mock_mysql: MagicMock) -> None:
        # Arrange
        mock_instance = MagicMock(spec=MySQLDriver)
        mock_mysql.return_value = mock_instance
        config = Config(
            mysql=MySQLConfig(
                dsn="mysql://admin:secret@db.example.com:3306/prod",
                queue_table="production_queue",
                dead_letter_table="production_dlq",
                max_attempts=10,
                min_pool_size=20,
                max_pool_size=100,
            ),
            task_defaults=TaskDefaultsConfig(
                retry_delay=300,
                visibility_timeout=1800,
            ),
        )

        # Act
        result = DriverFactory.create("mysql", config)

        # Assert
        mock_mysql.assert_called_once_with(
            dsn="mysql://admin:secret@db.example.com:3306/prod",
            queue_table="production_queue",
            dead_letter_table="production_dlq",
            max_attempts=10,
            retry_delay_seconds=300,
            visibility_timeout_seconds=1800,
            min_pool_size=20,
            max_pool_size=100,
            keep_completed_tasks=False,
        )
        assert result == mock_instance


@mark.unit
class TestDriverFactoryCreateRabbitMQ:
    """Test DriverFactory.create() method for RabbitMQ driver."""

    @patch("asynctasq.drivers.rabbitmq_driver.RabbitMQDriver")
    def test_create_rabbitmq_driver_with_defaults(self, mock_rabbitmq: MagicMock) -> None:
        # Arrange
        mock_instance = MagicMock(spec=RabbitMQDriver)
        mock_rabbitmq.return_value = mock_instance
        config = Config()

        # Act
        result = DriverFactory.create("rabbitmq", config)

        # Assert
        mock_rabbitmq.assert_called_once_with(
            url="amqp://guest:guest@localhost:5672/",
            exchange_name="asynctasq",
            prefetch_count=1,
            keep_completed_tasks=False,
        )
        assert result == mock_instance

    @patch("asynctasq.drivers.rabbitmq_driver.RabbitMQDriver")
    def test_create_rabbitmq_driver_with_custom_params(self, mock_rabbitmq: MagicMock) -> None:
        # Arrange
        mock_instance = MagicMock(spec=RabbitMQDriver)
        mock_rabbitmq.return_value = mock_instance
        config = Config(
            rabbitmq=RabbitMQConfig(
                url="amqp://user:pass@rabbitmq.example.com:5672/vhost",
                exchange_name="my_exchange",
                prefetch_count=5,
            )
        )

        # Act
        result = DriverFactory.create("rabbitmq", config)

        # Assert
        mock_rabbitmq.assert_called_once_with(
            url="amqp://user:pass@rabbitmq.example.com:5672/vhost",
            exchange_name="my_exchange",
            prefetch_count=5,
            keep_completed_tasks=False,
        )
        assert result == mock_instance


@mark.unit
class TestDriverFactoryErrorHandling:
    """Test error handling for unknown driver types."""

    def test_create_with_unknown_driver_type_raises_error(self) -> None:
        # Arrange
        config = Config()

        # Act & Assert
        with raises(ValueError, match="Unknown driver type: unknown"):
            DriverFactory.create("unknown", config)  # type: ignore

    def test_create_from_config_with_unknown_driver_type_raises_error(self) -> None:
        # Arrange
        config = Config()
        config.driver = "unknown"  # type: ignore

        # Act & Assert
        with raises(ValueError, match="Unknown driver type: unknown"):
            DriverFactory.create_from_config(config)

    def test_error_message_includes_supported_types(self) -> None:
        # Arrange
        config = Config()

        # Act & Assert
        with raises(ValueError, match=f"Supported types: {', '.join(list(get_args(DriverType)))}"):
            DriverFactory.create("invalid", config)  # type: ignore


@mark.unit
class TestDriverFactoryParameterPassing:
    """Test that parameters are correctly passed through."""

    @patch("asynctasq.drivers.redis_driver.RedisDriver")
    def test_create_redis_with_partial_params(self, mock_redis: MagicMock) -> None:
        # Arrange
        mock_instance = MagicMock(spec=RedisDriver)
        mock_redis.return_value = mock_instance
        config = Config(
            redis=RedisConfig(
                url="redis://partial:6379",
                db=7,
            )
        )

        # Act - only provide some parameters
        result = DriverFactory.create("redis", config)

        # Assert - defaults should be used for unspecified params
        mock_redis.assert_called_once_with(
            url="redis://partial:6379",
            password=None,  # Default
            db=7,
            max_connections=100,  # Default
            keep_completed_tasks=False,
        )
        assert result == mock_instance

    @patch("asynctasq.drivers.sqs_driver.SQSDriver")
    def test_create_sqs_with_only_credentials(self, mock_sqs: MagicMock) -> None:
        # Arrange
        mock_instance = MagicMock(spec=SQSDriver)
        mock_sqs.return_value = mock_instance
        config = Config(
            sqs=SQSConfig(
                aws_access_key_id="only_key",
                aws_secret_access_key="only_secret",
            )
        )

        # Act
        result = DriverFactory.create("sqs", config)

        # Assert
        mock_sqs.assert_called_once_with(
            region_name="us-east-1",  # Default
            queue_url_prefix=None,  # Default
            aws_access_key_id="only_key",
            aws_secret_access_key="only_secret",
            endpoint_url=None,
        )
        assert result == mock_instance

    @patch("asynctasq.drivers.postgres_driver.PostgresDriver")
    def test_create_postgres_with_minimal_params(self, mock_postgres: MagicMock) -> None:
        # Arrange
        mock_instance = MagicMock(spec=PostgresDriver)
        mock_postgres.return_value = mock_instance
        config = Config(
            postgres=PostgresConfig(
                dsn="postgresql://minimal:pass@localhost/db",
            )
        )

        # Act
        result = DriverFactory.create("postgres", config)

        # Assert
        mock_postgres.assert_called_once_with(
            dsn="postgresql://minimal:pass@localhost/db",
            queue_table="task_queue",  # Default
            dead_letter_table="dead_letter_queue",  # Default
            max_attempts=3,  # Default
            retry_delay_seconds=60,  # Default
            visibility_timeout_seconds=300,  # Default
            min_pool_size=10,  # Default
            max_pool_size=10,  # Default
            keep_completed_tasks=False,
        )
        assert result == mock_instance

    @patch("asynctasq.drivers.mysql_driver.MySQLDriver")
    def test_create_mysql_with_minimal_params(self, mock_mysql: MagicMock) -> None:
        # Arrange
        mock_instance = MagicMock(spec=MySQLDriver)
        mock_mysql.return_value = mock_instance
        config = Config(
            mysql=MySQLConfig(
                dsn="mysql://minimal:pass@localhost:3306/db",
            )
        )

        # Act
        result = DriverFactory.create("mysql", config)

        # Assert
        mock_mysql.assert_called_once_with(
            dsn="mysql://minimal:pass@localhost:3306/db",
            queue_table="task_queue",  # Default
            dead_letter_table="dead_letter_queue",  # Default
            max_attempts=3,  # Default
            retry_delay_seconds=60,  # Default
            visibility_timeout_seconds=300,  # Default
            min_pool_size=10,  # Default
            max_pool_size=10,  # Default
            keep_completed_tasks=False,
        )
        assert result == mock_instance

    @patch("asynctasq.drivers.rabbitmq_driver.RabbitMQDriver")
    def test_create_rabbitmq_with_minimal_params(self, mock_rabbitmq: MagicMock) -> None:
        # Arrange
        mock_instance = MagicMock(spec=RabbitMQDriver)
        mock_rabbitmq.return_value = mock_instance
        config = Config(
            rabbitmq=RabbitMQConfig(
                url="amqp://minimal:pass@localhost:5672/",
            )
        )

        # Act
        result = DriverFactory.create("rabbitmq", config)

        # Assert
        mock_rabbitmq.assert_called_once_with(
            url="amqp://minimal:pass@localhost:5672/",
            exchange_name="asynctasq",  # Default
            prefetch_count=1,  # Default
            keep_completed_tasks=False,
        )
        assert result == mock_instance


@mark.unit
class TestDriverFactoryConfigIntegration:
    """Test integration between Config and DriverFactory."""

    @patch("asynctasq.drivers.redis_driver.RedisDriver")
    def test_config_defaults_are_used(self, mock_redis: MagicMock) -> None:
        # Arrange
        config = Config(
            redis=RedisConfig(),
        )  # Use all defaults
        mock_instance = MagicMock(spec=RedisDriver)
        mock_redis.return_value = mock_instance

        # Act
        result = DriverFactory.create_from_config(config)

        # Assert - default Redis configuration
        mock_redis.assert_called_once()
        assert result == mock_instance

    @patch("asynctasq.drivers.postgres_driver.PostgresDriver")
    def test_all_postgres_config_fields_passed_correctly(self, mock_postgres: MagicMock) -> None:
        # Arrange - create config with all postgres fields customized
        config = Config(
            driver="postgres",
            postgres=PostgresConfig(
                dsn="postgresql://test:test@testhost:5432/testdb",
                queue_table="test_queue",
                dead_letter_table="test_dlq",
                max_attempts=7,
                min_pool_size=15,
                max_pool_size=50,
            ),
            task_defaults=TaskDefaultsConfig(
                retry_strategy="exponential",
                retry_delay=180,
                visibility_timeout=900,
            ),
            repository=RepositoryConfig(
                keep_completed_tasks=False,
            ),
        )
        mock_instance = MagicMock(spec=PostgresDriver)
        mock_postgres.return_value = mock_instance

        # Act
        result = DriverFactory.create_from_config(config)

        # Assert - all fields should be passed through
        mock_postgres.assert_called_once_with(
            dsn="postgresql://test:test@testhost:5432/testdb",
            queue_table="test_queue",
            dead_letter_table="test_dlq",
            max_attempts=7,
            retry_delay_seconds=180,
            visibility_timeout_seconds=900,
            min_pool_size=15,
            max_pool_size=50,
            keep_completed_tasks=False,
        )
        assert result == mock_instance

    @patch("asynctasq.drivers.sqs_driver.SQSDriver")
    def test_all_sqs_config_fields_passed_correctly(self, mock_sqs: MagicMock) -> None:
        # Arrange - create config with all SQS fields customized
        config = Config(
            driver="sqs",
            sqs=SQSConfig(
                region="ap-south-1",
                queue_url_prefix="https://sqs.ap-south-1.amazonaws.com/111222333/",
                aws_access_key_id="test_access_key",
                aws_secret_access_key="test_secret_access_key",
            ),
        )
        mock_instance = MagicMock(spec=SQSDriver)
        mock_sqs.return_value = mock_instance

        # Act
        result = DriverFactory.create_from_config(config)

        # Assert - all fields should be passed through
        mock_sqs.assert_called_once_with(
            region_name="ap-south-1",
            queue_url_prefix="https://sqs.ap-south-1.amazonaws.com/111222333/",
            aws_access_key_id="test_access_key",
            aws_secret_access_key="test_secret_access_key",
            endpoint_url=None,
        )
        assert result == mock_instance

    @patch("asynctasq.drivers.redis_driver.RedisDriver")
    def test_all_redis_config_fields_passed_correctly(self, mock_redis: MagicMock) -> None:
        # Arrange - create config with all Redis fields customized
        config = Config(
            driver="redis",
            redis=RedisConfig(
                url="redis://prod.redis.example.com:6380",
                password="super_secret_password",
                db=15,
                max_connections=100,
            ),
        )
        mock_instance = MagicMock(spec=RedisDriver)
        mock_redis.return_value = mock_instance

        # Act
        result = DriverFactory.create_from_config(config)

        # Assert - all fields should be passed through
        mock_redis.assert_called_once_with(
            url="redis://prod.redis.example.com:6380",
            password="super_secret_password",
            db=15,
            max_connections=100,
            keep_completed_tasks=False,
        )
        assert result == mock_instance

    @patch("asynctasq.drivers.mysql_driver.MySQLDriver")
    def test_all_mysql_config_fields_passed_correctly(self, mock_mysql: MagicMock) -> None:
        # Arrange - create config with all mysql fields customized
        config = Config(
            driver="mysql",
            mysql=MySQLConfig(
                dsn="mysql://test:test@testhost:3306/testdb",
                queue_table="test_queue",
                dead_letter_table="test_dlq",
                max_attempts=7,
                min_pool_size=15,
                max_pool_size=50,
            ),
            task_defaults=TaskDefaultsConfig(
                retry_strategy="exponential",
                retry_delay=180,
                visibility_timeout=900,
            ),
            repository=RepositoryConfig(
                keep_completed_tasks=False,
            ),
        )
        mock_instance = MagicMock(spec=MySQLDriver)
        mock_mysql.return_value = mock_instance

        # Act
        result = DriverFactory.create_from_config(config)

        # Assert - all fields should be passed through
        mock_mysql.assert_called_once_with(
            dsn="mysql://test:test@testhost:3306/testdb",
            queue_table="test_queue",
            dead_letter_table="test_dlq",
            max_attempts=7,
            retry_delay_seconds=180,
            visibility_timeout_seconds=900,
            min_pool_size=15,
            max_pool_size=50,
            keep_completed_tasks=False,
        )
        assert result == mock_instance


@mark.unit
class TestDriverFactoryEdgeCases:
    """Test edge cases and boundary conditions."""

    @patch("asynctasq.drivers.redis_driver.RedisDriver")
    def test_none_values_passed_correctly(self, mock_redis: MagicMock) -> None:
        # Arrange
        mock_instance = MagicMock(spec=RedisDriver)
        mock_redis.return_value = mock_instance
        config = Config(
            redis=RedisConfig(
                password=None,
            )
        )

        # Act - explicitly pass None for optional parameters
        result = DriverFactory.create("redis", config)

        # Assert
        mock_redis.assert_called_once_with(
            url="redis://localhost:6379",
            password=None,
            db=0,
            max_connections=100,
            keep_completed_tasks=False,
        )
        assert result == mock_instance

    @patch("asynctasq.drivers.sqs_driver.SQSDriver")
    def test_empty_string_values_passed_correctly(self, mock_sqs: MagicMock) -> None:
        # Arrange
        mock_instance = MagicMock(spec=SQSDriver)
        mock_sqs.return_value = mock_instance
        config = Config(
            sqs=SQSConfig(
                queue_url_prefix="",  # Empty string (different from None)
            )
        )

        # Act
        result = DriverFactory.create("sqs", config)

        # Assert
        mock_sqs.assert_called_once_with(
            region_name="us-east-1",
            queue_url_prefix="",  # Should be passed as-is
            aws_access_key_id=None,
            aws_secret_access_key=None,
            endpoint_url=None,
        )
        assert result == mock_instance

    @patch("asynctasq.drivers.postgres_driver.PostgresDriver")
    def test_boundary_pool_sizes(self, mock_postgres: MagicMock) -> None:
        # Arrange
        mock_instance = MagicMock(spec=PostgresDriver)
        mock_postgres.return_value = mock_instance
        config = Config(
            postgres=PostgresConfig(
                min_pool_size=1,
                max_pool_size=1000,
            )
        )

        # Act - test with same min and max pool size
        result = DriverFactory.create("postgres", config)

        # Assert
        mock_postgres.assert_called_once()
        call_kwargs = mock_postgres.call_args[1]
        assert call_kwargs["min_pool_size"] == 1
        assert call_kwargs["max_pool_size"] == 1000
        assert result == mock_instance

    @patch("asynctasq.drivers.mysql_driver.MySQLDriver")
    def test_boundary_pool_sizes_mysql(self, mock_mysql: MagicMock) -> None:
        # Arrange
        mock_instance = MagicMock(spec=MySQLDriver)
        mock_mysql.return_value = mock_instance
        config = Config(
            mysql=MySQLConfig(
                min_pool_size=1,
                max_pool_size=1000,
            )
        )

        # Act - test with same min and max pool size
        result = DriverFactory.create("mysql", config)

        # Assert
        mock_mysql.assert_called_once()
        call_kwargs = mock_mysql.call_args[1]
        assert call_kwargs["min_pool_size"] == 1
        assert call_kwargs["max_pool_size"] == 1000
        assert result == mock_instance


@mark.unit
class TestDriverFactoryParameterized:
    """Parameterized tests for DriverFactory to increase coverage of edge cases."""

    @mark.parametrize(
        "driver_type,driver_class_name,config_kwargs,expected_call_kwargs",
        [
            # Redis with boundary values
            (
                "redis",
                "RedisDriver",
                {"redis_db": 0, "redis_max_connections": 1},
                {
                    "url": "redis://localhost:6379",
                    "password": None,
                    "db": 0,
                    "max_connections": 1,
                    "keep_completed_tasks": False,
                },
            ),
            (
                "redis",
                "RedisDriver",
                {"redis_db": 15, "redis_max_connections": 1000},
                {
                    "url": "redis://localhost:6379",
                    "password": None,
                    "db": 15,
                    "max_connections": 1000,
                    "keep_completed_tasks": False,
                },
            ),
            # SQS with minimal config
            (
                "sqs",
                "SQSDriver",
                {"sqs_region": "eu-west-1"},
                {
                    "region_name": "eu-west-1",
                    "queue_url_prefix": None,
                    "aws_access_key_id": None,
                    "aws_secret_access_key": None,
                    "endpoint_url": None,
                },
            ),
            # Postgres with pool size boundaries
            (
                "postgres",
                "PostgresDriver",
                {"postgres_min_pool_size": 1, "postgres_max_pool_size": 1},
                {
                    "dsn": "postgresql://test:test@localhost:5432/test_db",
                    "queue_table": "task_queue",
                    "dead_letter_table": "dead_letter_queue",
                    "max_attempts": 3,
                    "retry_delay_seconds": 60,
                    "visibility_timeout_seconds": 300,
                    "min_pool_size": 1,
                    "max_pool_size": 1,
                    "keep_completed_tasks": False,
                },
            ),
            # MySQL with pool size boundaries
            (
                "mysql",
                "MySQLDriver",
                {"mysql_min_pool_size": 1, "mysql_max_pool_size": 1},
                {
                    "dsn": "mysql://test:test@localhost:3306/test_db",
                    "queue_table": "task_queue",
                    "dead_letter_table": "dead_letter_queue",
                    "max_attempts": 3,
                    "retry_delay_seconds": 60,
                    "visibility_timeout_seconds": 300,
                    "min_pool_size": 1,
                    "max_pool_size": 1,
                    "keep_completed_tasks": False,
                },
            ),
            # RabbitMQ with prefetch boundaries
            (
                "rabbitmq",
                "RabbitMQDriver",
                {"rabbitmq_prefetch_count": 1},
                {
                    "url": "amqp://guest:guest@localhost:5672/",
                    "exchange_name": "asynctasq",
                    "prefetch_count": 1,
                    "keep_completed_tasks": False,
                },
            ),
        ],
    )
    def test_create_with_boundary_values(
        self,
        driver_type: str,
        driver_class_name: str,
        config_kwargs: dict[str, Any],
        expected_call_kwargs: dict[str, Any],
    ) -> None:
        """Test DriverFactory.create() with boundary and edge case values."""
        # Arrange
        config = Config()
        if driver_type == "redis":
            config.redis = RedisConfig(
                **{k.replace("redis_", ""): v for k, v in config_kwargs.items()}
            )
        elif driver_type == "sqs":
            config.sqs = SQSConfig(**{k.replace("sqs_", ""): v for k, v in config_kwargs.items()})
        elif driver_type == "postgres":
            config.postgres = PostgresConfig(
                **{k.replace("postgres_", ""): v for k, v in config_kwargs.items()}
            )
        elif driver_type == "mysql":
            config.mysql = MySQLConfig(
                **{k.replace("mysql_", ""): v for k, v in config_kwargs.items()}
            )
        elif driver_type == "rabbitmq":
            config.rabbitmq = RabbitMQConfig(
                **{k.replace("rabbitmq_", ""): v for k, v in config_kwargs.items()}
            )

        with patch(f"asynctasq.drivers.{driver_type}_driver.{driver_class_name}") as mock_driver:
            mock_instance = MagicMock()
            mock_driver.return_value = mock_instance

            # Act
            result = DriverFactory.create(driver_type, config)  # type: ignore

            # Assert
            mock_driver.assert_called_once_with(**expected_call_kwargs)
            assert result == mock_instance

    @mark.parametrize(
        "driver_type,driver_class_name,missing_kwargs",
        [
            ("redis", "RedisDriver", {}),  # All defaults
            ("sqs", "SQSDriver", {"sqs_region": "us-east-1"}),  # Minimal SQS
            (
                "postgres",
                "PostgresDriver",
                {"postgres_dsn": "postgresql://test"},
            ),  # Minimal Postgres
            ("mysql", "MySQLDriver", {"mysql_dsn": "mysql://test"}),  # Minimal MySQL
            ("rabbitmq", "RabbitMQDriver", {}),  # All defaults
        ],
    )
    def test_create_with_minimal_kwargs(
        self, driver_type: str, driver_class_name: str, missing_kwargs: dict[str, Any]
    ) -> None:
        """Test DriverFactory.create() with minimal required kwargs."""
        # Arrange
        config = Config()
        if driver_type == "redis":
            config.redis = RedisConfig(
                **{k.replace("redis_", ""): v for k, v in missing_kwargs.items()}
            )
        elif driver_type == "sqs":
            config.sqs = SQSConfig(**{k.replace("sqs_", ""): v for k, v in missing_kwargs.items()})
        elif driver_type == "postgres":
            config.postgres = PostgresConfig(
                **{k.replace("postgres_", ""): v for k, v in missing_kwargs.items()}
            )
        elif driver_type == "mysql":
            config.mysql = MySQLConfig(
                **{k.replace("mysql_", ""): v for k, v in missing_kwargs.items()}
            )
        elif driver_type == "rabbitmq":
            config.rabbitmq = RabbitMQConfig(
                **{k.replace("rabbitmq_", ""): v for k, v in missing_kwargs.items()}
            )

        with patch(f"asynctasq.drivers.{driver_type}_driver.{driver_class_name}") as mock_driver:
            mock_instance = MagicMock()
            mock_driver.return_value = mock_instance

            # Act
            result = DriverFactory.create(driver_type, config)  # type: ignore

            # Assert
            mock_driver.assert_called_once()
            assert result == mock_instance


if __name__ == "__main__":
    main([__file__, "-s", "-m", "unit"])
