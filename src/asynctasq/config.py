from __future__ import annotations

from typing import Any, ClassVar, Literal

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

from asynctasq.drivers import DriverType

# Type alias for serializer selection
type SerializerType = Literal["msgspec", "msgpack"]


class RedisConfig(BaseSettings):
    """Redis driver configuration.

    Context: Both dispatch and worker contexts.
    Used for queue connections in both task dispatching and processing.

    Environment variables:
        ASYNCTASQ_REDIS_URL: Redis connection URL (default: redis://localhost:6379)
        ASYNCTASQ_REDIS_PASSWORD: Redis password (default: None)
        ASYNCTASQ_REDIS_DB: Redis database number (default: 0)
        ASYNCTASQ_REDIS_MAX_CONNECTIONS: Maximum connections in pool (default: 100)
    """

    model_config = SettingsConfigDict(
        env_prefix="ASYNCTASQ_REDIS_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    url: str = "redis://localhost:6379"
    password: str | None = None
    db: int = 0
    max_connections: int = 100

    @field_validator("db")
    @classmethod
    def validate_db(cls, v: int) -> int:
        """Validate Redis database number."""
        if v < 0 or v > 15:
            raise ValueError("db must be between 0 and 15")
        return v

    @field_validator("max_connections")
    @classmethod
    def validate_max_connections(cls, v: int) -> int:
        """Validate max connections."""
        if v < 1:
            raise ValueError("max_connections must be positive")
        return v


class SQSConfig(BaseSettings):
    """AWS SQS driver configuration.

    Context: Both dispatch and worker contexts.
    Used for queue connections in both task dispatching and processing.

    Environment variables:
        ASYNCTASQ_SQS_REGION: AWS region (default: us-east-1)
        ASYNCTASQ_SQS_QUEUE_URL_PREFIX: Queue URL prefix (default: None)
        ASYNCTASQ_SQS_ENDPOINT_URL: Custom endpoint URL (default: None)
        ASYNCTASQ_SQS_AWS_ACCESS_KEY_ID: AWS access key ID (default: None)
        ASYNCTASQ_SQS_AWS_SECRET_ACCESS_KEY: AWS secret access key (default: None)
    """

    model_config = SettingsConfigDict(
        env_prefix="ASYNCTASQ_SQS_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    region: str = "us-east-1"
    queue_url_prefix: str | None = None
    endpoint_url: str | None = None
    aws_access_key_id: str | None = None
    aws_secret_access_key: str | None = None


class PostgresConfig(BaseSettings):
    """PostgreSQL driver configuration.

    Context: Both dispatch and worker contexts.
    Used for queue connections in both task dispatching and processing.

    Environment variables:
        ASYNCTASQ_POSTGRES_DSN: PostgreSQL connection DSN
        ASYNCTASQ_POSTGRES_QUEUE_TABLE: Queue table name (default: task_queue)
        ASYNCTASQ_POSTGRES_DEAD_LETTER_TABLE: Dead letter table name (default: dead_letter_queue)
        ASYNCTASQ_POSTGRES_MIN_POOL_SIZE: Minimum pool size (default: 10)
        ASYNCTASQ_POSTGRES_MAX_POOL_SIZE: Maximum pool size (default: 10)
    """

    model_config = SettingsConfigDict(
        env_prefix="ASYNCTASQ_POSTGRES_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    dsn: str = "postgresql://test:test@localhost:5432/test_db"
    queue_table: str = "task_queue"
    dead_letter_table: str = "dead_letter_queue"
    min_pool_size: int = 10
    max_pool_size: int = 10

    @field_validator("min_pool_size")
    @classmethod
    def validate_min_pool_size(cls, v: int) -> int:
        """Validate min pool size."""
        if v < 1:
            raise ValueError("min_pool_size must be positive")
        return v

    @field_validator("max_pool_size")
    @classmethod
    def validate_max_pool_size(cls, v: int) -> int:
        """Validate max pool size."""
        if v < 1:
            raise ValueError("max_pool_size must be positive")
        return v

    def model_post_init(self, __context: Any) -> None:
        """Additional validation after field validation."""
        if self.min_pool_size > self.max_pool_size:
            raise ValueError("min_pool_size cannot be greater than max_pool_size")


class MySQLConfig(BaseSettings):
    """MySQL driver configuration.

    Context: Both dispatch and worker contexts.
    Used for queue connections in both task dispatching and processing.

    Environment variables:
        ASYNCTASQ_MYSQL_DSN: MySQL connection DSN
        ASYNCTASQ_MYSQL_QUEUE_TABLE: Queue table name (default: task_queue)
        ASYNCTASQ_MYSQL_DEAD_LETTER_TABLE: Dead letter table name (default: dead_letter_queue)
        ASYNCTASQ_MYSQL_MIN_POOL_SIZE: Minimum pool size (default: 10)
        ASYNCTASQ_MYSQL_MAX_POOL_SIZE: Maximum pool size (default: 10)
    """

    model_config = SettingsConfigDict(
        env_prefix="ASYNCTASQ_MYSQL_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    dsn: str = "mysql://test:test@localhost:3306/test_db"
    queue_table: str = "task_queue"
    dead_letter_table: str = "dead_letter_queue"
    min_pool_size: int = 10
    max_pool_size: int = 10

    @field_validator("min_pool_size")
    @classmethod
    def validate_min_pool_size(cls, v: int) -> int:
        """Validate min pool size."""
        if v < 1:
            raise ValueError("min_pool_size must be positive")
        return v

    @field_validator("max_pool_size")
    @classmethod
    def validate_max_pool_size(cls, v: int) -> int:
        """Validate max pool size."""
        if v < 1:
            raise ValueError("max_pool_size must be positive")
        return v

    def model_post_init(self, __context: Any) -> None:
        """Additional validation after field validation."""
        if self.min_pool_size > self.max_pool_size:
            raise ValueError("min_pool_size cannot be greater than max_pool_size")


class RabbitMQConfig(BaseSettings):
    """RabbitMQ driver configuration.

    Context: Both dispatch and worker contexts.
    Used for queue connections in both task dispatching and processing.

    Environment variables:
        ASYNCTASQ_RABBITMQ_URL: RabbitMQ connection URL (default: amqp://guest:guest@localhost:5672/)
        ASYNCTASQ_RABBITMQ_EXCHANGE_NAME: Exchange name (default: asynctasq)
        ASYNCTASQ_RABBITMQ_PREFETCH_COUNT: Prefetch count (default: 1)
    """

    model_config = SettingsConfigDict(
        env_prefix="ASYNCTASQ_RABBITMQ_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    url: str = "amqp://guest:guest@localhost:5672/"
    exchange_name: str = "asynctasq"
    prefetch_count: int = 1


class EventsConfig(BaseSettings):
    """Events and monitoring configuration.

    Context: Both dispatch and worker contexts.
    Event emission happens in both task dispatching and processing contexts.

    Environment variables:
        ASYNCTASQ_EVENTS_REDIS_URL: Redis URL for event emitter (default: None)
        ASYNCTASQ_EVENTS_CHANNEL: Event channel name (default: asynctasq:events)
        ASYNCTASQ_EVENTS_ENABLE_EVENT_EMITTER_REDIS: Enable Redis event emitter (default: False)
    """

    model_config = SettingsConfigDict(
        env_prefix="ASYNCTASQ_EVENTS_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    redis_url: str | None = None
    channel: str = "asynctasq:events"
    enable_event_emitter_redis: bool = False


class TaskDefaultsConfig(BaseSettings):
    """Default task configuration.

    Context specificity:
    - queue: Both dispatch and worker contexts (used when dispatching, stored in task)
    - max_attempts: Both contexts (used when dispatching, stored in task; used by worker when retrying)
    - retry_strategy: Both contexts (used when dispatching, stored in task; used by worker when retrying)
    - retry_delay: Both contexts (used when dispatching, stored in task; used by worker when retrying)

    Environment variables:
        ASYNCTASQ_TASK_DEFAULTS_QUEUE: Default queue name (default: default)
        ASYNCTASQ_TASK_DEFAULTS_MAX_ATTEMPTS: Default max attempts (default: 3)
        ASYNCTASQ_TASK_DEFAULTS_RETRY_STRATEGY: Default retry strategy [fixed, exponential] (default: exponential)
        ASYNCTASQ_TASK_DEFAULTS_RETRY_DELAY: Default retry delay in seconds (default: 60)
    """

    model_config = SettingsConfigDict(
        env_prefix="ASYNCTASQ_TASK_DEFAULTS_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    queue: str = "default"
    max_attempts: int = 3
    retry_strategy: str = "exponential"
    retry_delay: int = 60

    @field_validator("max_attempts")
    @classmethod
    def validate_max_attempts(cls, v: int) -> int:
        """Validate max attempts."""
        if v < 0:
            raise ValueError("max_attempts must be non-negative")
        return v

    @field_validator("retry_delay")
    @classmethod
    def validate_retry_delay(cls, v: int) -> int:
        """Validate retry delay."""
        if v < 0:
            raise ValueError("retry_delay must be non-negative")
        return v

    @field_validator("retry_strategy")
    @classmethod
    def validate_retry_strategy(cls, v: str) -> str:
        """Validate retry strategy."""
        if v not in ("fixed", "exponential"):
            raise ValueError("retry_strategy must be 'fixed' or 'exponential'")
        return v


class ProcessPoolConfig(BaseSettings):
    """Process pool configuration for CPU-bound tasks.

    Context: Worker context only.
    Only used by workers when executing AsyncProcessTask or SyncProcessTask tasks.

    Environment variables:
        ASYNCTASQ_PROCESS_POOL_SIZE: Process pool size (default: None = CPU count)
        ASYNCTASQ_PROCESS_POOL_MAX_TASKS_PER_CHILD: Max tasks per child process (default: None = unlimited)
    """

    model_config = SettingsConfigDict(
        env_prefix="ASYNCTASQ_PROCESS_POOL_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    size: int | None = None
    max_tasks_per_child: int | None = None


class RepositoryConfig(BaseSettings):
    """Task repository configuration.

    Context: Worker context only.
    Only used by workers when completing tasks to determine if they should be kept or removed.

    Environment variables:
        ASYNCTASQ_REPOSITORY_KEEP_COMPLETED_TASKS: Keep completed tasks (default: False)
    """

    model_config = SettingsConfigDict(
        env_prefix="ASYNCTASQ_REPOSITORY_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    keep_completed_tasks: bool = False


class Config(BaseSettings):
    """Configuration for AsyncTasQ library.

    All configuration can be set via:
    1. Environment variables (with ASYNCTASQ_ prefix)
    2. .env file
    3. Constructor arguments (highest priority)

    Environment variables:
        ASYNCTASQ_DRIVER: Driver type [redis, sqs, postgres, mysql, rabbitmq] (default: redis)
        ASYNCTASQ_SERIALIZER: Serializer type [msgspec, msgpack] (default: msgspec)

    Nested configurations use their own prefixes:
    - ASYNCTASQ_REDIS_*: RedisConfig settings
    - ASYNCTASQ_SQS_*: SQSConfig settings
    - ASYNCTASQ_POSTGRES_*: PostgresConfig settings
    - ASYNCTASQ_MYSQL_*: MySQLConfig settings
    - ASYNCTASQ_RABBITMQ_*: RabbitMQConfig settings
    - ASYNCTASQ_EVENTS_*: EventsConfig settings
    - ASYNCTASQ_TASK_DEFAULTS_*: TaskDefaultsConfig settings
    - ASYNCTASQ_PROCESS_POOL_*: ProcessPoolConfig settings
    - ASYNCTASQ_REPOSITORY_*: RepositoryConfig settings
    """

    model_config = SettingsConfigDict(
        env_prefix="ASYNCTASQ_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Class-level storage for the global Config singleton. Use classmethods
    # `set` and `get` to access. Declared as ClassVar so pydantic ignores it.
    _instance: ClassVar[Config | None] = None

    # Driver selection
    driver: DriverType = "redis"

    # Serializer selection (msgspec is default for better performance)
    serializer: SerializerType = "msgspec"

    # Driver-specific configurations
    redis: RedisConfig = Field(default_factory=RedisConfig)
    sqs: SQSConfig = Field(default_factory=SQSConfig)
    postgres: PostgresConfig = Field(default_factory=PostgresConfig)
    mysql: MySQLConfig = Field(default_factory=MySQLConfig)
    rabbitmq: RabbitMQConfig = Field(default_factory=RabbitMQConfig)

    # Feature configurations
    events: EventsConfig = Field(default_factory=EventsConfig)
    task_defaults: TaskDefaultsConfig = Field(default_factory=TaskDefaultsConfig)
    process_pool: ProcessPoolConfig = Field(default_factory=ProcessPoolConfig)
    repository: RepositoryConfig = Field(default_factory=RepositoryConfig)

    # SQLAlchemy engine for ORM cleanup
    sqlalchemy_engine: Any = None

    # Tortoise ORM configuration for automatic initialization
    tortoise_orm: dict[str, Any] | None = None

    @field_validator("serializer")
    @classmethod
    def validate_serializer(cls, v: str) -> str:
        """Validate serializer type and check availability."""
        if v not in ("msgspec", "msgpack"):
            raise ValueError("serializer must be 'msgspec' or 'msgpack'")
        return v

    def create_serializer(self) -> Any:
        """Create serializer instance based on configuration.

        Returns:
            Configured serializer instance (MsgspecSerializer or MsgpackSerializer)
        """
        if self.serializer == "msgspec":
            from asynctasq.serializers.msgspec_serializer import MsgspecSerializer

            return MsgspecSerializer()
        else:
            from asynctasq.serializers.msgpack_serializer import MsgpackSerializer

            return MsgpackSerializer()

    @classmethod
    def set(cls, **overrides: Any) -> None:
        """Set the global configuration with overrides.

        Args:
            **overrides: Configuration overrides. User-passed values take
                precedence over environment variables.

        This centralizes global state on the `Config` class and keeps the
        instance-level validation performed by pydantic.
        """
        cls._instance = cls(**overrides)

    @classmethod
    def get(cls) -> Config:
        """Return the global `Config` singleton, initializing with defaults
        and environment variables if it hasn't been set yet."""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance
