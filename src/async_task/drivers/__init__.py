"""Queue driver implementations for async-task.

This module provides the driver abstraction and concrete implementations
for various queue backends (Redis, PostgreSQL, MySQL, AWS SQS).
"""

from typing import Literal, TypeAlias

from .base_driver import BaseDriver

DRIVERS = ("redis", "sqs", "postgres", "mysql", "rabbitmq")

DriverType: TypeAlias = Literal["redis", "sqs", "postgres", "mysql", "rabbitmq"]

__all__ = ["BaseDriver", "DRIVERS"]
