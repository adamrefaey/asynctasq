from __future__ import annotations

from dataclasses import dataclass
from typing import Any, ClassVar, TypedDict, Unpack

from asynctasq.drivers import DriverType


# TypedDict for config overrides
class ConfigOverrides(TypedDict, total=False):
    driver: DriverType
    redis: RedisConfig
    sqs: SQSConfig
    postgres: PostgresConfig
    mysql: MySQLConfig
    rabbitmq: RabbitMQConfig
    events: EventsConfig
    task_defaults: TaskDefaultsConfig
    process_pool: ProcessPoolConfig
    repository: RepositoryConfig
    sqlalchemy_engine: Any


@dataclass
class RedisConfig:
    """Redis driver configuration.

    Context: Both dispatch and worker contexts.
    Used for queue connections in both task dispatching and processing.
    """

    url: str = "redis://localhost:6379"
    password: str | None = None
    db: int = 0
    max_connections: int = 100

    def __post_init__(self):
        """Validate Redis configuration."""
        if self.db < 0 or self.db > 15:
            raise ValueError("db must be between 0 and 15")
        if self.max_connections < 1:
            raise ValueError("max_connections must be positive")


@dataclass
class SQSConfig:
    """AWS SQS driver configuration.

    Context: Both dispatch and worker contexts.
    Used for queue connections in both task dispatching and processing.
    """

    region: str = "us-east-1"
    queue_url_prefix: str | None = None
    endpoint_url: str | None = None
    aws_access_key_id: str | None = None
    aws_secret_access_key: str | None = None


@dataclass
class PostgresConfig:
    """PostgreSQL driver configuration.

    Context: Both dispatch and worker contexts.
    Used for queue connections in both task dispatching and processing.
    """

    dsn: str = "postgresql://test:test@localhost:5432/test_db"
    queue_table: str = "task_queue"
    dead_letter_table: str = "dead_letter_queue"
    max_attempts: int = 3
    min_pool_size: int = 10
    max_pool_size: int = 10

    def __post_init__(self):
        """Validate PostgreSQL configuration."""
        if self.max_attempts < 1:
            raise ValueError("max_attempts must be positive")
        if self.min_pool_size < 1:
            raise ValueError("min_pool_size must be positive")
        if self.max_pool_size < 1:
            raise ValueError("max_pool_size must be positive")
        if self.min_pool_size > self.max_pool_size:
            raise ValueError("min_pool_size cannot be greater than max_pool_size")


@dataclass
class MySQLConfig:
    """MySQL driver configuration.

    Context: Both dispatch and worker contexts.
    Used for queue connections in both task dispatching and processing.
    """

    dsn: str = "mysql://test:test@localhost:3306/test_db"
    queue_table: str = "task_queue"
    dead_letter_table: str = "dead_letter_queue"
    max_attempts: int = 3
    min_pool_size: int = 10
    max_pool_size: int = 10

    def __post_init__(self):
        """Validate MySQL configuration."""
        if self.max_attempts < 1:
            raise ValueError("max_attempts must be positive")
        if self.min_pool_size < 1:
            raise ValueError("min_pool_size must be positive")
        if self.max_pool_size < 1:
            raise ValueError("max_pool_size must be positive")
        if self.min_pool_size > self.max_pool_size:
            raise ValueError("min_pool_size cannot be greater than max_pool_size")


@dataclass
class RabbitMQConfig:
    """RabbitMQ driver configuration.

    Context: Both dispatch and worker contexts.
    Used for queue connections in both task dispatching and processing.
    """

    url: str = "amqp://guest:guest@localhost:5672/"
    exchange_name: str = "asynctasq"
    prefetch_count: int = 1


@dataclass
class EventsConfig:
    """Events and monitoring configuration.

    Context: Both dispatch and worker contexts.
    Event emission happens in both task dispatching and processing contexts.
    """

    redis_url: str | None = None
    channel: str = "asynctasq:events"
    enable_event_emitter_redis: bool = False


@dataclass
class TaskDefaultsConfig:
    """Default task configuration.

    Context specificity:
    - queue: Both dispatch and worker contexts (used when dispatching, stored in task)
    - max_attempts: Both contexts (used when dispatching, stored in task; used by worker when retrying)
    - retry_strategy: Both contexts (used when dispatching, stored in task; used by worker when retrying)
    - retry_delay: Both contexts (used when dispatching, stored in task; used by worker when retrying)

    Note:
    - timeout and visibility_timeout are now configured per-task via TaskConfig
    """

    queue: str = "default"
    max_attempts: int = 3
    retry_strategy: str = "exponential"
    retry_delay: int = 60

    def __post_init__(self):
        """Validate task defaults configuration."""
        if self.max_attempts < 0:
            raise ValueError("max_attempts must be non-negative")
        if self.retry_delay < 0:
            raise ValueError("retry_delay must be non-negative")
        if self.retry_strategy not in ("fixed", "exponential"):
            raise ValueError("retry_strategy must be 'fixed' or 'exponential'")


@dataclass
class ProcessPoolConfig:
    """Process pool configuration for CPU-bound tasks.

    Context: Worker context only.
    Only used by workers when executing AsyncProcessTask or SyncProcessTask tasks.
    """

    size: int | None = None
    max_tasks_per_child: int | None = None


@dataclass
class RepositoryConfig:
    """Task repository configuration.

    Context: Worker context only.
    Only used by workers when completing tasks to determine if they should be kept or removed.
    """

    keep_completed_tasks: bool = False


@dataclass
class Config:
    """Configuration for AsyncTasQ library"""

    # Class-level storage for the global Config singleton. Use classmethods
    # `set` and `get` to access. Declared as ClassVar so dataclasses ignore it.
    _instance: ClassVar[Config] | None = None

    # Driver selection
    driver: DriverType = "redis"

    # Driver-specific configurations
    redis: RedisConfig = None
    sqs: SQSConfig = None
    postgres: PostgresConfig = None
    mysql: MySQLConfig = None
    rabbitmq: RabbitMQConfig = None

    # Feature configurations
    events: EventsConfig = None
    task_defaults: TaskDefaultsConfig = None
    process_pool: ProcessPoolConfig = None
    repository: RepositoryConfig = None

    # SQLAlchemy engine for ORM cleanup
    sqlalchemy_engine: Any = None

    def __post_init__(self):
        """Initialize nested config objects with defaults if not provided."""
        if self.redis is None:
            self.redis = RedisConfig()
        if self.sqs is None:
            self.sqs = SQSConfig()
        if self.postgres is None:
            self.postgres = PostgresConfig()
        if self.mysql is None:
            self.mysql = MySQLConfig()
        if self.rabbitmq is None:
            self.rabbitmq = RabbitMQConfig()
        if self.events is None:
            self.events = EventsConfig()
        if self.task_defaults is None:
            self.task_defaults = TaskDefaultsConfig()
        if self.process_pool is None:
            self.process_pool = ProcessPoolConfig()
        if self.repository is None:
            self.repository = RepositoryConfig()

    @classmethod
    def set(cls, **overrides: Unpack[ConfigOverrides]) -> None:
        """Set the global configuration using the same overrides accepted by
        `Config`'s constructor.

        This centralizes global state on the `Config` class and keeps the
        instance-level validation performed by `__post_init__`.
        """
        cls._instance = cls(**overrides)

    @classmethod
    def get(cls) -> Config:
        """Return the global `Config` singleton, initializing with defaults
        if it hasn't been set yet."""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance
