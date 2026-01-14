# AsyncTasQ

[![Tests](https://raw.githubusercontent.com/adamrefaey/asynctasq/main/.github/tests.svg)](https://github.com/adamrefaey/asynctasq/actions/workflows/ci.yml)
[![Coverage](https://raw.githubusercontent.com/adamrefaey/asynctasq/main/.github/coverage.svg)](https://raw.githubusercontent.com/adamrefaey/asynctasq/main/.github/coverage.svg)
[![Python Version](https://raw.githubusercontent.com/adamrefaey/asynctasq/main/.github/python-version.svg)](https://www.python.org/downloads/)
[![PyPI Version](https://img.shields.io/pypi/v/asynctasq)](https://pypi.org/project/asynctasq/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

A modern, async-first, type-safe task queue for Python. Built with asyncio, featuring 5 queue backends (Redis, PostgreSQL, MySQL, RabbitMQ, AWS SQS), automatic ORM serialization, and enterprise-grade reliability.

## Table of Contents

- [AsyncTasQ](#asynctasq)
  - [Table of Contents](#table-of-contents)
  - [Quick Start](#quick-start)
  - [Documentation](#documentation)
  - [Why AsyncTasQ?](#why-asynctasq)
  - [Key Features](#key-features)
  - [Comparison with Alternatives](#comparison-with-alternatives)
  - [Contributing](#contributing)
  - [Roadmap](#roadmap)
  - [License \& Support](#license--support)

## Quick Start

```bash
# Install with your preferred driver
uv add "asynctasq[redis]"

# Configure environment
asynctasq publish  # Generate .env.example template
cp .env.example .env  # Edit with your settings
```

**Define and dispatch tasks:**

```python
from asynctasq import init, run, task

init()  # Loads from .env

@task
async def send_email(to: str, subject: str):
    print(f"Sending to {to}: {subject}")
    return f"Email sent to {to}"

# Dispatch tasks
async def main():
    task_id = await send_email(to="user@example.com", subject="Welcome!").dispatch()
    print(f"Task dispatched: {task_id}")

if __name__ == "__main__":
    run(main())
```

**Run workers:**

```bash
uv run asynctasq worker --queues default
```

See the [full Quick Start guide](docs/examples/function-based-tasks.md) for complete examples with Redis setup, class-based tasks, and configuration chaining.

## Documentation

- **[Installation](docs/installation.md)** – Installation instructions
- **[Configuration](docs/configuration.md)** – Complete configuration guide
- **[Environment Variables](docs/environment-variables.md)** – .env file support and configuration
- **[Task Definitions](docs/task-definitions.md)** – Function-based and class-based tasks
- **[Queue Drivers](docs/queue-drivers.md)** – Redis, PostgreSQL, MySQL, RabbitMQ, AWS SQS
- **[Running Workers](docs/running-workers.md)** – CLI and programmatic workers
- **[Monitoring](docs/monitoring.md)** – Event streaming and queue statistics
- **[ORM Integrations](docs/orm-integrations.md)** – SQLAlchemy, Django, Tortoise
- **[Framework Integrations](docs/framework-integrations.md)** – FastAPI integration
- **[CLI Reference](docs/cli-reference.md)** – Command reference
- **[Best Practices](docs/best-practices.md)** – Production guidelines

**Examples:**
- [Function-Based Tasks](docs/examples/function-based-tasks.md)
- [Class-Based Tasks](docs/examples/class-based-tasks.md)

## Why AsyncTasQ?

**True async-first architecture** – Built with asyncio from the ground up, not retrofitted onto sync foundations like Celery/RQ. Four execution modes (async I/O, sync I/O, async CPU, sync CPU) for optimal performance.

**Intelligent serialization** – Automatic ORM model handling (SQLAlchemy, Django, Tortoise) with msgpack encoding reduces payloads by 90%+. Pass models directly as task arguments.

**Enterprise reliability** – ACID guarantees (PostgreSQL/MySQL), dead-letter queues, crash recovery via visibility timeouts, graceful shutdown, and real-time event streaming.

**Zero vendor lock-in** – 5 production backends (Redis, PostgreSQL, MySQL, RabbitMQ, AWS SQS) with identical API. Switch drivers with one config line.

**Developer experience** – Type-safe and IDE support, elegant Laravel-inspired API, method chaining, beautiful Rich-formatted output, and first-class FastAPI integration.

## Key Features

- ✅ **Async-first** with native asyncio throughout
- ✅ **5 queue backends**: Redis, PostgreSQL, MySQL, RabbitMQ, AWS SQS
- ✅ **Type-safe** with full type hints and IDE support
- ✅ **4 execution modes**: async I/O, sync I/O (threads), CPU-bound (processes)
- ✅ **ORM integration**: Auto-serialization for SQLAlchemy, Django, Tortoise
- ✅ **msgpack serialization**: 2-3x faster than JSON
- ✅ **ACID guarantees** (PostgreSQL/MySQL)
- ✅ **Dead-letter queues** for failed task inspection
- ✅ **Environment & .env file support**
- ✅ **FastAPI integration** with lifecycle management
- ✅ **Real-time event streaming** via Redis Pub/Sub
- ✅ **Beautiful console output** with Rich formatting
- ✅ **Graceful shutdown** with signal handlers
- ✅ **Configurable retries** with custom logic hooks

## Comparison with Alternatives

AsyncTasQ differentiates itself with **true async-first architecture**, **ORM auto-serialization**, **5 production backends** (Redis, PostgreSQL, MySQL, RabbitMQ, SQS), **ACID guarantees**, and **dead-letter queues**.

| Feature                    | AsyncTasQ                         | Celery     | ARQ      | Dramatiq  | RQ       | Huey      |
| -------------------------- | --------------------------------- | ---------- | -------- | --------- | -------- | --------- |
| **Async**                  | ✅ Native                          | ❌ No       | ✅ Yes    | ⚠️ Limited | ❌ No     | ⚠️ Limited |
| **Type Safety**            | ✅ Full type hints and IDE support | ⚠️ External | ✅ Yes    | ✅ Yes     | ✅ Yes    | ⚠️ Limited |
| **Backends**               | 5                                 | 3          | 1        | 2         | 1        | 4         |
| **ORM Auto-serialization** | ✅ Yes                             | ❌ No       | ❌ No     | ❌ No      | ❌ No     | ❌ No      |
| **ACID**                   | ✅ Yes                             | ❌ No       | ❌ No     | ❌ No      | ❌ No     | ❌ No      |
| **DLQ**                    | ✅ Built-in                        | ⚠️ Manual   | ❌ No     | ✅ Yes     | ❌ No     | ❌ No      |
| **FastAPI**                | ✅ Native                          | ⚠️ Manual   | ⚠️ Manual | ⚠️ Manual  | ⚠️ Manual | ⚠️ Manual  |

**Choose AsyncTasQ for:** Modern async apps (FastAPI, aiohttp), type-safe codebases, automatic ORM handling, enterprise ACID requirements, multi-backend flexibility.

**Choose alternatives for:** Mature ecosystems with many plugins (Celery), cron scheduling (Huey, ARQ), simple sync applications (RQ), or existing large codebases.

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for setup and development workflow:

```bash
just init        # One-line setup with deps and hooks
just docker-up   # Start Redis, PostgreSQL, MySQL, RabbitMQ, LocalStack
just test        # Run all tests (or just test-unit / just test-integration)
just ci          # Full CI suite locally
```

## Roadmap

- [ ] SQLite & Oracle drivers
- [ ] Task chaining & workflows
- [ ] Rate limiting & task priority
- [ ] Scheduled/cron tasks

## License & Support

MIT License – see [LICENSE](LICENSE).

**Links:** [Repository](https://github.com/adamrefaey/asynctasq) • [Issues](https://github.com/adamrefaey/asynctasq/issues) • [Discussions](https://github.com/adamrefaey/asynctasq/discussions)

Built with ❤️ by [Adam Refaey](https://github.com/adamrefaey)
