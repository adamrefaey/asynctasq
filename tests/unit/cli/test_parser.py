"""Unit tests for CLI argument parser.

Testing Strategy:
- pytest 9.0.1 with asyncio_mode="auto" (no decorators needed)
- AAA pattern (Arrange, Act, Assert)
- Test argument parsing and validation
- Fast, isolated tests
"""

import argparse

from pytest import main, mark, raises

from async_task.cli.parser import add_driver_args, create_parser


@mark.unit
class TestAddDriverArgs:
    """Test add_driver_args() function."""

    def test_add_driver_args_adds_driver_argument(self) -> None:
        # Arrange
        parser = argparse.ArgumentParser()

        # Act
        add_driver_args(parser)

        # Assert
        args = parser.parse_args(["--driver", "redis"])
        assert args.driver == "redis"

    def test_add_driver_args_adds_redis_options(self) -> None:
        # Arrange
        parser = argparse.ArgumentParser()
        add_driver_args(parser)

        # Act
        args = parser.parse_args(
            [
                "--driver",
                "redis",
                "--redis-url",
                "redis://test:6379",
                "--redis-password",
                "secret",
                "--redis-db",
                "5",
                "--redis-max-connections",
                "20",
            ]
        )

        # Assert
        assert args.driver == "redis"
        assert args.redis_url == "redis://test:6379"
        assert args.redis_password == "secret"
        assert args.redis_db == 5
        assert args.redis_max_connections == 20

    def test_add_driver_args_adds_sqs_options(self) -> None:
        # Arrange
        parser = argparse.ArgumentParser()
        add_driver_args(parser)

        # Act
        args = parser.parse_args(
            [
                "--driver",
                "sqs",
                "--sqs-region",
                "us-west-2",
                "--sqs-queue-url-prefix",
                "https://sqs.us-west-2/",
                "--aws-access-key-id",
                "key123",
                "--aws-secret-access-key",
                "secret123",
            ]
        )

        # Assert
        assert args.driver == "sqs"
        assert args.sqs_region == "us-west-2"
        assert args.sqs_queue_url_prefix == "https://sqs.us-west-2/"
        assert args.aws_access_key_id == "key123"
        assert args.aws_secret_access_key == "secret123"

    def test_add_driver_args_adds_postgres_options(self) -> None:
        # Arrange
        parser = argparse.ArgumentParser()
        add_driver_args(parser)

        # Act
        args = parser.parse_args(
            [
                "--driver",
                "postgres",
                "--postgres-dsn",
                "postgresql://user:pass@localhost/db",
                "--postgres-queue-table",
                "custom_queue",
                "--postgres-dead-letter-table",
                "custom_dlq",
            ]
        )

        # Assert
        assert args.driver == "postgres"
        assert args.postgres_dsn == "postgresql://user:pass@localhost/db"
        assert args.postgres_queue_table == "custom_queue"
        assert args.postgres_dead_letter_table == "custom_dlq"

    def test_add_driver_args_driver_choices_validation(self) -> None:
        # Arrange
        parser = argparse.ArgumentParser()
        add_driver_args(parser)

        # Act & Assert
        for driver in ["redis", "sqs", "memory", "postgres"]:
            args = parser.parse_args(["--driver", driver])
            assert args.driver == driver

        # Invalid driver should raise error
        with raises(SystemExit):
            parser.parse_args(["--driver", "invalid"])


@mark.unit
class TestCreateParser:
    """Test create_parser() function."""

    def test_create_parser_returns_argument_parser(self) -> None:
        # Act
        parser = create_parser()

        # Assert
        assert isinstance(parser, argparse.ArgumentParser)

    def test_create_parser_requires_command(self) -> None:
        # Arrange
        parser = create_parser()

        # Act & Assert
        with raises(SystemExit):
            parser.parse_args([])

    def test_create_parser_has_worker_command(self) -> None:
        # Arrange
        parser = create_parser()

        # Act
        args = parser.parse_args(["worker", "--driver", "redis"])

        # Assert
        assert args.command == "worker"
        assert args.driver == "redis"

    def test_create_parser_has_migrate_command(self) -> None:
        # Arrange
        parser = create_parser()

        # Act
        args = parser.parse_args(["migrate", "--driver", "postgres"])

        # Assert
        assert args.command == "migrate"
        assert args.driver == "postgres"

    def test_create_parser_worker_has_queues_argument(self) -> None:
        # Arrange
        parser = create_parser()

        # Act
        args = parser.parse_args(["worker", "--driver", "redis", "--queues", "high,low"])

        # Assert
        assert args.command == "worker"
        assert args.queues == "high,low"

    def test_create_parser_worker_has_concurrency_argument(self) -> None:
        # Arrange
        parser = create_parser()

        # Act
        args = parser.parse_args(["worker", "--driver", "redis", "--concurrency", "20"])

        # Assert
        assert args.command == "worker"
        assert args.concurrency == 20

    def test_create_parser_worker_concurrency_default(self) -> None:
        # Arrange
        parser = create_parser()

        # Act
        args = parser.parse_args(["worker", "--driver", "redis"])

        # Assert
        assert args.concurrency == 10

    def test_create_parser_worker_with_all_options(self) -> None:
        # Arrange
        parser = create_parser()

        # Act
        args = parser.parse_args(
            [
                "worker",
                "--driver",
                "redis",
                "--redis-url",
                "redis://test:6379",
                "--queues",
                "high,low",
                "--concurrency",
                "15",
            ]
        )

        # Assert
        assert args.command == "worker"
        assert args.driver == "redis"
        assert args.redis_url == "redis://test:6379"
        assert args.queues == "high,low"
        assert args.concurrency == 15

    def test_create_parser_migrate_with_postgres_options(self) -> None:
        # Arrange
        parser = create_parser()

        # Act
        args = parser.parse_args(
            [
                "migrate",
                "--driver",
                "postgres",
                "--postgres-dsn",
                "postgresql://user:pass@localhost/db",
                "--postgres-queue-table",
                "custom_queue",
            ]
        )

        # Assert
        assert args.command == "migrate"
        assert args.driver == "postgres"
        assert args.postgres_dsn == "postgresql://user:pass@localhost/db"
        assert args.postgres_queue_table == "custom_queue"

    def test_create_parser_invalid_command_raises_error(self) -> None:
        # Arrange
        parser = create_parser()

        # Act & Assert
        with raises(SystemExit):
            parser.parse_args(["invalid_command"])

    def test_create_parser_help_shows_commands(self) -> None:
        # Arrange
        parser = create_parser()

        # Act
        help_text = parser.format_help()

        # Assert
        assert "worker" in help_text
        assert "migrate" in help_text
        assert "Available commands" in help_text

    def test_create_parser_worker_help_shows_options(self) -> None:
        # Arrange
        parser = create_parser()

        # Act
        # Find the subparsers action by iterating through parser actions
        subparsers_action = None
        for action in parser._actions:
            if isinstance(action, argparse._SubParsersAction):
                subparsers_action = action
                break

        assert subparsers_action is not None
        assert isinstance(subparsers_action.choices, dict)
        worker_parser = subparsers_action.choices["worker"]
        help_text = worker_parser.format_help()

        # Assert
        assert "--driver" in help_text
        assert "--queues" in help_text
        assert "--concurrency" in help_text
        assert "Redis options" in help_text
        assert "SQS options" in help_text
        assert "PostgreSQL options" in help_text


if __name__ == "__main__":
    main([__file__, "-s", "-m", "unit"])
