from __future__ import annotations

from dataclasses import dataclass
from typing import Any, ClassVar, TypedDict, Unpack

from asynctasq.drivers import DriverType


# TypedDict for config overrides
class ConfigOverrides(TypedDict, total=False):
    driver: DriverType
    redis_url: str
    redis_password: str | None
    redis_db: int
    redis_max_connections: int
    sqs_region: str
    sqs_queue_url_prefix: str | None
    sqs_endpoint_url: str | None
    aws_access_key_id: str | None
    aws_secret_access_key: str | None
    postgres_dsn: str
    postgres_queue_table: str
    postgres_dead_letter_table: str
    postgres_max_attempts: int
    postgres_min_pool_size: int
    postgres_max_pool_size: int
    mysql_dsn: str
    mysql_queue_table: str
    mysql_dead_letter_table: str
    mysql_max_attempts: int
    mysql_min_pool_size: int
    mysql_max_pool_size: int
    rabbitmq_url: str
    rabbitmq_exchange_name: str
    rabbitmq_prefetch_count: int
    events_redis_url: str | None
    events_channel: str
    enable_event_emitter_redis: bool
    default_queue: str
    default_max_attempts: int
    default_retry_strategy: str
    default_retry_delay: int
    default_timeout: int | None
    default_visibility_timeout: int
    process_pool_size: int | None
    process_pool_max_tasks_per_child: int | None
    task_scan_limit: int
    keep_completed_tasks: bool
    sqlalchemy_engine: Any


@dataclass
class Config:
    """Configuration for AsyncTasQ library"""

    # Class-level storage for the global Config singleton. Use classmethods
    # `set` and `get` to access. Declared as ClassVar so dataclasses ignore it.
    _instance: ClassVar[Config] | None = None

    # Driver selection
    driver: DriverType = "redis"

    # Redis configuration
    redis_url: str = "redis://localhost:6379"
    redis_password: str | None = None
    redis_db: int = 0
    redis_max_connections: int = 100

    # SQS configuration
    sqs_region: str = "us-east-1"
    sqs_queue_url_prefix: str | None = None
    sqs_endpoint_url: str | None = None
    aws_access_key_id: str | None = None
    aws_secret_access_key: str | None = None

    # PostgreSQL configuration
    postgres_dsn: str = "postgresql://test:test@localhost:5432/test_db"
    postgres_queue_table: str = "task_queue"
    postgres_dead_letter_table: str = "dead_letter_queue"
    postgres_max_attempts: int = 3
    postgres_min_pool_size: int = 10
    postgres_max_pool_size: int = 10

    # MySQL configuration
    mysql_dsn: str = "mysql://test:test@localhost:3306/test_db"
    mysql_queue_table: str = "task_queue"
    mysql_dead_letter_table: str = "dead_letter_queue"
    mysql_max_attempts: int = 3
    mysql_min_pool_size: int = 10
    mysql_max_pool_size: int = 10

    # RabbitMQ configuration
    rabbitmq_url: str = "amqp://guest:guest@localhost:5672/"
    rabbitmq_exchange_name: str = "asynctasq"
    rabbitmq_prefetch_count: int = 1

    # Events/Monitoring configuration
    # If None, falls back to redis_url for Pub/Sub events
    events_redis_url: str | None = None
    events_channel: str = "asynctasq:events"
    # Controls whether to emit monitoring events (task_enqueued, task_started, etc.) via Redis Pub/Sub
    enable_event_emitter_redis: bool = False

    # Task defaults
    default_queue: str = "default"
    default_max_attempts: int = 3
    default_retry_strategy: str = "exponential"
    default_retry_delay: int = 60
    default_timeout: int | None = None
    default_visibility_timeout: int = 300

    # ProcessTask/ProcessPoolExecutor configuration
    # If None, ProcessTask will auto-initialize using os.process_cpu_count() or 4
    process_pool_size: int | None = None
    # If None, worker processes live until pool shutdown (no recycling)
    # Recommended: 100-1000 to prevent memory leaks (Python 3.11+)
    process_pool_max_tasks_per_child: int | None = None

    # Task repository configuration
    task_scan_limit: int = 10000

    # Task retention configuration
    # If False (default), completed tasks are deleted/removed after acknowledgment
    # If True, completed tasks are kept for history/audit purposes
    # Note: Not applicable for SQS driver (SQS always deletes acknowledged messages)
    keep_completed_tasks: bool = False

    # SQLAlchemy engine for ORM cleanup
    sqlalchemy_engine: Any = None

    def __post_init__(self):
        """Validate configuration after initialization."""
        if self.default_max_attempts < 0:
            raise ValueError("default_max_attempts must be non-negative")
        if self.default_retry_delay < 0:
            raise ValueError("default_retry_delay must be non-negative")
        if self.default_retry_strategy not in ("fixed", "exponential"):
            raise ValueError("default_retry_strategy must be 'fixed' or 'exponential'")
        if self.default_visibility_timeout < 1:
            raise ValueError("default_visibility_timeout must be positive")
        if self.redis_db < 0 or self.redis_db > 15:
            raise ValueError("redis_db must be between 0 and 15")
        if self.redis_max_connections < 1:
            raise ValueError("redis_max_connections must be positive")
        if self.postgres_max_attempts < 1:
            raise ValueError("postgres_max_attempts must be positive")
        if self.postgres_min_pool_size < 1:
            raise ValueError("postgres_min_pool_size must be positive")
        if self.postgres_max_pool_size < 1:
            raise ValueError("postgres_max_pool_size must be positive")
        if self.postgres_min_pool_size > self.postgres_max_pool_size:
            raise ValueError("postgres_min_pool_size cannot be greater than postgres_max_pool_size")
        if self.mysql_max_attempts < 1:
            raise ValueError("mysql_max_attempts must be positive")
        if self.mysql_min_pool_size < 1:
            raise ValueError("mysql_min_pool_size must be positive")
        if self.mysql_max_pool_size < 1:
            raise ValueError("mysql_max_pool_size must be positive")
        if self.mysql_min_pool_size > self.mysql_max_pool_size:
            raise ValueError("mysql_min_pool_size cannot be greater than mysql_max_pool_size")
        if self.task_scan_limit < 1:
            raise ValueError("task_scan_limit must be positive")

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
