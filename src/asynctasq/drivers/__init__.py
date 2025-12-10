"""Queue driver implementations for asynctasq.

This module provides the driver abstraction and concrete implementations
for various queue backends (Redis, PostgreSQL, MySQL, AWS SQS).
"""

from typing import Literal

from .base_driver import BaseDriver

DRIVERS = ("redis", "sqs", "postgres", "mysql", "rabbitmq")

type DriverType = Literal["redis", "sqs", "postgres", "mysql", "rabbitmq"]

__all__ = ["BaseDriver", "DRIVERS", "DriverType"]
