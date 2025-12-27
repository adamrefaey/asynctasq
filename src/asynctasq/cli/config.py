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
    if hasattr(args, "postgres_max_attempts") and args.postgres_max_attempts is not None:
        postgres_overrides["max_attempts"] = args.postgres_max_attempts
    if hasattr(args, "postgres_min_pool_size") and args.postgres_min_pool_size is not None:
        postgres_overrides["min_pool_size"] = args.postgres_min_pool_size
    if hasattr(args, "postgres_max_pool_size") and args.postgres_max_pool_size is not None:
        postgres_overrides["max_pool_size"] = args.postgres_max_pool_size
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
    if hasattr(args, "mysql_max_attempts") and args.mysql_max_attempts is not None:
        mysql_overrides["max_attempts"] = args.mysql_max_attempts
    if hasattr(args, "mysql_min_pool_size") and args.mysql_min_pool_size is not None:
        mysql_overrides["min_pool_size"] = args.mysql_min_pool_size
    if hasattr(args, "mysql_max_pool_size") and args.mysql_max_pool_size is not None:
        mysql_overrides["max_pool_size"] = args.mysql_max_pool_size
    if mysql_overrides:
        overrides["mysql"] = MySQLConfig(**mysql_overrides)

    # RabbitMQ
    rabbitmq_overrides = {}
    if hasattr(args, "rabbitmq_url") and args.rabbitmq_url is not None:
        rabbitmq_overrides["url"] = args.rabbitmq_url
    if hasattr(args, "rabbitmq_exchange_name") and args.rabbitmq_exchange_name is not None:
        rabbitmq_overrides["exchange_name"] = args.rabbitmq_exchange_name
    if hasattr(args, "rabbitmq_prefetch_count") and args.rabbitmq_prefetch_count is not None:
        rabbitmq_overrides["prefetch_count"] = args.rabbitmq_prefetch_count
    if rabbitmq_overrides:
        overrides["rabbitmq"] = RabbitMQConfig(**rabbitmq_overrides)

    # Events
    events_overrides = {}
    if hasattr(args, "events_redis_url") and args.events_redis_url is not None:
        events_overrides["redis_url"] = args.events_redis_url
    if hasattr(args, "events_channel") and args.events_channel is not None:
        events_overrides["channel"] = args.events_channel
    if (
        hasattr(args, "events_enable_event_emitter_redis")
        and args.events_enable_event_emitter_redis
    ):
        events_overrides["enable_event_emitter_redis"] = args.events_enable_event_emitter_redis
    if events_overrides:
        overrides["events"] = EventsConfig(**events_overrides)

    # Task defaults
    task_defaults_overrides = {}
    if hasattr(args, "task_defaults_queue") and args.task_defaults_queue is not None:
        task_defaults_overrides["queue"] = args.task_defaults_queue
    if hasattr(args, "task_defaults_max_attempts") and args.task_defaults_max_attempts is not None:
        task_defaults_overrides["max_attempts"] = args.task_defaults_max_attempts
    if (
        hasattr(args, "task_defaults_retry_strategy")
        and args.task_defaults_retry_strategy is not None
    ):
        task_defaults_overrides["retry_strategy"] = args.task_defaults_retry_strategy
    if hasattr(args, "task_defaults_retry_delay") and args.task_defaults_retry_delay is not None:
        task_defaults_overrides["retry_delay"] = args.task_defaults_retry_delay
    # Note: timeout and visibility_timeout are now per-task (TaskConfig), not global defaults
    if task_defaults_overrides:
        overrides["task_defaults"] = TaskDefaultsConfig(**task_defaults_overrides)

    # Process pool
    process_pool_overrides = {}
    if hasattr(args, "process_pool_size") and args.process_pool_size is not None:
        process_pool_overrides["size"] = args.process_pool_size
    if (
        hasattr(args, "process_pool_max_tasks_per_child")
        and args.process_pool_max_tasks_per_child is not None
    ):
        process_pool_overrides["max_tasks_per_child"] = args.process_pool_max_tasks_per_child
    if process_pool_overrides:
        overrides["process_pool"] = ProcessPoolConfig(**process_pool_overrides)

    # Repository
    repository_overrides = {}
    if hasattr(args, "repository_keep_completed_tasks") and args.repository_keep_completed_tasks:
        repository_overrides["keep_completed_tasks"] = args.repository_keep_completed_tasks
    if repository_overrides:
        overrides["repository"] = RepositoryConfig(**repository_overrides)

    # Task defaults
    task_defaults_overrides = {}
    if hasattr(args, "task_defaults_queue") and args.task_defaults_queue is not None:
        task_defaults_overrides["queue"] = args.task_defaults_queue
    if hasattr(args, "task_defaults_max_attempts") and args.task_defaults_max_attempts is not None:
        task_defaults_overrides["max_attempts"] = args.task_defaults_max_attempts
    if (
        hasattr(args, "task_defaults_retry_strategy")
        and args.task_defaults_retry_strategy is not None
    ):
        task_defaults_overrides["retry_strategy"] = args.task_defaults_retry_strategy
    if hasattr(args, "task_defaults_retry_delay") and args.task_defaults_retry_delay is not None:
        task_defaults_overrides["retry_delay"] = args.task_defaults_retry_delay
    # Note: timeout and visibility_timeout are now per-task (TaskConfig), not global defaults
    if task_defaults_overrides:
        overrides["task_defaults"] = TaskDefaultsConfig(**task_defaults_overrides)

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
