"""Configuration utilities for CLI."""

import argparse
from typing import Any

from asynctasq.config import Config


def build_config_overrides(args: argparse.Namespace) -> dict[str, Any]:
    """Extract configuration overrides from parsed arguments.

    Groups CLI arguments into nested config objects.

    Args:
        args: Parsed command-line arguments

    Returns:
        Dictionary of config overrides to pass to Config()
    """
    from asynctasq.config import (
        MySQLConfig,
        PostgresConfig,
        RabbitMQConfig,
        RedisConfig,
        SQSConfig,
    )

    overrides = {}

    # Driver
    if hasattr(args, "driver") and args.driver is not None:
        overrides["driver"] = args.driver

    # Redis
    redis_overrides = {}
    if hasattr(args, "redis_url") and args.redis_url is not None:
        redis_overrides["url"] = args.redis_url
    if hasattr(args, "redis_password") and args.redis_password is not None:
        redis_overrides["password"] = args.redis_password
    if hasattr(args, "redis_db") and args.redis_db is not None:
        redis_overrides["db"] = args.redis_db
    if hasattr(args, "redis_max_connections") and args.redis_max_connections is not None:
        redis_overrides["max_connections"] = args.redis_max_connections
    if redis_overrides:
        overrides["redis"] = RedisConfig(**redis_overrides)

    # SQS
    sqs_overrides = {}
    if hasattr(args, "sqs_region") and args.sqs_region is not None:
        sqs_overrides["region"] = args.sqs_region
    if hasattr(args, "sqs_queue_url_prefix") and args.sqs_queue_url_prefix is not None:
        sqs_overrides["queue_url_prefix"] = args.sqs_queue_url_prefix
    if hasattr(args, "sqs_endpoint_url") and args.sqs_endpoint_url is not None:
        sqs_overrides["endpoint_url"] = args.sqs_endpoint_url
    if hasattr(args, "aws_access_key_id") and args.aws_access_key_id is not None:
        sqs_overrides["aws_access_key_id"] = args.aws_access_key_id
    if hasattr(args, "aws_secret_access_key") and args.aws_secret_access_key is not None:
        sqs_overrides["aws_secret_access_key"] = args.aws_secret_access_key
    if sqs_overrides:
        overrides["sqs"] = SQSConfig(**sqs_overrides)

    # PostgreSQL
    postgres_overrides = {}
    if hasattr(args, "postgres_dsn") and args.postgres_dsn is not None:
        postgres_overrides["dsn"] = args.postgres_dsn
    if hasattr(args, "postgres_queue_table") and args.postgres_queue_table is not None:
        postgres_overrides["queue_table"] = args.postgres_queue_table
    if hasattr(args, "postgres_dead_letter_table") and args.postgres_dead_letter_table is not None:
        postgres_overrides["dead_letter_table"] = args.postgres_dead_letter_table
    if postgres_overrides:
        overrides["postgres"] = PostgresConfig(**postgres_overrides)

    # MySQL
    mysql_overrides = {}
    if hasattr(args, "mysql_dsn") and args.mysql_dsn is not None:
        mysql_overrides["dsn"] = args.mysql_dsn
    if hasattr(args, "mysql_queue_table") and args.mysql_queue_table is not None:
        mysql_overrides["queue_table"] = args.mysql_queue_table
    if hasattr(args, "mysql_dead_letter_table") and args.mysql_dead_letter_table is not None:
        mysql_overrides["dead_letter_table"] = args.mysql_dead_letter_table
    if mysql_overrides:
        overrides["mysql"] = MySQLConfig(**mysql_overrides)

    # RabbitMQ
    rabbitmq_overrides = {}
    if hasattr(args, "rabbitmq_url") and args.rabbitmq_url is not None:
        rabbitmq_overrides["url"] = args.rabbitmq_url
    if rabbitmq_overrides:
        overrides["rabbitmq"] = RabbitMQConfig(**rabbitmq_overrides)

    return overrides


def build_config(args: argparse.Namespace) -> Config:
    """Build Config object from parsed arguments.

    Args:
        args: Parsed command-line arguments

    Returns:
        Configured Config instance
    """
    overrides = build_config_overrides(args)
    return Config(**overrides)
