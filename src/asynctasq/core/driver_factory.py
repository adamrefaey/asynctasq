from typing import get_args

from asynctasq.config import (
    Config,
)
from asynctasq.drivers import DriverType
from asynctasq.drivers.base_driver import BaseDriver


class DriverFactory:
    """Factory for creating queue drivers from configuration.

    Provides a unified interface for instantiating queue drivers without
    coupling code to specific driver implementations. Supports switching
    drivers by changing configuration only.
    """

    @staticmethod
    def create_from_config(config: Config, driver_type: DriverType | None = None) -> BaseDriver:
        """Create driver from configuration object.

        Args:
            config: Config instance
            driver_type: Optional driver type to override config.driver
                        Useful for testing or runtime driver switching

        Returns:
            Configured BaseDriver instance

        Raises:
            ValueError: If driver type is unknown
        """
        return DriverFactory.create(
            driver_type if driver_type is not None else config.driver,
            config,
        )

    @staticmethod
    def create(driver_type: DriverType, config: Config) -> BaseDriver:
        """Create driver by type with configuration.

        Args:
            driver_type: Type of driver
            config: Configuration object containing all settings

        Returns:
            Configured BaseDriver instance

        Raises:
            ValueError: If driver type is unknown

        """
        match driver_type:
            case "redis":
                from asynctasq.drivers.redis_driver import RedisDriver

                return RedisDriver(
                    url=config.redis.url,
                    password=config.redis.password,
                    db=config.redis.db,
                    max_connections=config.redis.max_connections,
                    keep_completed_tasks=config.repository.keep_completed_tasks,
                )
            case "sqs":
                from asynctasq.drivers.sqs_driver import SQSDriver

                return SQSDriver(
                    region_name=config.sqs.region,
                    queue_url_prefix=config.sqs.queue_url_prefix,
                    aws_access_key_id=config.sqs.aws_access_key_id,
                    aws_secret_access_key=config.sqs.aws_secret_access_key,
                    endpoint_url=config.sqs.endpoint_url,
                )
            case "postgres":
                from asynctasq.drivers.postgres_driver import PostgresDriver

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
                from asynctasq.drivers.mysql_driver import MySQLDriver

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
                from asynctasq.drivers.rabbitmq_driver import RabbitMQDriver

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
