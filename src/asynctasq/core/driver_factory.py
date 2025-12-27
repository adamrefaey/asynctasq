from typing import TYPE_CHECKING, Literal, get_args, overload

from asynctasq.config import (
    Config,
)
from asynctasq.drivers import DriverType
from asynctasq.drivers.base_driver import BaseDriver

if TYPE_CHECKING:
    from asynctasq.drivers.mysql_driver import MySQLDriver
    from asynctasq.drivers.postgres_driver import PostgresDriver
    from asynctasq.drivers.rabbitmq_driver import RabbitMQDriver
    from asynctasq.drivers.redis_driver import RedisDriver
    from asynctasq.drivers.sqs_driver import SQSDriver


class DriverFactory:
    """Factory for creating queue drivers from configuration.

    Provides a unified interface for instantiating queue drivers without
    coupling code to specific driver implementations. Supports switching
    drivers by changing configuration only.
    """

    @overload
    @staticmethod
    def create(driver_type: Literal["redis"], config: Config) -> "RedisDriver": ...

    @overload
    @staticmethod
    def create(driver_type: Literal["sqs"], config: Config) -> "SQSDriver": ...

    @overload
    @staticmethod
    def create(driver_type: Literal["postgres"], config: Config) -> "PostgresDriver": ...

    @overload
    @staticmethod
    def create(driver_type: Literal["mysql"], config: Config) -> "MySQLDriver": ...

    @overload
    @staticmethod
    def create(driver_type: Literal["rabbitmq"], config: Config) -> "RabbitMQDriver": ...

    @overload
    @staticmethod
    def create(driver_type: str, config: Config) -> BaseDriver: ...

    @staticmethod
    def create(driver_type: str, config: Config) -> BaseDriver:
        """Create driver from configuration object.

        Args:
            driver_type: Type of driver to create ("redis", "sqs", "postgres", "mysql", "rabbitmq")
            config: Config instance

        Returns:
            Configured BaseDriver instance

        Raises:
            ValueError: If driver type is unknown
        """
        match driver_type:
            case "redis":
                try:
                    from asynctasq.drivers.redis_driver import RedisDriver
                except ImportError as e:
                    raise ImportError(
                        "Redis driver requires the 'redis' optional dependency. "
                        "Install it with: pip install asynctasq[redis] or uv add asynctasq[redis]"
                    ) from e

                return RedisDriver(
                    url=config.redis.url,
                    password=config.redis.password,
                    db=config.redis.db,
                    max_connections=config.redis.max_connections,
                    keep_completed_tasks=config.repository.keep_completed_tasks,
                )
            case "sqs":
                try:
                    from asynctasq.drivers.sqs_driver import SQSDriver
                except ImportError as e:
                    raise ImportError(
                        "SQS driver requires the 'sqs' optional dependency. "
                        "Install it with: pip install asynctasq[sqs] or uv add asynctasq[sqs]"
                    ) from e

                return SQSDriver(
                    region_name=config.sqs.region,
                    queue_url_prefix=config.sqs.queue_url_prefix,
                    aws_access_key_id=config.sqs.aws_access_key_id,
                    aws_secret_access_key=config.sqs.aws_secret_access_key,
                    endpoint_url=config.sqs.endpoint_url,
                )
            case "postgres":
                try:
                    from asynctasq.drivers.postgres_driver import PostgresDriver
                except ImportError as e:
                    raise ImportError(
                        "PostgreSQL driver requires the 'postgres' optional dependency. "
                        "Install it with: pip install asynctasq[postgres] or uv add asynctasq[postgres]"
                    ) from e

                return PostgresDriver(
                    dsn=config.postgres.dsn,
                    queue_table=config.postgres.queue_table,
                    dead_letter_table=config.postgres.dead_letter_table,
                    max_attempts=config.postgres.max_attempts,
                    retry_delay_seconds=config.task_defaults.retry_delay,
                    visibility_timeout_seconds=config.task_defaults.visibility_timeout,
                    min_pool_size=config.postgres.min_pool_size,
                    max_pool_size=config.postgres.max_pool_size,
                    keep_completed_tasks=config.repository.keep_completed_tasks,
                )
            case "mysql":
                try:
                    from asynctasq.drivers.mysql_driver import MySQLDriver
                except ImportError as e:
                    raise ImportError(
                        "MySQL driver requires the 'mysql' optional dependency. "
                        "Install it with: pip install asynctasq[mysql] or uv add asynctasq[mysql]"
                    ) from e

                return MySQLDriver(
                    dsn=config.mysql.dsn,
                    queue_table=config.mysql.queue_table,
                    dead_letter_table=config.mysql.dead_letter_table,
                    max_attempts=config.mysql.max_attempts,
                    retry_delay_seconds=config.task_defaults.retry_delay,
                    visibility_timeout_seconds=config.task_defaults.visibility_timeout,
                    min_pool_size=config.mysql.min_pool_size,
                    max_pool_size=config.mysql.max_pool_size,
                    keep_completed_tasks=config.repository.keep_completed_tasks,
                )
            case "rabbitmq":
                try:
                    from asynctasq.drivers.rabbitmq_driver import RabbitMQDriver
                except ImportError as e:
                    raise ImportError(
                        "RabbitMQ driver requires the 'rabbitmq' optional dependency. "
                        "Install it with: pip install asynctasq[rabbitmq] or uv add asynctasq[rabbitmq]"
                    ) from e

                return RabbitMQDriver(
                    url=config.rabbitmq.url,
                    exchange_name=config.rabbitmq.exchange_name,
                    prefetch_count=config.rabbitmq.prefetch_count,
                    keep_completed_tasks=config.repository.keep_completed_tasks,
                )
            case _:
                raise ValueError(
                    f"Unknown driver type: {driver_type}. "
                    f"Supported types: {', '.join(list(get_args(DriverType)))}"
                )
