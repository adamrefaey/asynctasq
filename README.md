# AsyncTasQ

[![Tests](https://raw.githubusercontent.com/adamrefaey/asynctasq/main/.github/tests.svg)](https://github.com/adamrefaey/asynctasq/actions/workflows/ci.yml)
[![Coverage](https://raw.githubusercontent.com/adamrefaey/asynctasq/main/.github/coverage.svg)](https://raw.githubusercontent.com/adamrefaey/asynctasq/main/.github/coverage.svg)
[![Python Version](https://raw.githubusercontent.com/adamrefaey/asynctasq/main/.github/python-version.svg)](https://www.python.org/downloads/)
[![PyPI Version](https://img.shields.io/pypi/v/asynctasq)](https://pypi.org/project/asynctasq/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

A modern, async-first, type-safe task queue Python package inspired by Laravel. Runs on uvloop for maximum performance. Native FastAPI integration. Switch between multiple queue backends (Redis, PostgreSQL, MySQL, RabbitMQ, AWS SQS) with one config line. Automatic, smart ORM serialization (SQLAlchemy, Django, Tortoise) using msgpack reduces payloads by 90%+. Features ACID guarantees, dead-letter queues, crash recovery, and real-time event streaming.

---

## Table of Contents

- [Quick Start](#quick-start)
- [Documentation](#documentation)
- [Examples](#examples)
- [Why AsyncTasQ?](#why-asynctasq)
- [Key Features](#key-features)
- [Comparison with Alternatives](#comparison-with-alternatives)
- [Contributing](#contributing)
- [License](#license)
- [Support](#support)
- [Roadmap](#roadmap)

---

## Quick Start

```bash
# Install with your preferred driver
uv add "asynctasq[redis]"

# Generate .env.example template
asynctasq publish

# Configure your environment (see docs/environment-variables.md for details)
cp .env.example .env  # Edit with your settings
```

Note: This example requires a Redis server running on localhost:6379. If you don't have Redis installed, you can start one using Docker:

```bash
docker run -d --name redis-test -p 127.0.0.1:6379:6379 redis:8.0-alpine
```

Create a new file named `quick_start.py` and add the following code:

```python
import asyncio

from asynctasq import AsyncTask, RedisConfig, TaskConfig, init, print, task

# 1. Configure AsyncTasQ (see docs/environment-variables.md for detailed setup)
init()  # Loads from .env (recommended) or environment variables

# For quick testing without .env file:
# init({"driver": "redis", "redis": RedisConfig(url="redis://localhost:6379")})


# 2. Define tasks (function-based or class-based)
# Function-based task
@task
async def send_email(to: str, subject: str, body: str):
    # Use asynctasq.print() for beautiful Rich-formatted console output
    print(f"[cyan]Sending email to[/cyan] [yellow]{to}[/yellow]: [bold]{subject}[/bold]")
    await asyncio.sleep(1)  # Simulate email sending
    return f"Email sent to {to}"


# Class-based task with TaskConfig
class ProcessPayment(AsyncTask[bool]):
    config: TaskConfig = {
        "queue": "payments",
        "max_attempts": 3,
        "retry_delay": 60,
        "timeout": 30,
        "correlation_id": None,
    }

    def __init__(self, user_id: int, amount: float, **kwargs):
        super().__init__(**kwargs)
        self.user_id = user_id
        self.amount = amount

    async def execute(self) -> bool:
        # Use asynctasq.print() for beautiful Rich-formatted console output
        print(
            f"[green]Processing[/green] [bold]${self.amount}[/bold] for user [cyan]{self.user_id}[/cyan]"
        )
        await asyncio.sleep(2)  # Simulate payment processing
        return True


# 3. Dispatch tasks with optional configuration chaining
async def main():
    # Function-based task dispatch
    for i in range(10):
        task_id = await send_email(
            to=f"user{i}@example.com", subject=f"Welcome {i}!", body="Welcome to our platform!"
        ).dispatch()
        print(f"Task dispatched: {task_id}")

    # Class-based task dispatch with TaskConfig defaults
    payment_task_id = await ProcessPayment(user_id=123, amount=99.99).dispatch()
    print(f"Payment task dispatched: {payment_task_id}")

    # With configuration chaining (overrides TaskConfig)
    critical_task_id = (
        await send_email(to="admin@example.com", subject="Critical Alert", body="System issue!")
        .on_queue("high-priority")
        .max_attempts(10)
        .timeout(60)
        .dispatch()
    )
    print(f"Critical task dispatched: {critical_task_id}")

    # Class-based with method chaining
    urgent_payment_id = (
        await ProcessPayment(user_id=456, amount=199.99)
        .on_queue("urgent")
        .max_attempts(5)
        .timeout(120)
        .dispatch()
    )
    print(f"Urgent payment dispatched: {urgent_payment_id}")


if __name__ == "__main__":
    # AsyncTasQ works with any event loop - choose what works best for you:

    # Option 1: Use AsyncTasQ's runner (automatic uvloop support)
    from asynctasq import run

    run(main())

    # Option 2: Use standard asyncio
    # import asyncio
    # asyncio.run(main())

    # Option 3: Use uvloop directly
    # import uvloop
    # uvloop.run(main())

```

Run the script to dispatch tasks:

```bash
uv run python quick_start.py
```

In a separate terminal, run the worker to process the tasks:

```bash
# Worker uses the same .env configuration automatically
uv run asynctasq worker --queues urgent,high-priority,payments,default
```

**That's it!** Your first AsyncTasQ application is ready. AsyncTasQ works seamlessly with `asyncio.run()`, uvloop, FastAPI, Jupyter notebooks, or any other async framework - cleanup happens automatically when the event loop closes.

To stop and remove the Redis container when done:

```bash
docker stop redis-test && docker rm redis-test
```

---

## Documentation

Comprehensive guides to get you started:

- **[Installation](https://github.com/adamrefaey/asynctasq/blob/main/docs/installation.md#installation)** – Installation instructions for uv and pip
- **[Configuration](https://github.com/adamrefaey/asynctasq/blob/main/docs/configuration.md)** – Complete configuration guide with `asynctasq.init()` and `Config.get()`
  - Configuration properties apply to different contexts: **dispatch** (when enqueuing tasks) vs **worker** (when processing tasks)
  - Driver configs (redis, postgres, mysql, rabbitmq, sqs) and events config apply to **both contexts**
  - **⚠️ IMPORTANT:** See [Visibility Timeout Warning](https://github.com/adamrefaey/asynctasq/blob/main/docs/configuration.md#visibility-timeout-warning) for critical `visibility_timeout` configuration details
- **[Environment Variables](https://github.com/adamrefaey/asynctasq/blob/main/docs/environment-variables.md)** – Complete guide to .env file support and environment variable configuration
- **[Task Definitions](https://github.com/adamrefaey/asynctasq/blob/main/docs/task-definitions.md#task-types-and-execution-modes)** – Function-based and class-based tasks with all four execution modes
- **[Queue Drivers](https://github.com/adamrefaey/asynctasq/blob/main/docs/queue-drivers.md#overview)** – Redis, PostgreSQL, MySQL, RabbitMQ, AWS SQS with feature comparison
- **[Running Workers](https://github.com/adamrefaey/asynctasq/blob/main/docs/running-workers.md#cli-workers-recommended)** – CLI and programmatic workers, deployment patterns
- **[Monitoring](https://github.com/adamrefaey/asynctasq/blob/main/docs/monitoring.md#event-streaming)** – Real-time event streaming and queue statistics
- **[ORM Integrations](https://github.com/adamrefaey/asynctasq/blob/main/docs/orm-integrations.md#how-it-works)** – Automatic serialization for SQLAlchemy, Django ORM, Tortoise ORM
- **[Framework Integrations](https://github.com/adamrefaey/asynctasq/blob/main/docs/framework-integrations.md#fastapi-integration)** – FastAPI lifespan integration and configuration
- **[CLI Reference](https://github.com/adamrefaey/asynctasq/blob/main/docs/cli-reference.md#worker-command)** – Complete command reference for worker, migrate, and publish
- **[Best Practices](https://github.com/adamrefaey/asynctasq/blob/main/docs/best-practices.md#task-design)** – Task design guidelines, error handling, queue organization, production deployment

---

## Examples

Complete code examples:

- **[Function-Based Tasks Examples](https://github.com/adamrefaey/asynctasq/blob/main/docs/examples/function-based-tasks.md#basic-usage)** – Decorators, configuration, method chaining, and practical patterns
- **[Class-Based Tasks Examples](https://github.com/adamrefaey/asynctasq/blob/main/docs/examples/class-based-tasks.md#all-four-task-types)** – All four task types, lifecycle hooks, and advanced patterns

---

## Why AsyncTasQ?

### True Async-First Architecture

Unlike Celery and RQ which are built on synchronous foundations, AsyncTasQ is **designed from the ground up for asyncio**:

- **Native async/await everywhere** – All core operations use asyncio, no threading or blocking on critical paths
- **Four execution modes** – Choose the right execution strategy for each task: async I/O (event loop), sync I/O (thread pool), async CPU-bound (process pool), or sync CPU-bound (process pool). See [Task Definitions](https://github.com/adamrefaey/asynctasq/blob/main/docs/task-definitions.md#task-types-and-execution-modes) for detailed comparison.
- **High-performance concurrency** – Process hundreds of tasks concurrently with minimal overhead using asyncio's efficient task scheduling
- **Smart connection pooling** – All drivers use connection pools optimized for async operations
- **Non-blocking by design** – Worker polling, task execution, and all I/O operations are truly non-blocking
- **Universal event loop compatibility** – AsyncTasQ works seamlessly with any event loop (asyncio, uvloop, or custom implementations). Cleanup hooks automatically attach to running loops, so you can use `asyncio.run()`, uvloop, FastAPI, Jupyter notebooks, or any other async framework. The optional `asynctasq.utils.loop.run` helper provides uvloop support with automatic fallback to asyncio.

### Intelligent Serialization & ORM Integration

- **msgpack binary encoding** – 2-3x faster than JSON with smaller payloads
- **Automatic ORM model handling** – Pass SQLAlchemy, Django ORM, or Tortoise ORM models directly as task arguments. AsyncTasQ automatically:
  - Serializes them as lightweight references (primary key only)
  - Reduces payload size by 90%+
  - Re-fetches with fresh data when the task executes
  - Supports all 3 major Python ORMs out of the box
- **Smart type handling** – Native support for `datetime`, `Decimal`, `UUID`, `set`, and custom types without manual conversion

### Enterprise-Grade Reliability

- **ACID guarantees** – PostgreSQL and MySQL drivers provide transactional dequeue with exactly-once processing semantics
- **Built-in dead-letter queues** – PostgreSQL/MySQL drivers automatically move permanently failed tasks to DLQ for inspection
- **Crash recovery** – Visibility timeouts ensure no task is lost even if workers crash mid-execution
- **Graceful shutdown** – SIGTERM/SIGINT handlers drain in-flight tasks before stopping (configurable timeout)
- **Flexible retry strategies** – Per-task retry configuration with custom `should_retry()` hooks for intelligent retry logic
- **Task timeout protection** – Prevent runaway tasks with configurable per-task timeouts
- **Real-time observability** – Redis Pub/Sub event streaming broadcasts task lifecycle events for monitoring dashboards

### Developer Experience That Just Works

- **Elegant, Laravel-inspired API** – Clean, intuitive syntax that feels natural
- **Full type safety** – Complete type hints, mypy/pyright compatible, Generic `Task[T]` for return type checking
- **Simple configuration** – Use `asynctasq.init()` and `Config.get()` for all configuration needs
- **Two task styles** – Choose function-based `@task` decorators or class-based tasks with lifecycle hooks
- **Fluent method chaining** – Configure tasks expressively: `.delay(60).on_queue("high").max_attempts(10).timeout(300).dispatch()`
- **Beautiful console output** – Built-in Rich integration provides colorized logging, syntax highlighting, and formatted output. Use `asynctasq.print()` in tasks for gorgeous terminal displays with zero configuration
- **First-class FastAPI integration** – Lifespan management, automatic connection pooling, native async support

### Multi-Driver Flexibility Without Vendor Lock-In

- **5 production-ready drivers** – Redis, PostgreSQL, MySQL, RabbitMQ, AWS SQS – all with the same API
- **Switch with one line** – Change `driver="redis"` to `driver="postgres"` – no code changes needed
- **Per-task driver override** – Use Redis for high-throughput tasks, PostgreSQL for ACID-critical tasks in the same application
- **Same API, different guarantees** – Choose the driver that matches your SLA requirements without rewriting code

---

## Key Features

### Core Capabilities

  - ✅ **Async-first design** with asyncio throughout the stack

  - ✅ **Multiple queue drivers**: Redis, PostgreSQL, MySQL, RabbitMQ, AWS SQS

  - ✅ **Environment variables & .env file support** for easy configuration across environments

  - ✅ **High-performance msgpack serialization** with binary support

  - ✅ **Automatic ORM model handling** for SQLAlchemy, Django, Tortoise

  - ✅ **Type-safe** with full type hints and Generic support

  - ✅ **Four execution modes**: Async I/O (event loop), Sync I/O (thread pool), Async CPU-bound (process pool), Sync CPU-bound (process pool)

  - ✅ **Beautiful console output** with Rich library integration for colorized logs and formatted task output

  - ✅ **Configurable retries** with custom retry logic hooks

  - ✅ **Task timeouts** to prevent runaway tasks

  - ✅ **Delayed task execution** with precision timing

  - ✅ **Queue priority** with multiple queues per worker

  - ✅ **Graceful shutdown** with signal handlers

### Enterprise Features

  - ✅ **ACID guarantees** (PostgreSQL/MySQL drivers)

  - ✅ **Dead-letter queues** for failed task inspection

  - ✅ **Visibility timeouts** for crash recovery

  - ✅ **Connection pooling** for optimal resource usage

  - ✅ **Transactional dequeue** with `SELECT FOR UPDATE SKIP LOCKED`

  - ✅ **Task metadata tracking** (attempts, timestamps, task IDs)

  - ✅ **Concurrent processing** with configurable worker concurrency

  - ✅ **Real-time event streaming** via Redis Pub/Sub

### Integrations

  - ✅ **FastAPI** – Automatic lifecycle management, dependency injection

  - ✅ **SQLAlchemy** – Async and sync model serialization

  - ✅ **Django ORM** – Native async support (Django 5.0+)

  - ✅ **Tortoise ORM** – Full async ORM integration

  - ✅ **[asynctasq-monitor](https://github.com/adamrefaey/asynctasq-monitor)** – Real-time monitoring dashboard (optional)

### Developer Tools

  - ✅ **Comprehensive CLI** – Worker management and database migrations

  - ✅ **Function-based tasks** with `@task` decorator

  - ✅ **Class-based tasks** with 4 execution modes:
    - `AsyncTask` – Async I/O-bound (API calls, async DB queries)
    - `SyncTask` – Sync I/O-bound via thread pool (`requests`, sync DB drivers)
    - `AsyncProcessTask` – Async CPU-intensive via process pool
    - `SyncProcessTask` – Sync CPU-intensive via process pool (bypasses GIL)

  - ✅ **Lifecycle hooks** – `execute()`, `failed()`, `should_retry()` for complete control

  - ✅ **Method chaining** for fluent task configuration

  - ✅ **Flexible configuration** – Use `asynctasq.init()` / `Config.get()` for all settings

---

## Comparison with Alternatives

### AsyncTasQ vs. Celery

| Feature                  | AsyncTasQ                                         | Celery                                                    |
| ------------------------ | ------------------------------------------------- | --------------------------------------------------------- |
| **Async Support**        | ✅ Async-first, built with asyncio                 | ❌ No asyncio support (promised for years, not delivered)  |
| **Type Safety**          | ✅ Full type hints, Generic[T]                     | ⚠️ Third-party stubs (celery-types)                        |
| **Multi-Driver**         | ✅ 5 drivers (Redis/PostgreSQL/MySQL/RabbitMQ/SQS) | ⚠️ 3 brokers (Redis/RabbitMQ/SQS)                          |
| **ORM Integration**      | ✅ Auto-serialization (SQLAlchemy/Django/Tortoise) | ❌ Manual serialization required                           |
| **Serialization**        | ✅ msgpack (fast, binary, efficient)               | ⚠️ JSON default (pickle/YAML/msgpack available)            |
| **FastAPI Integration**  | ✅ First-class, lifespan management                | ⚠️ Manual setup, workarounds needed                        |
| **Dead-Letter Queue**    | ✅ Built-in (PostgreSQL/MySQL)                     | ⚠️ Manual setup (RabbitMQ DLX)                             |
| **ACID Guarantees**      | ✅ PostgreSQL/MySQL drivers                        | ❌ Not available                                           |
| **Global Rate Limiting** | ⚠️ Not yet implemented                             | ❌ Not available (per-worker only)                         |
| **Setup Complexity**     | ✅ Simple with `asynctasq.init()`                  | ⚠️ Complex configuration                                   |
| **Prefetch Multiplier**  | ✅ Sensible default (1)                            | ⚠️ Dangerous default (4x), often causes performance issues |
| **Learning Curve**       | ✅ Simple, intuitive API                           | ⚠️ Steep learning curve                                    |

**When to use AsyncTasQ:**

- Modern async Python applications (FastAPI, aiohttp, async web frameworks)
- Need true asyncio support for I/O-bound tasks (API calls, database queries)
- Type-safe codebase with full IDE support
- Multiple driver flexibility (dev → production migration)
- Automatic ORM model handling (SQLAlchemy, Django, Tortoise)
- Enterprise ACID requirements (financial transactions, critical workflows)
- Simple, clean API without steep learning curve

**When to use Celery:**

- Mature ecosystem with many plugins and extensions
- Complex workflows (chains, chords, groups with callbacks)
- Large existing Celery codebase that's not worth migrating
- Synchronous applications where asyncio isn't needed
- Need for battle-tested, widely-adopted solution

---

### AsyncTasQ vs. Dramatiq

| Feature                 | AsyncTasQ                                         | Dramatiq                                                  |
| ----------------------- | ------------------------------------------------- | --------------------------------------------------------- |
| **Async Support**       | ✅ Async-first, native asyncio                     | ⚠️ Limited (via async-dramatiq extension, not first-class) |
| **Type Safety**         | ✅ Full type hints, Generic[T]                     | ✅ Type hints (py.typed)                                   |
| **Multi-Driver**        | ✅ 5 drivers (Redis/PostgreSQL/MySQL/RabbitMQ/SQS) | ⚠️ 2 brokers (Redis/RabbitMQ)                              |
| **ORM Integration**     | ✅ Auto-serialization (SQLAlchemy/Django/Tortoise) | ❌ Manual serialization required                           |
| **Dead-Letter Queue**   | ✅ Built-in (PostgreSQL/MySQL)                     | ✅ Built-in (all brokers)                                  |
| **FastAPI Integration** | ✅ First-class, lifespan management                | ⚠️ Manual setup needed                                     |
| **Database Drivers**    | ✅ PostgreSQL/MySQL with ACID                      | ❌ Not available                                           |
| **Simplicity**          | ✅ Clean, intuitive API                            | ✅ Simple, well-designed                                   |

**When to use AsyncTasQ:**

- Async-first applications (FastAPI, aiohttp, modern Python stack)
- True asyncio support for I/O-bound tasks
- Database-backed queues with ACID guarantees
- Automatic ORM model serialization
- Type-safe codebase with IDE support

**When to use Dramatiq:**

- Synchronous applications
- Mature, battle-tested solution needed
- Complex middleware requirements
- Don't need async support

---

### AsyncTasQ vs. ARQ (Async Redis Queue)

| Feature                  | AsyncTasQ                                         | ARQ                                   |
| ------------------------ | ------------------------------------------------- | ------------------------------------- |
| **Async Support**        | ✅ Async-first, native asyncio                     | ✅ Async-first, native asyncio         |
| **Multi-Driver**         | ✅ 5 drivers (Redis/PostgreSQL/MySQL/RabbitMQ/SQS) | ❌ Redis only                          |
| **Type Safety**          | ✅ Full type hints, Generic[T]                     | ✅ Type hints                          |
| **ORM Integration**      | ✅ Auto-serialization (SQLAlchemy/Django/Tortoise) | ❌ Manual serialization                |
| **Serialization**        | ✅ msgpack (binary, efficient)                     | ⚠️ pickle (default, security concerns) |
| **Dead-Letter Queue**    | ✅ Built-in (PostgreSQL/MySQL)                     | ❌ Not available                       |
| **ACID Guarantees**      | ✅ PostgreSQL/MySQL drivers                        | ❌ Not available                       |
| **FastAPI Integration**  | ✅ First-class, lifespan management                | ⚠️ Manual setup                        |
| **Task Execution Model** | ✅ At-least-once with idempotency support          | ⚠️ At-least-once ("pessimistic")       |
| **Simplicity**           | ✅ Clean, Laravel-inspired API                     | ✅ Lightweight, minimal                |
| **Custom Serializers**   | ✅ Configurable serializers                        | ✅ Configurable serializers            |

**When to use AsyncTasQ:**

- Need multiple driver options (not locked into Redis)
- Database-backed queues with ACID guarantees
- Automatic ORM model handling
- Dead-letter queue support for failed task inspection
- FastAPI applications with first-class integration
- Enterprise reliability requirements

**When to use ARQ:**

- Simple Redis-only infrastructure
- Lightweight solution with minimal dependencies
- Cron job scheduling is a primary requirement
- Mature async task queue needed
- Custom serializers (e.g., msgpack) are acceptable to configure manually

---

### AsyncTasQ vs. RQ (Redis Queue)

| Feature               | AsyncTasQ                                         | RQ                               |
| --------------------- | ------------------------------------------------- | -------------------------------- |
| **Async Support**     | ✅ Async-first, native asyncio                     | ❌ Sync only (no asyncio support) |
| **Multi-Driver**      | ✅ 5 drivers (Redis/PostgreSQL/MySQL/RabbitMQ/SQS) | ❌ Redis only                     |
| **Type Safety**       | ✅ Full type hints, Generic[T]                     | ✅ Type hints added               |
| **Retries**           | ✅ Configurable with custom `should_retry()`       | ✅ Configurable retries           |
| **Dead-Letter Queue** | ✅ Built-in (PostgreSQL/MySQL)                     | ❌ Not available                  |
| **Database Drivers**  | ✅ PostgreSQL/MySQL with ACID                      | ❌ Not available                  |
| **Simplicity**        | ✅ Intuitive, clean API                            | ✅ Very simple                    |

**When to use AsyncTasQ:**

- Async applications (FastAPI, aiohttp)
- True asyncio support for efficient I/O
- Multiple driver options
- Enterprise features (DLQ, ACID)
- ORM integration

**When to use RQ:**

- Simple, synchronous use cases
- Synchronous applications
- Redis-only infrastructure
- Need mature, battle-tested solution

---

### AsyncTasQ vs. Huey

| Feature                 | AsyncTasQ                                         | Huey                                               |
| ----------------------- | ------------------------------------------------- | -------------------------------------------------- |
| **Async Support**       | ✅ Async-first, native asyncio                     | ⚠️ Limited (async result awaiting only via helpers) |
| **Multi-Driver**        | ✅ 5 drivers (Redis/PostgreSQL/MySQL/RabbitMQ/SQS) | ⚠️ Redis/SQLite/Filesystem/Memory                   |
| **Type Safety**         | ✅ Full type hints, Generic[T]                     | ⚠️ Limited type hints                               |
| **ORM Integration**     | ✅ Auto-serialization (SQLAlchemy/Django/Tortoise) | ❌ Manual serialization                             |
| **Enterprise Features** | ✅ ACID, DLQ, visibility timeout                   | ⚠️ Basic features                                   |
| **Simplicity**          | ✅ Clean, modern API                               | ✅ Simple, lightweight                              |
| **Cron Jobs**           | ⚠️ Not yet implemented                             | ✅ Built-in periodic tasks                          |

**When to use AsyncTasQ:**

- Async-first applications requiring true asyncio
- Enterprise requirements (ACID, DLQ)
- Type-safe codebase with IDE support
- Automatic ORM integration
- Need for multiple driver options

**When to use Huey:**

- Lightweight use cases
- Simple periodic/cron tasks
- SQLite-backed queues for embedded apps
- Mature, stable solution needed

---

### Key Differentiators

**AsyncTasQ stands out with:**

1. **True async-first architecture** – Built with asyncio from the ground up (unlike Celery, RQ, Huey)
2. **Multiple execution modes** – Choose async I/O, sync I/O (thread pool), or CPU-bound (process pool) per task
3. **Intelligent ORM handling** – Automatic model serialization for SQLAlchemy, Django ORM, and Tortoise ORM (90%+ smaller payloads)
4. **msgpack serialization** – Binary format that's 2-3x faster than JSON with smaller payloads
5. **Multi-driver flexibility** – 5 production-ready drivers (Redis, PostgreSQL, MySQL, RabbitMQ, AWS SQS) with identical API
6. **Type safety everywhere** – Full type hints with Generic[T] support, mypy/pyright compatible
7. **Enterprise ACID guarantees** – PostgreSQL/MySQL drivers with transactional dequeue for exactly-once processing
8. **Built-in dead-letter queues** – PostgreSQL/MySQL drivers automatically handle permanently failed tasks
9. **First-class FastAPI integration** – Lifespan management, automatic connection pooling, native async support
10. **Real-time event streaming** – Redis Pub/Sub broadcasts task lifecycle events for monitoring
11. **Optional monitoring UI** – Beautiful real-time dashboard via [asynctasq-monitor](https://github.com/adamrefaey/asynctasq-monitor)
12. **Elegant, Laravel-inspired API** – Method chaining (`.delay(60).on_queue("high").dispatch()`) and intuitive task definitions
13. **Simple configuration** – Use `asynctasq.init()` and `Config.get()` for all configuration needs

---

## CI & Contributing (short)

- **One-line setup:** `just init` — install deps and pre-commit hooks
- **Start services:** `just docker-up` — Redis, PostgreSQL, MySQL, RabbitMQ, LocalStack (SQS) for local integration tests
- **Run tests:** `just test` — use `just test-unit` / `just test-integration` to scope
- **Run with coverage:** `just test-cov` or `pytest --cov=src/asynctasq --cov-report=html`
- **Run the worker locally:** `python -m asynctasq worker`
- **Pre-commit hooks:** [`./setup-pre-commit.sh`](https://github.com/adamrefaey/asynctasq/blob/main/setup-pre-commit.sh) or `just setup-hooks`
- **Format / lint / typecheck:** `just format`, `just lint`, `just typecheck`
- **CI runs on PRs and pushes to `main`** and includes lint, type checks and tests across Python 3.12–3.14.
- **Pre-commit hooks** enforce formatting and static checks locally before commits (see [`./setup-pre-commit.sh`](https://github.com/adamrefaey/asynctasq/blob/main/setup-pre-commit.sh)).
- **Branch protection:** enable required status checks (CI success, lint, unit/integration jobs) for `main`.
- **Coverage badge:** the repository updates `.github/coverage.svg` automatically via `.github/workflows/coverage-badge.yml`.
- **Run full CI locally:** `just ci` (runs format/lint/typecheck/tests like the workflow).

---

## Contributing

Contributions are welcome! Please see [CONTRIBUTING.md](https://github.com/adamrefaey/asynctasq/blob/main/CONTRIBUTING.md) for guidelines.

---

## License

MIT License – see [LICENSE](https://github.com/adamrefaey/asynctasq/blob/main/LICENSE) file for details.

---

## Support

- **Repository:** [github.com/adamrefaey/asynctasq](https://github.com/adamrefaey/asynctasq)
- **Issues:** [github.com/adamrefaey/asynctasq/issues](https://github.com/adamrefaey/asynctasq/issues)
- **Discussions:** [github.com/adamrefaey/asynctasq/discussions](https://github.com/adamrefaey/asynctasq/discussions)

---

## Roadmap

- [ ] SQLite driver support
- [ ] Oracle driver support
- [ ] Task batching support
- [ ] Task chaining and workflows (chains, chords, groups)
- [ ] Rate limiting
- [ ] Task priority within queues
- [ ] Scheduled/cron tasks

---

## Credits

Built with ❤️ by [Adam Refaey](https://github.com/adamrefaey).
