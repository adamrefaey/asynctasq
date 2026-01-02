"""Argument parser for CLI commands."""

import argparse

from asynctasq.drivers import DRIVERS

from .utils import DEFAULT_CONCURRENCY, DEFAULT_QUEUE


def add_driver_args(parser: argparse.ArgumentParser, default_driver: str | None = None) -> None:
    """Add common driver configuration arguments to a parser.

    Args:
        parser: Argument parser to add driver arguments to
        default_driver: Optional default driver value to use if not specified
    """
    # Driver selection
    parser.add_argument(
        "--driver",
        type=str,
        choices=list(DRIVERS),
        default=default_driver,
        help="Queue driver to use (default: 'redis')",
    )

    # Redis options
    redis_group = parser.add_argument_group("Redis options")
    redis_group.add_argument(
        "--redis-url",
        type=str,
        help="Redis connection URL (default: 'redis://localhost:6379')",
    )
    redis_group.add_argument(
        "--redis-password",
        type=str,
        help="Redis password (default: None)",
    )
    redis_group.add_argument(
        "--redis-db",
        type=int,
        help="Redis database number (default: 0)",
    )
    redis_group.add_argument(
        "--redis-max-connections",
        type=int,
        help="Redis max connections (default: 100)",
    )

    # SQS options
    sqs_group = parser.add_argument_group("SQS options")
    sqs_group.add_argument(
        "--sqs-region",
        type=str,
        help="AWS SQS region (default: 'us-east-1')",
    )
    sqs_group.add_argument(
        "--sqs-queue-url-prefix",
        type=str,
        help="SQS queue URL prefix (default: None)",
    )
    sqs_group.add_argument(
        "--sqs-endpoint-url",
        type=str,
        help="SQS endpoint URL (default: None)",
    )
    sqs_group.add_argument(
        "--aws-access-key-id",
        type=str,
        help="AWS access key ID (default: from AWS_ACCESS_KEY_ID env var)",
    )
    sqs_group.add_argument(
        "--aws-secret-access-key",
        type=str,
        help="AWS secret access key (default: from AWS_SECRET_ACCESS_KEY env var)",
    )

    # PostgreSQL options
    postgres_group = parser.add_argument_group("PostgreSQL options")
    postgres_group.add_argument(
        "--postgres-dsn",
        type=str,
        help="PostgreSQL connection DSN (default: 'postgresql://test:test@localhost:5432/test_db')",
    )
    postgres_group.add_argument(
        "--postgres-queue-table",
        type=str,
        help="PostgreSQL queue table name (default: 'task_queue')",
    )
    postgres_group.add_argument(
        "--postgres-dead-letter-table",
        type=str,
        help="PostgreSQL dead letter table name (default: 'dead_letter_queue')",
    )
    postgres_group.add_argument(
        "--postgres-max-attempts",
        type=int,
        help="PostgreSQL maximum attempts before dead-lettering (default: 3)",
    )
    postgres_group.add_argument(
        "--postgres-min-pool-size",
        type=int,
        help="PostgreSQL minimum connection pool size (default: 10)",
    )
    postgres_group.add_argument(
        "--postgres-max-pool-size",
        type=int,
        help="PostgreSQL maximum connection pool size (default: 10)",
    )

    # MySQL options
    mysql_group = parser.add_argument_group("MySQL options")
    mysql_group.add_argument(
        "--mysql-dsn",
        type=str,
        help="MySQL connection DSN (default: 'mysql://test:test@localhost:3306/test_db')",
    )
    mysql_group.add_argument(
        "--mysql-queue-table",
        type=str,
        help="MySQL queue table name (default: 'task_queue')",
    )
    mysql_group.add_argument(
        "--mysql-dead-letter-table",
        type=str,
        help="MySQL dead letter table name (default: 'dead_letter_queue')",
    )
    mysql_group.add_argument(
        "--mysql-max-attempts",
        type=int,
        help="MySQL maximum attempts before dead-lettering (default: 3)",
    )
    mysql_group.add_argument(
        "--mysql-min-pool-size",
        type=int,
        help="MySQL minimum connection pool size (default: 10)",
    )
    mysql_group.add_argument(
        "--mysql-max-pool-size",
        type=int,
        help="MySQL maximum connection pool size (default: 10)",
    )

    # RabbitMQ options
    rabbitmq_group = parser.add_argument_group("RabbitMQ options")
    rabbitmq_group.add_argument(
        "--rabbitmq-url",
        type=str,
        help="RabbitMQ connection URL (default: 'amqp://guest:guest@localhost:5672/')",
    )
    rabbitmq_group.add_argument(
        "--rabbitmq-exchange-name",
        type=str,
        help="RabbitMQ exchange name (default: 'asynctasq')",
    )
    rabbitmq_group.add_argument(
        "--rabbitmq-prefetch-count",
        type=int,
        help="RabbitMQ consumer prefetch count (default: 1)",
    )

    # Events options
    events_group = parser.add_argument_group("Events options")
    events_group.add_argument(
        "--events-redis-url",
        type=str,
        help="Redis URL for event pub/sub (default: None, uses main redis.url)",
    )
    events_group.add_argument(
        "--events-channel",
        type=str,
        help="Redis Pub/Sub channel name for events (default: 'asynctasq:events')",
    )
    events_group.add_argument(
        "--events-enable-event-emitter-redis",
        action="store_true",
        help="Enable Redis Pub/Sub event emitter (default: False)",
    )

    # Task defaults options (worker context only)
    task_defaults_group = parser.add_argument_group("Task defaults options (worker context only)")
    task_defaults_group.add_argument(
        "--task-defaults-queue",
        type=str,
        help="Default queue name for tasks (default: 'default')",
    )
    task_defaults_group.add_argument(
        "--task-defaults-max-attempts",
        type=int,
        help="Default maximum retry attempts (default: 3)",
    )
    task_defaults_group.add_argument(
        "--task-defaults-retry-strategy",
        type=str,
        choices=["fixed", "exponential"],
        help="Retry delay strategy (default: 'exponential')",
    )
    task_defaults_group.add_argument(
        "--task-defaults-retry-delay",
        type=int,
        help="Base retry delay in seconds (default: 60)",
    )
    task_defaults_group.add_argument(
        "--task-defaults-timeout",
        type=int,
        help="Default task timeout in seconds (default: None)",
    )
    task_defaults_group.add_argument(
        "--task-defaults-visibility-timeout",
        type=int,
        help="Visibility timeout for crash recovery in seconds (worker context only, default: 300)",
    )

    # Process pool options (worker context only)
    process_pool_group = parser.add_argument_group("Process pool options (worker context only)")
    process_pool_group.add_argument(
        "--process-pool-size",
        type=int,
        help="Number of worker processes for CPU-bound tasks (default: None, auto-detect CPU count)",
    )
    process_pool_group.add_argument(
        "--process-pool-max-tasks-per-child",
        type=int,
        help="Recycle worker processes after N tasks (default: None)",
    )

    # Repository options (worker context only)
    repository_group = parser.add_argument_group("Repository options (worker context only)")
    repository_group.add_argument(
        "--repository-keep-completed-tasks",
        action="store_true",
        help="Keep completed tasks for history/audit (default: False)",
    )


def create_parser() -> argparse.ArgumentParser:
    """Create and configure the argument parser.

    Returns:
        Configured argument parser with all subcommands
    """
    parser = argparse.ArgumentParser(
        description="AsyncTasQ - Task queue system for Python",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    subparsers = parser.add_subparsers(
        dest="command",
        help="Available commands",
        required=True,
    )

    # Worker subcommand
    worker_parser = subparsers.add_parser(
        "worker",
        description="Start a worker to process tasks from queues",
        help="Start a worker to process tasks",
    )
    add_driver_args(worker_parser)
    worker_parser.add_argument(
        "--queues",
        type=str,
        help=f"Comma-separated list of queue names to process (default: '{DEFAULT_QUEUE}')",
    )
    worker_parser.add_argument(
        "--concurrency",
        type=int,
        help=f"Maximum number of concurrent tasks (default: {DEFAULT_CONCURRENCY})",
        default=DEFAULT_CONCURRENCY,
    )

    # Migrate subcommand
    migrate_parser = subparsers.add_parser(
        "migrate",
        description="Initialize database schema for PostgreSQL or MySQL driver",
        help="Initialize database schema",
    )
    add_driver_args(migrate_parser, default_driver="postgres")
    migrate_parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be created without making changes (default: False)",
    )
    migrate_parser.add_argument(
        "--force",
        action="store_true",
        help="Force migration even if tables already exist (default: False)",
    )

    return parser
