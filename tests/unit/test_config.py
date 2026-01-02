"""Unit tests for asynctasq.config module."""

from pydantic_core import ValidationError
import pytest

from asynctasq.config import (
    Config,
    EventsConfig,
    MySQLConfig,
    PostgresConfig,
    ProcessPoolConfig,
    RabbitMQConfig,
    RedisConfig,
    RepositoryConfig,
    SQSConfig,
    TaskDefaultsConfig,
)


class TestConfigValidation:
    """Test Config validation in __post_init__."""

    def test_valid_config(self):
        """Test that valid config passes validation."""
        config = Config()
        # Should not raise any exception
        assert config.task_defaults.max_attempts == 3

    @pytest.mark.parametrize("invalid_value", [-1, -5])
    def test_default_max_attempts_validation(self, invalid_value):
        """Test default_max_attempts validation."""
        with pytest.raises(
            (ValueError, ValidationError), match="max_attempts must be non-negative"
        ):
            TaskDefaultsConfig(max_attempts=invalid_value)

    @pytest.mark.parametrize("invalid_value", [-1, -5])
    def test_default_retry_delay_validation(self, invalid_value):
        """Test default_retry_delay validation."""
        with pytest.raises((ValueError, ValidationError), match="retry_delay must be non-negative"):
            TaskDefaultsConfig(retry_delay=invalid_value)

    @pytest.mark.parametrize("invalid_value", ["linear", "random", ""])
    def test_default_retry_strategy_validation(self, invalid_value):
        """Test default_retry_strategy validation."""
        with pytest.raises(
            (ValueError, ValidationError), match="retry_strategy must be 'fixed' or 'exponential'"
        ):
            TaskDefaultsConfig(retry_strategy=invalid_value)

    @pytest.mark.parametrize("invalid_value", [-1, 16, 100])
    def test_redis_db_validation(self, invalid_value):
        """Test redis_db validation."""
        with pytest.raises((ValueError, ValidationError), match="db must be between 0 and 15"):
            RedisConfig(db=invalid_value)

    @pytest.mark.parametrize("invalid_value", [0, -1])
    def test_redis_max_connections_validation(self, invalid_value):
        """Test redis_max_connections validation."""
        with pytest.raises((ValueError, ValidationError), match="max_connections must be positive"):
            RedisConfig(max_connections=invalid_value)

    @pytest.mark.parametrize("invalid_value", [0, -1])
    def test_postgres_max_attempts_validation(self, invalid_value):
        """Test postgres_max_attempts validation."""
        with pytest.raises((ValueError, ValidationError), match="max_attempts must be positive"):
            PostgresConfig(max_attempts=invalid_value)

    @pytest.mark.parametrize("invalid_value", [0, -1])
    def test_postgres_min_pool_size_validation(self, invalid_value):
        """Test postgres_min_pool_size validation."""
        with pytest.raises((ValueError, ValidationError), match="min_pool_size must be positive"):
            PostgresConfig(min_pool_size=invalid_value)

    @pytest.mark.parametrize("invalid_value", [0, -1])
    def test_postgres_max_pool_size_validation(self, invalid_value):
        """Test postgres_max_pool_size validation."""
        with pytest.raises((ValueError, ValidationError), match="max_pool_size must be positive"):
            PostgresConfig(max_pool_size=invalid_value)

    def test_postgres_pool_size_ordering_validation(self):
        """Test postgres pool size ordering validation."""
        with pytest.raises(
            (ValueError, ValidationError),
            match="min_pool_size cannot be greater than max_pool_size",
        ):
            PostgresConfig(min_pool_size=10, max_pool_size=5)

    @pytest.mark.parametrize("invalid_value", [0, -1])
    def test_mysql_max_attempts_validation(self, invalid_value):
        """Test mysql_max_attempts validation."""
        with pytest.raises((ValueError, ValidationError), match="max_attempts must be positive"):
            MySQLConfig(max_attempts=invalid_value)

    @pytest.mark.parametrize("invalid_value", [0, -1])
    def test_mysql_min_pool_size_validation(self, invalid_value):
        """Test mysql_min_pool_size validation."""
        with pytest.raises((ValueError, ValidationError), match="min_pool_size must be positive"):
            MySQLConfig(min_pool_size=invalid_value)

    @pytest.mark.parametrize("invalid_value", [0, -1])
    def test_mysql_max_pool_size_validation(self, invalid_value):
        """Test mysql_max_pool_size validation."""
        with pytest.raises((ValueError, ValidationError), match="max_pool_size must be positive"):
            MySQLConfig(max_pool_size=invalid_value)

    def test_mysql_pool_size_ordering_validation(self):
        """Test mysql pool size ordering validation."""
        with pytest.raises(
            (ValueError, ValidationError),
            match="min_pool_size cannot be greater than max_pool_size",
        ):
            MySQLConfig(min_pool_size=10, max_pool_size=5)


class TestConfigSingleton:
    """Test Config singleton behavior."""

    def test_get_returns_default_instance(self):
        """Test get() returns default instance when not set."""
        # Reset instance
        Config._instance = None

        config = Config.get()
        assert isinstance(config, Config)
        assert Config._instance is config

    def test_get_returns_same_instance(self):
        """Test get() returns the same instance."""
        # Reset instance
        Config._instance = None

        config1 = Config.get()
        config2 = Config.get()

        assert config1 is config2

    def test_set_creates_new_instance(self):
        """Test set() creates new instance with overrides."""
        # Reset instance
        Config._instance = None

        Config.set(driver="redis", redis=RedisConfig(url="redis://test:6379"))

        config = Config.get()
        assert config.driver == "redis"
        assert config.redis.url == "redis://test:6379"

    def test_set_overrides_existing(self):
        """Test set() overrides existing configuration."""
        # Set initial config
        Config.set(driver="postgres")

        # Override
        Config.set(driver="redis", redis=RedisConfig(url="redis://test:6379"))

        config = Config.get()
        assert config.driver == "redis"
        assert config.redis.url == "redis://test:6379"


class TestConfigGroupDefaults:
    """Test that config groups are initialized with defaults."""

    def test_config_initializes_all_groups(self):
        """Test that all config groups are initialized with defaults."""
        config = Config()

        assert isinstance(config.redis, RedisConfig)
        assert isinstance(config.sqs, SQSConfig)
        assert isinstance(config.postgres, PostgresConfig)
        assert isinstance(config.mysql, MySQLConfig)
        assert isinstance(config.rabbitmq, RabbitMQConfig)
        assert isinstance(config.events, EventsConfig)
        assert isinstance(config.task_defaults, TaskDefaultsConfig)
        assert isinstance(config.process_pool, ProcessPoolConfig)
        assert isinstance(config.repository, RepositoryConfig)

    def test_config_groups_have_correct_defaults(self):
        """Test that config groups have the correct default values."""
        config = Config()

        # RedisConfig defaults
        assert config.redis.url == "redis://localhost:6379"
        assert config.redis.password is None
        assert config.redis.db == 0
        assert config.redis.max_connections == 100

        # TaskDefaultsConfig defaults
        assert config.task_defaults.queue == "default"
        assert config.task_defaults.max_attempts == 3
        assert config.task_defaults.retry_strategy == "exponential"
        assert config.task_defaults.retry_delay == 60

        # RepositoryConfig defaults
        assert config.repository.keep_completed_tasks is False
