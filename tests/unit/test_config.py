"""Unit tests for asynctasq.config module."""

import pytest

from asynctasq.config import Config


class TestConfigValidation:
    """Test Config validation in __post_init__."""

    def test_valid_config(self):
        """Test that valid config passes validation."""
        config = Config()
        # Should not raise any exception
        assert config.default_max_attempts == 3

    @pytest.mark.parametrize("invalid_value", [-1, -5])
    def test_default_max_attempts_validation(self, invalid_value):
        """Test default_max_attempts validation."""
        with pytest.raises(ValueError, match="default_max_attempts must be non-negative"):
            Config(default_max_attempts=invalid_value)

    @pytest.mark.parametrize("invalid_value", [-1, -0.5])
    def test_default_retry_delay_validation(self, invalid_value):
        """Test default_retry_delay validation."""
        with pytest.raises(ValueError, match="default_retry_delay must be non-negative"):
            Config(default_retry_delay=invalid_value)

    @pytest.mark.parametrize("invalid_value", ["linear", "random", ""])
    def test_default_retry_strategy_validation(self, invalid_value):
        """Test default_retry_strategy validation."""
        with pytest.raises(
            ValueError, match="default_retry_strategy must be 'fixed' or 'exponential'"
        ):
            Config(default_retry_strategy=invalid_value)

    @pytest.mark.parametrize("invalid_value", [0, -1])
    def test_default_visibility_timeout_validation(self, invalid_value):
        """Test default_visibility_timeout validation."""
        with pytest.raises(ValueError, match="default_visibility_timeout must be positive"):
            Config(default_visibility_timeout=invalid_value)

    @pytest.mark.parametrize("invalid_value", [-1, 16, 100])
    def test_redis_db_validation(self, invalid_value):
        """Test redis_db validation."""
        with pytest.raises(ValueError, match="redis_db must be between 0 and 15"):
            Config(redis_db=invalid_value)

    @pytest.mark.parametrize("invalid_value", [0, -1])
    def test_redis_max_connections_validation(self, invalid_value):
        """Test redis_max_connections validation."""
        with pytest.raises(ValueError, match="redis_max_connections must be positive"):
            Config(redis_max_connections=invalid_value)

    @pytest.mark.parametrize("invalid_value", [0, -1])
    def test_postgres_max_attempts_validation(self, invalid_value):
        """Test postgres_max_attempts validation."""
        with pytest.raises(ValueError, match="postgres_max_attempts must be positive"):
            Config(postgres_max_attempts=invalid_value)

    @pytest.mark.parametrize("invalid_value", [0, -1])
    def test_postgres_min_pool_size_validation(self, invalid_value):
        """Test postgres_min_pool_size validation."""
        with pytest.raises(ValueError, match="postgres_min_pool_size must be positive"):
            Config(postgres_min_pool_size=invalid_value)

    @pytest.mark.parametrize("invalid_value", [0, -1])
    def test_postgres_max_pool_size_validation(self, invalid_value):
        """Test postgres_max_pool_size validation."""
        with pytest.raises(ValueError, match="postgres_max_pool_size must be positive"):
            Config(postgres_max_pool_size=invalid_value)

    def test_postgres_pool_size_ordering_validation(self):
        """Test postgres pool size ordering validation."""
        with pytest.raises(
            ValueError, match="postgres_min_pool_size cannot be greater than postgres_max_pool_size"
        ):
            Config(postgres_min_pool_size=10, postgres_max_pool_size=5)

    @pytest.mark.parametrize("invalid_value", [0, -1])
    def test_mysql_max_attempts_validation(self, invalid_value):
        """Test mysql_max_attempts validation."""
        with pytest.raises(ValueError, match="mysql_max_attempts must be positive"):
            Config(mysql_max_attempts=invalid_value)

    @pytest.mark.parametrize("invalid_value", [0, -1])
    def test_mysql_min_pool_size_validation(self, invalid_value):
        """Test mysql_min_pool_size validation."""
        with pytest.raises(ValueError, match="mysql_min_pool_size must be positive"):
            Config(mysql_min_pool_size=invalid_value)

    @pytest.mark.parametrize("invalid_value", [0, -1])
    def test_mysql_max_pool_size_validation(self, invalid_value):
        """Test mysql_max_pool_size validation."""
        with pytest.raises(ValueError, match="mysql_max_pool_size must be positive"):
            Config(mysql_max_pool_size=invalid_value)

    def test_mysql_pool_size_ordering_validation(self):
        """Test mysql pool size ordering validation."""
        with pytest.raises(
            ValueError, match="mysql_min_pool_size cannot be greater than mysql_max_pool_size"
        ):
            Config(mysql_min_pool_size=10, mysql_max_pool_size=5)

    @pytest.mark.parametrize("invalid_value", [0, -1])
    def test_task_scan_limit_validation(self, invalid_value):
        """Test task_scan_limit validation."""
        with pytest.raises(ValueError, match="task_scan_limit must be positive"):
            Config(task_scan_limit=invalid_value)


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

        Config.set(driver="redis", redis_url="redis://test:6379")

        config = Config.get()
        assert config.driver == "redis"
        assert config.redis_url == "redis://test:6379"

    def test_set_overrides_existing(self):
        """Test set() overrides existing configuration."""
        # Set initial config
        Config.set(driver="postgres")

        # Override
        Config.set(driver="redis", redis_url="redis://test:6379")

        config = Config.get()
        assert config.driver == "redis"
        assert config.redis_url == "redis://test:6379"
