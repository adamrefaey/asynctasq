# Async Task

[![Python Version](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

A modern, async-first, type-safe task queue Python package inspired by Laravel. Switch between multiple queue backends (Memory, Redis, PostgreSQL, MySQL, AWS SQS) with one config line. Automatic ORM serialization (SQLAlchemy, Django, Tortoise) using msgpack reduces payloads by 90%+. Features ACID guarantees, dead-letter queues, crash recovery, and native FastAPI integration.

---

## Table of Contents

- [Why Async Task?](#why-async-task)
- [Key Features](#key-features)
- [Installation](#installation)
- [Quick Start](#quick-start)
- [Queue Drivers](#queue-drivers)
- [ORM Integrations](#orm-integrations)
- [Framework Integrations](#framework-integrations)
- [Task Definitions](#task-definitions)
- [Running Workers](#running-workers)
- [Configuration](#configuration)
- [CLI Reference](#cli-reference)
- [Comparison with Alternatives](#comparison-with-alternatives)
- [Best Practices](#best-practices)
- [Contributing](#contributing)
- [License](#license)
- [Credits](#credits)
- [Support](#support)
- [Roadmap](#roadmap)

---

## Why Async Task?

### Async-First Architecture

- **Built with asyncio from the ground up** – No threading, no blocking operations on critical paths
- **Native async/await support** – Seamless integration with modern Python async code
- **High concurrency** – Process thousands of tasks concurrently with minimal resource usage
- **Efficient I/O** – Connection pooling for all database drivers

### High-Performance Serialization

- **msgpack encoding** – Binary serialization that's faster and more compact than JSON
- **Efficient binary handling** – Native `use_bin_type=True` for optimal bytes processing
- **Automatic ORM model handling** – Pass SQLAlchemy, Django, or Tortoise models directly as task parameters. They're automatically serialized as lightweight references (PK only), reducing payload size by 90%+, then re-fetched with fresh data when the task executes
- **Custom type support** – Native handling of datetime, Decimal, UUID, sets without manual conversion

### Production-Ready Features

- **Enterprise ACID guarantees** – PostgreSQL/MySQL drivers with transactional dequeue
- **Dead-letter queues** – Automatic handling of permanently failed tasks
- **Crash recovery** – Visibility timeouts ensure tasks are never lost
- **Graceful shutdown** – SIGTERM/SIGINT handlers wait for in-flight tasks to complete
- **Configurable retries** – Per-task retry logic with custom `should_retry()` hooks
- **Task timeouts** – Prevent runaway tasks with per-task timeout configuration

### Developer Experience

- **Elegant, intuitive API** – Clean, expressive syntax inspired by Laravel's queue system
- **Type-safe** – Full type hints with mypy/pyright support, Generic Task[T] for return types
- **Zero configuration** – Works with environment variables out of the box
- **Multiple task styles** – Function-based decorators or class-based tasks with lifecycle hooks
- **Method chaining** – Fluent API for task configuration: `.delay(60).on_queue("high").dispatch()`
- **First-class FastAPI integration** – Automatic lifecycle management and dependency injection

### Multi-Driver Flexibility

- **Switch drivers instantly** – Change one config line to swap between Memory, Redis, PostgreSQL, MySQL, or AWS SQS
- **Same API everywhere** – Write once, run on any driver without code changes
- **Per-task driver override** – Different tasks can use different drivers in the same application
- **Production-ready options** – From in-memory testing to enterprise databases to managed cloud queues

---

## Key Features

### Core Capabilities

✅ **Async-first design** with asyncio throughout the stack
✅ **Multiple queue drivers**: Memory, Redis, PostgreSQL, MySQL, AWS SQS
✅ **High-performance msgpack serialization** with binary support
✅ **Automatic ORM model handling** for SQLAlchemy, Django, Tortoise
✅ **Type-safe** with full type hints and Generic support
✅ **Configurable retries** with custom retry logic hooks
✅ **Task timeouts** to prevent runaway tasks
✅ **Delayed task execution** with precision timing
✅ **Queue priority** with multiple queues per worker
✅ **Graceful shutdown** with signal handlers

### Enterprise Features

✅ **ACID guarantees** (PostgreSQL/MySQL drivers)
✅ **Dead-letter queues** for failed task inspection
✅ **Visibility timeouts** for crash recovery
✅ **Connection pooling** for optimal resource usage
✅ **Transactional dequeue** with `SELECT FOR UPDATE SKIP LOCKED`
✅ **Task metadata tracking** (attempts, timestamps, task IDs)
✅ **Concurrent processing** with configurable worker concurrency

### Integrations

✅ **FastAPI** – Automatic lifecycle management, dependency injection
✅ **SQLAlchemy** – Async and sync model serialization
✅ **Django ORM** – Native async support (Django 3.1+)
✅ **Tortoise ORM** – Full async ORM integration

### Developer Tools

✅ **Comprehensive CLI** – Worker management and database migrations
✅ **Function-based tasks** with `@task` decorator
✅ **Class-based tasks** with lifecycle hooks (`handle`, `failed`, `should_retry`)
✅ **Method chaining** for fluent task configuration
✅ **Environment variable configuration** for 12-factor apps

---

## Installation

### Using uv (Recommended)

[uv](https://github.com/astral-sh/uv) is a fast Python package installer and resolver.

```bash
# Basic installation
uv add async-task

# With specific drivers
uv add "async-task[redis]"      # Redis support
uv add "async-task[postgres]"   # PostgreSQL support
uv add "async-task[mysql]"      # MySQL support
uv add "async-task[sqs]"        # AWS SQS support

# With ORM support
uv add "async-task[sqlalchemy]" # SQLAlchemy
uv add "async-task[django]"     # Django
uv add "async-task[tortoise]"   # Tortoise ORM

# With framework integrations
uv add "async-task[fastapi]"    # FastAPI integration

# Complete installation with all features
uv add "async-task[all]"
```

### Using pip

```bash
# Basic installation
pip install async-task

# With specific drivers
pip install "async-task[redis]"
pip install "async-task[postgres]"
pip install "async-task[mysql]"
pip install "async-task[sqs]"

# With ORM support
pip install "async-task[sqlalchemy]"
pip install "async-task[django]"
pip install "async-task[tortoise]"

# With framework integrations
pip install "async-task[fastapi]"

# Complete installation
pip install "async-task[all]"
```

---

## Quick Start

Get started in 60 seconds:

```python
import asyncio
from async_task.core.task import task
from async_task.config import set_global_config

# 1. Configure (or use environment variables)
set_global_config(driver='memory')  # Use 'redis' for production

# 2. Define a task
@task(queue='emails')
async def send_email(to: str, subject: str, body: str):
    print(f"Sending email to {to}: {subject}")
    await asyncio.sleep(1)  # Simulate email sending
    return f"Email sent to {to}"

# 3. Dispatch the task
async def main():
    task_id = await send_email.dispatch(
        to="user@example.com",
        subject="Welcome!",
        body="Welcome to our platform!"
    )
    print(f"Task dispatched: {task_id}")

# 4. Run a worker to process tasks
# Terminal: python -m async_task worker

if __name__ == "__main__":
    asyncio.run(main())
```

**That's it!** Your first async task queue is ready. Now let's explore the powerful features.

---

## Queue Drivers

Async Task supports five production-ready queue drivers with identical APIs.

### Memory Driver

**Best for:** Development, testing, single-process applications

**Features:**

- In-memory storage using Python collections (deque + list)
- No external dependencies or infrastructure
- Fast (<0.1ms latency, 50k+ tasks/sec)
- Delayed task support with 100ms precision
- Data lost on process restart

**Installation:**

```bash
# No extra dependencies needed
uv add async-task
```

**Configuration:**

```python
# Environment variables
export ASYNC_TASK_DRIVER=memory

# Or programmatic
from async_task.config import set_global_config
set_global_config(driver='memory')
```

**Use cases:** Local development, unit testing, prototyping

---

### Redis Driver

**Best for:** Production applications, distributed systems, high throughput

**Features:**

- Reliable Queue Pattern using `LMOVE` (atomic operations)
- Delayed tasks with Sorted Sets (score = Unix timestamp)
- Processing list for crash recovery
- Connection pooling for optimal performance
- RESP3 protocol support

**Requirements:** Redis 6.2+ (for `LMOVE` command support)

**Installation:**

```bash
# With uv
uv add "async-task[redis]"

# With pip
pip install "async-task[redis]"
```

**Configuration:**

```bash
# Environment variables
export ASYNC_TASK_DRIVER=redis
export ASYNC_TASK_REDIS_URL=redis://localhost:6379
export ASYNC_TASK_REDIS_PASSWORD=secret  # Optional
export ASYNC_TASK_REDIS_DB=0
export ASYNC_TASK_REDIS_MAX_CONNECTIONS=10
```

```python
# Programmatic configuration
from async_task.config import set_global_config

set_global_config(
    driver='redis',
    redis_url='redis://localhost:6379',
    redis_password='secret',  # Optional
    redis_db=0,
    redis_max_connections=10
)
```

**Architecture:**

- Immediate tasks: Redis List at `queue:{name}`
- Processing tasks: Redis List at `queue:{name}:processing`
- Delayed tasks: Sorted Set at `queue:{name}:delayed`

**Use cases:** Production apps, microservices, distributed systems, high-throughput scenarios

---

### PostgreSQL Driver

**Best for:** Enterprise applications, existing PostgreSQL infrastructure, ACID guarantees

**Features:**

- ACID guarantees with transactional dequeue
- `SELECT ... FOR UPDATE SKIP LOCKED` for concurrent workers
- Dead-letter queue for permanently failed tasks
- Visibility timeout for crash recovery (locked_until timestamp)
- Connection pooling with asyncpg
- Automatic schema migrations

**Requirements:** PostgreSQL 14+ (for `SKIP LOCKED` support)

**Installation:**

```bash
# With uv
uv add "async-task[postgres]"

# With pip
pip install "async-task[postgres]"
```

**Configuration:**

```bash
# Environment variables
export ASYNC_TASK_DRIVER=postgres
export ASYNC_TASK_POSTGRES_DSN=postgresql://user:pass@localhost:5432/dbname
export ASYNC_TASK_POSTGRES_QUEUE_TABLE=task_queue
export ASYNC_TASK_POSTGRES_DEAD_LETTER_TABLE=dead_letter_queue
export ASYNC_TASK_POSTGRES_MAX_ATTEMPTS=3
export ASYNC_TASK_POSTGRES_RETRY_DELAY_SECONDS=60
export ASYNC_TASK_POSTGRES_VISIBILITY_TIMEOUT_SECONDS=300
export ASYNC_TASK_POSTGRES_MIN_POOL_SIZE=10
export ASYNC_TASK_POSTGRES_MAX_POOL_SIZE=10
```

```python
# Programmatic configuration
from async_task.config import set_global_config

set_global_config(
    driver='postgres',
    postgres_dsn='postgresql://user:pass@localhost:5432/dbname',
    postgres_queue_table='task_queue',
    postgres_dead_letter_table='dead_letter_queue',
    postgres_max_attempts=3,
    postgres_retry_delay_seconds=60,
    postgres_visibility_timeout_seconds=300,
    postgres_min_pool_size=10,
    postgres_max_pool_size=10
)
```

**Schema Setup:**

```bash
# Initialize database schema (creates queue and dead-letter tables)
python -m async_task migrate --driver postgres --postgres-dsn postgresql://user:pass@localhost/dbname

# Or with uv
uv run python -m async_task migrate --driver postgres --postgres-dsn postgresql://user:pass@localhost/dbname
```

**Use cases:** Enterprise apps, existing PostgreSQL infrastructure, need for ACID guarantees, complex failure handling

---

### MySQL Driver

**Best for:** Enterprise applications, existing MySQL infrastructure, ACID guarantees

**Features:**

- ACID guarantees with transactional dequeue
- `SELECT ... FOR UPDATE SKIP LOCKED` for concurrent workers
- Dead-letter queue for permanently failed tasks
- Visibility timeout for crash recovery
- Connection pooling with asyncmy
- InnoDB row-level locking

**Requirements:** MySQL 8.0+ (for `SKIP LOCKED` support)

**Installation:**

```bash
# With uv
uv add "async-task[mysql]"

# With pip
pip install "async-task[mysql]"
```

**Configuration:**

```bash
# Environment variables
export ASYNC_TASK_DRIVER=mysql
export ASYNC_TASK_MYSQL_DSN=mysql://user:pass@localhost:3306/dbname
export ASYNC_TASK_MYSQL_QUEUE_TABLE=task_queue
export ASYNC_TASK_MYSQL_DEAD_LETTER_TABLE=dead_letter_queue
export ASYNC_TASK_MYSQL_MAX_ATTEMPTS=3
export ASYNC_TASK_MYSQL_RETRY_DELAY_SECONDS=60
export ASYNC_TASK_MYSQL_VISIBILITY_TIMEOUT_SECONDS=300
export ASYNC_TASK_MYSQL_MIN_POOL_SIZE=10
export ASYNC_TASK_MYSQL_MAX_POOL_SIZE=10
```

```python
# Programmatic configuration
from async_task.config import set_global_config

set_global_config(
    driver='mysql',
    mysql_dsn='mysql://user:pass@localhost:3306/dbname',
    mysql_queue_table='task_queue',
    mysql_dead_letter_table='dead_letter_queue',
    mysql_max_attempts=3,
    mysql_retry_delay_seconds=60,
    mysql_visibility_timeout_seconds=300,
    mysql_min_pool_size=10,
    mysql_max_pool_size=10
)
```

**Schema Setup:**

```bash
# Initialize database schema
python -m async_task migrate --driver mysql --mysql-dsn mysql://user:pass@localhost:3306/dbname

# Or with uv
uv run python -m async_task migrate --driver mysql --mysql-dsn mysql://user:pass@localhost:3306/dbname
```

**Use cases:** Enterprise apps, existing MySQL infrastructure, need for ACID guarantees, complex failure handling

---

### AWS SQS Driver

**Best for:** AWS-based applications, serverless, zero infrastructure management

**Features:**

- Fully managed service (no infrastructure to maintain)
- Auto-scaling based on queue depth
- Native delayed messages (up to 15 minutes)
- Message visibility timeout
- Built-in dead-letter queue support
- Multi-region support

**Requirements:** AWS account with SQS access

**Installation:**

```bash
# With uv
uv add "async-task[sqs]"

# With pip
pip install "async-task[sqs]"
```

**Configuration:**

```bash
# Environment variables
export ASYNC_TASK_DRIVER=sqs
export ASYNC_TASK_SQS_REGION=us-east-1
export ASYNC_TASK_SQS_QUEUE_PREFIX=https://sqs.us-east-1.amazonaws.com/123456789/
export AWS_ACCESS_KEY_ID=your_access_key
export AWS_SECRET_ACCESS_KEY=your_secret_key
```

```python
# Programmatic configuration
from async_task.config import set_global_config

set_global_config(
    driver='sqs',
    sqs_region='us-east-1',
    sqs_queue_url_prefix='https://sqs.us-east-1.amazonaws.com/123456789/',
    aws_access_key_id='your_access_key',     # Optional (uses AWS credentials chain)
    aws_secret_access_key='your_secret_key'  # Optional
)
```

**Queue URLs:** Constructed as `{queue_url_prefix}{queue_name}`

**Limitations:**

- Maximum delay: 15 minutes (use EventBridge Scheduler or Step Functions for longer delays)
- Approximate queue counts (not exact like databases)
- Base64 encoding overhead (SQS requires UTF-8 text)

**Use cases:** AWS/serverless apps, multi-region deployments, zero infrastructure management

---

### Driver Comparison

| Driver         | Best For       | Pros                                          | Cons                           | Requirements   |
| -------------- | -------------- | --------------------------------------------- | ------------------------------ | -------------- |
| **Memory**     | Dev/Testing    | Fast, no setup, no dependencies               | Data lost on restart           | None           |
| **Redis**      | Production     | Fast, reliable, distributed, mature           | Requires Redis server          | Redis 6.2+     |
| **PostgreSQL** | Enterprise     | ACID, DLQ, visibility timeout, transactions   | Requires PostgreSQL setup      | PostgreSQL 14+ |
| **MySQL**      | Enterprise     | ACID, DLQ, visibility timeout, transactions   | Requires MySQL setup           | MySQL 8.0+     |
| **SQS**        | AWS/Serverless | Managed, auto-scaling, zero ops, multi-region | AWS-specific, cost per message | AWS account    |

**Recommendation:**

- **Development:** Use `memory` driver
- **Production (general):** Use `redis` for most applications
- **Production (enterprise):** Use `postgres` or `mysql` if you need ACID guarantees
- **AWS/Cloud-native:** Use `sqs` for managed infrastructure

---

## ORM Integrations

Async Task automatically handles ORM model serialization and deserialization, reducing queue payload size and ensuring fresh data.

### How It Works

**Serialization (Dispatch):**

1. ORM models detected during task serialization
2. Converted to lightweight references: `{"__orm:sqlalchemy__": primary_key, "__orm_class__": "app.models.User"}`
3. Only PK stored in queue (90%+ payload reduction)

**Deserialization (Execution):**

1. ORM references detected during task deserialization
2. Models automatically fetched from database using PK
3. Fresh data ensures consistency
4. Multiple models fetched in parallel with `asyncio.gather()`

---

### SQLAlchemy

**Supports:** Both async and sync SQLAlchemy sessions

**Installation:**

```bash
# With uv
uv add "async-task[sqlalchemy]"

# With pip
pip install "async-task[sqlalchemy]"
```

**Requirements:**

- SQLAlchemy >= 2.0.44
- greenlet >= 3.2.4

**Configuration:**

```python
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from async_task.core.task import task
from async_task.serializers.orm_handler import set_sqlalchemy_session_factory

# Define your models
class Base(DeclarativeBase):
    pass

class User(Base):
    __tablename__ = 'users'
    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str]
    name: Mapped[str]

# Setup async engine
engine = create_async_engine('postgresql+asyncpg://user:pass@localhost/db')
async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

# Configure session factory for ORM handler
def get_session():
    return async_session()

set_sqlalchemy_session_factory(get_session)

# Define task with ORM model parameter
@task(queue='users')
async def send_welcome_email(user: User):
    # User model automatically serialized as reference on dispatch
    # and fetched from database when task executes
    print(f"Sending welcome email to {user.email}")
    # User data is fresh from database

# Dispatch task
async def main():
    async with async_session() as session:
        user = await session.get(User, 1)
        # Only user.id is serialized to queue
        await send_welcome_email.dispatch(user=user)
```

**Supports:**

- Composite primary keys
- Both async (`AsyncSession`) and sync (`Session`) sessions
- Auto-detection of SQLAlchemy models via mapper inspection

---

### Django ORM

**Supports:** Both async and sync Django ORM operations

**Installation:**

```bash
# With uv
uv add "async-task[django]"

# With pip
pip install "async-task[django]"
```

**Requirements:**

- Django >= 5.2.8 (for full async support)
- psycopg2-binary >= 2.9.11

**Configuration:**

```python
from django.db import models
from async_task.core.task import task

# Define your Django model
class User(models.Model):
    email = models.EmailField()
    name = models.CharField(max_length=100)

# Define task with Django model parameter
@task(queue='users')
async def send_welcome_email(user: User):
    # Django model automatically serialized as reference
    print(f"Sending welcome email to {user.email}")

# Dispatch task
async def main():
    user = await User.objects.aget(id=1)  # Django 3.1+ async support
    await send_welcome_email.dispatch(user=user)
```

**Supports:**

- Django 3.1+ async methods (`aget`, `acreate`, etc.)
- Fallback to sync with executor for older Django versions
- Uses `pk` property for primary key access

---

### Tortoise ORM

**Supports:** Fully async Tortoise ORM

**Installation:**

```bash
# With uv
uv add "async-task[tortoise]"

# With pip
pip install "async-task[tortoise]"
```

**Requirements:**

- tortoise-orm >= 0.25.1

**Configuration:**

```python
from tortoise import fields
from tortoise.models import Model
from async_task.core.task import task

# Define your Tortoise model
class User(Model):
    id = fields.IntField(pk=True)
    email = fields.CharField(max_length=255)
    name = fields.CharField(max_length=100)

# Define task with Tortoise model parameter
@task(queue='users')
async def send_welcome_email(user: User):
    # Tortoise model automatically serialized as reference
    print(f"Sending welcome email to {user.email}")

# Dispatch task
async def main():
    await Tortoise.init(
        db_url='postgres://user:pass@localhost/db',
        modules={'models': ['app.models']}
    )
    user = await User.get(id=1)
    await send_welcome_email.dispatch(user=user)
```

**Supports:**

- Full async operations
- Uses `pk` property for primary key access
- Native Tortoise async methods

---

### Custom Type Support

In addition to ORM models, msgpack serializer handles these Python types automatically:

- `datetime` → ISO format string
- `date` → ISO format string
- `Decimal` → String representation
- `UUID` → String representation
- `set` → List (converted back to set on deserialization)
- `bytes` → Binary msgpack encoding (efficient)

**Example:**

```python
from datetime import datetime
from decimal import Decimal
from uuid import UUID

@task
async def process_order(
    order_id: UUID,
    created_at: datetime,
    amount: Decimal,
    tags: set[str]
):
    # All types automatically serialized and deserialized
    print(f"Processing order {order_id} for ${amount}")
```

---

## Framework Integrations

### FastAPI Integration

Async Task provides seamless FastAPI integration with automatic lifecycle management and dependency injection.

**Installation:**

```bash
# With uv
uv add "async-task[fastapi]"

# With pip
pip install "async-task[fastapi]"
```

**Requirements:**

- fastapi >= 0.115.0

**Basic Setup:**

```python
from fastapi import FastAPI, Depends
from async_task.integrations.fastapi import AsyncTaskIntegration
from async_task.core.task import task
from async_task.core.dispatcher import Dispatcher
from async_task.drivers.base_driver import BaseDriver

# Auto-configure from environment variables
# ASYNC_TASK_DRIVER=redis
# ASYNC_TASK_REDIS_URL=redis://localhost:6379
async_task = AsyncTaskIntegration()

# Create FastAPI app with async_task lifespan
app = FastAPI(lifespan=async_task.lifespan)

# Define a task
@task(queue='emails')
async def send_email(to: str, subject: str, body: str):
    print(f"Sending email to {to}: {subject}")
    return f"Email sent to {to}"

# Use in endpoint
@app.post("/send-email")
async def send_email_route(to: str, subject: str, body: str):
    task_id = await send_email.dispatch(to=to, subject=subject, body=body)
    return {"task_id": task_id, "status": "queued"}
```

**Explicit Configuration:**

```python
from async_task.config import Config

config = Config(
    driver="redis",
    redis_url="redis://localhost:6379",
    redis_db=1
)
async_task = AsyncTaskIntegration(config=config)
app = FastAPI(lifespan=async_task.lifespan)
```

**Dependency Injection:**

```python
@app.post("/dispatch-task")
async def dispatch_task(
    dispatcher: Dispatcher = Depends(async_task.get_dispatcher)
):
    # Use dispatcher directly
    task_id = await dispatcher.dispatch(my_task)
    return {"task_id": task_id}

@app.get("/queue-stats")
async def get_stats(
    driver: BaseDriver = Depends(async_task.get_driver)
):
    # Access driver for queue inspection
    size = await driver.get_queue_size("default")
    return {"queue": "default", "size": size}
```

**Custom Driver Instance:**

```python
from async_task.drivers.redis_driver import RedisDriver

# Use pre-configured driver
custom_driver = RedisDriver(url='redis://cache-server:6379', db=2)
async_task = AsyncTaskIntegration(driver=custom_driver)
app = FastAPI(lifespan=async_task.lifespan)
```

**Important Notes:**

- FastAPI integration handles **task dispatching only**
- **Workers must run separately** to process tasks
- Two processes required:
  - **Terminal 1:** FastAPI app (dispatch tasks)
  - **Terminal 2:** Worker (process tasks)

**Example Deployment:**

```bash
# Terminal 1: Start FastAPI app
uvicorn app:app --host 0.0.0.0 --port 8000

# Terminal 2: Start worker
python -m async_task worker \
    --driver redis \
    --redis-url redis://localhost:6379 \
    --queues default,emails \
    --concurrency 10
```

**Features:**

- Automatic driver connection on startup
- Graceful driver disconnection on shutdown
- Zero-configuration with environment variables
- Dependency injection for dispatcher and driver access
- Works with all drivers (Memory, Redis, PostgreSQL, MySQL, SQS)

---

## Task Definitions

Async Task supports two task definition styles: **function-based** (simple, inline) and **class-based** (reusable, testable).

### Function-Based Tasks

Use the `@task` decorator for simple, inline task definitions.

**Basic Function Task:**

```python
from async_task.core.task import task

@task
async def send_email(to: str, subject: str, body: str):
    print(f"Sending email to {to}: {subject}")
    await asyncio.sleep(1)  # Simulate email sending
    return f"Email sent to {to}"

# Dispatch
task_id = await send_email.dispatch(
    to="user@example.com",
    subject="Welcome!",
    body="Welcome to our platform!"
)
```

**With Configuration:**

```python
@task(queue='emails', max_retries=5, retry_delay=120, timeout=30)
async def send_welcome_email(user_id: int):
    # Task automatically retries up to 5 times with 120s delay
    # Timeout after 30 seconds
    print(f"Sending welcome email to user {user_id}")
```

**Synchronous Tasks:**

For blocking I/O or CPU-intensive work:

```python
@task(queue='reports')
def generate_report(report_id: int):
    # Synchronous function runs in thread pool
    import time
    time.sleep(5)  # Blocking operation OK
    return f"Report {report_id} generated"
```

**Dispatching Function Tasks:**

```python
# Method 1: Direct dispatch
task_id = await send_email.dispatch(to="user@example.com", subject="Hello", body="Hi!")

# Method 2: With delay (execute after 60 seconds)
task_id = await send_email.dispatch(to="user@example.com", subject="Hello", body="Hi!", delay=60)

# Method 3: Method chaining
task_id = await send_email(to="user@example.com", subject="Hello", body="Hi!").delay(60).dispatch()
```

---

### Class-Based Tasks

Use the `Task` base class for complex tasks with lifecycle hooks and custom retry logic.

**Basic Class Task:**

```python
from async_task.core.task import Task

class ProcessPayment(Task[bool]):
    queue = "payments"
    max_retries = 3
    retry_delay = 60
    timeout = 30

    def __init__(self, user_id: int, amount: float, **kwargs):
        super().__init__(**kwargs)
        self.user_id = user_id
        self.amount = amount

    async def handle(self) -> bool:
        # Your payment processing logic
        print(f"Processing ${self.amount} for user {self.user_id}")
        await asyncio.sleep(2)
        return True
```

**With Lifecycle Hooks:**

```python
class ProcessPayment(Task[bool]):
    queue = "payments"
    max_retries = 3
    retry_delay = 60

    def __init__(self, user_id: int, amount: float, **kwargs):
        super().__init__(**kwargs)
        self.user_id = user_id
        self.amount = amount

    async def handle(self) -> bool:
        # Main task logic
        print(f"Processing ${self.amount} for user {self.user_id}")
        await self._charge_card()
        await self._send_receipt()
        return True

    async def failed(self, exception: Exception) -> None:
        # Called when task fails after all retries
        print(f"Payment failed for user {self.user_id}: {exception}")
        await self._refund_user()
        await self._notify_admin(exception)

    def should_retry(self, exception: Exception) -> bool:
        # Custom retry logic
        if isinstance(exception, ValueError):
            # Don't retry validation errors
            return False
        if isinstance(exception, ConnectionError):
            # Always retry network errors
            return True
        return True  # Default: retry

    async def _charge_card(self):
        # Private helper methods
        pass

    async def _send_receipt(self):
        pass

    async def _refund_user(self):
        pass

    async def _notify_admin(self, exception: Exception):
        pass
```

**Dispatching Class Tasks:**

```python
# Method 1: Immediate dispatch
task_id = await ProcessPayment(user_id=123, amount=99.99).dispatch()

# Method 2: With delay
task_id = await ProcessPayment(user_id=123, amount=99.99).delay(60).dispatch()

# Method 3: Method chaining
task_id = await ProcessPayment(user_id=123, amount=99.99) \
    .on_queue("high-priority") \
    .delay(60) \
    .retry_after(120) \
    .dispatch()
```

**Synchronous Class Tasks:**

```python
from async_task.core.task import SyncTask

class GenerateReport(SyncTask[str]):
    queue = "reports"
    timeout = 300  # 5 minutes

    def __init__(self, report_id: int, **kwargs):
        super().__init__(**kwargs)
        self.report_id = report_id

    def handle_sync(self) -> str:
        # Synchronous handle method (runs in thread pool)
        import time
        time.sleep(5)  # Blocking operation OK
        return f"Report {self.report_id} generated"
```

---

### Task Configuration Options

**Available Configuration:**

| Option        | Type          | Default     | Description                                 |
| ------------- | ------------- | ----------- | ------------------------------------------- |
| `queue`       | `str`         | `"default"` | Queue name for task                         |
| `max_retries` | `int`         | `3`         | Maximum retry attempts                      |
| `retry_delay` | `int`         | `60`        | Seconds to wait between retries             |
| `timeout`     | `int \| None` | `None`      | Task timeout in seconds (None = no timeout) |

**Configuration Methods:**

```python
# 1. Decorator configuration (function tasks)
@task(queue='emails', max_retries=5, retry_delay=120, timeout=30)
async def send_email(to: str, subject: str):
    pass

# 2. Class attributes (class tasks)
class ProcessPayment(Task[bool]):
    queue = "payments"
    max_retries = 3
    retry_delay = 60
    timeout = 30

# 3. Method chaining (runtime configuration)
await task_instance.on_queue("high").retry_after(120).delay(60).dispatch()

# 4. Dispatch parameters
await send_email.dispatch(to="user@example.com", subject="Hello", delay=60)
```

**Task Metadata:**

Tasks automatically track metadata:

- `_task_id`: UUID string for task identification
- `_attempts`: Current retry attempt count (0-indexed)
- `_dispatched_at`: ISO format datetime when task was first queued

Access metadata in task methods:

```python
class MyTask(Task[None]):
    async def handle(self) -> None:
        print(f"Task ID: {self._task_id}")
        print(f"Attempt: {self._attempts}")
        print(f"Dispatched at: {self._dispatched_at}")
```

---

## Running Workers

Workers continuously poll queues and execute tasks. Run workers via CLI (recommended) or programmatically.

### CLI Workers (Recommended)

**Basic Usage:**

```bash
# Start worker with default settings
python -m async_task worker

# Or with uv
uv run python -m async_task worker
```

**With Driver Configuration:**

```bash
# Redis worker
python -m async_task worker \
    --driver redis \
    --redis-url redis://localhost:6379 \
    --redis-password secret \
    --redis-db 1

# PostgreSQL worker
python -m async_task worker \
    --driver postgres \
    --postgres-dsn postgresql://user:pass@localhost/dbname \
    --queues default,emails \
    --concurrency 10

# MySQL worker
python -m async_task worker \
    --driver mysql \
    --mysql-dsn mysql://user:pass@localhost:3306/dbname \
    --queues default,emails \
    --concurrency 10

# AWS SQS worker
python -m async_task worker \
    --driver sqs \
    --sqs-region us-west-2 \
    --sqs-queue-url-prefix https://sqs.us-west-2.amazonaws.com/123456789/ \
    --queues default,emails
```

**Multiple Queues with Priority:**

```bash
# Process queues in priority order: high → default → low
python -m async_task worker --queues high,default,low --concurrency 20
```

**Environment Variables:**

```bash
# Set environment variables
export ASYNC_TASK_DRIVER=redis
export ASYNC_TASK_REDIS_URL=redis://localhost:6379

# Start worker (reads from env vars)
python -m async_task worker
```

**Worker Options:**

| Option          | Description                                    | Default   |
| --------------- | ---------------------------------------------- | --------- |
| `--driver`      | Queue driver (redis/postgres/mysql/sqs/memory) | `redis`   |
| `--queues`      | Comma-separated queue names (priority order)   | `default` |
| `--concurrency` | Max concurrent tasks                           | `10`      |

**Driver-Specific Options:**

See [Configuration](#configuration) section for complete list of driver-specific CLI options.

---

### Programmatic Workers

For custom worker implementations or embedding workers in applications:

```python
import asyncio
from async_task.config import Config
from async_task.core.driver_factory import DriverFactory
from async_task.core.worker import Worker

async def main():
    # Create configuration
    config = Config.from_env(driver='redis', redis_url='redis://localhost:6379')

    # Create driver and connect
    driver = DriverFactory.create_from_config(config)
    await driver.connect()

    try:
        # Create and start worker
        worker = Worker(
            queue_driver=driver,
            queues=['high-priority', 'default', 'low-priority'],
            concurrency=10
        )

        # Start worker (blocks until SIGTERM/SIGINT)
        await worker.start()
    finally:
        # Cleanup
        await driver.disconnect()

if __name__ == "__main__":
    asyncio.run(main())
```

**Worker Parameters:**

| Parameter      | Type             | Description                                    |
| -------------- | ---------------- | ---------------------------------------------- |
| `queue_driver` | `BaseDriver`     | Queue driver instance                          |
| `queues`       | `list[str]`      | Queue names to process (priority order)        |
| `concurrency`  | `int`            | Maximum concurrent tasks                       |
| `max_tasks`    | `int \| None`    | Process N tasks then exit (None = run forever) |
| `serializer`   | `BaseSerializer` | Custom serializer (default: MsgpackSerializer) |

**Worker Behavior:**

1. **Polling Loop:** Continuously checks queues until stopped
2. **Round-Robin:** Processes queues in priority order (first = highest priority)
3. **Concurrency Control:** Tracks active tasks, respects concurrency limit
4. **Fair Distribution:** Polls all queues before repeating first queue
5. **Sleep on Empty:** 100ms sleep when no tasks available (prevents CPU spinning)
6. **Graceful Shutdown:** SIGTERM/SIGINT wait for in-flight tasks to complete

**Testing/Batch Mode:**

```python
# Process exactly 10 tasks then exit
worker = Worker(
    queue_driver=driver,
    queues=['default'],
    concurrency=5,
    max_tasks=10  # Exit after 10 tasks
)
await worker.start()
```

---

### Multiple Workers for Different Queues

Run multiple worker processes for different queue priorities:

```bash
# Terminal 1: High-priority queue with high concurrency
python -m async_task worker --queues high-priority --concurrency 20

# Terminal 2: Default queue with moderate concurrency
python -m async_task worker --queues default --concurrency 10

# Terminal 3: Low-priority and batch jobs with low concurrency
python -m async_task worker --queues low-priority,batch --concurrency 5
```

**Benefits:**

- Isolate critical tasks from low-priority work
- Prevent slow tasks from blocking fast tasks
- Scale different queues independently
- Dedicate resources based on queue importance

---

### Graceful Shutdown

Workers handle `SIGTERM` and `SIGINT` signals for clean shutdown:

**Shutdown Process:**

1. **Stop accepting new tasks** – No new tasks dequeued from driver
2. **Wait for completion** – Currently processing tasks finish naturally
3. **Disconnect** – Driver connections closed cleanly
4. **Exit** – Process terminates gracefully

**Trigger Shutdown:**

```bash
# Send SIGTERM for graceful shutdown
kill -TERM <worker_pid>

# Or use Ctrl+C for SIGINT (same behavior)
```

**Production Deployment:**

Use process managers that send SIGTERM for clean shutdowns:

- **systemd:** Sends SIGTERM by default
- **supervisor:** Configure `stopasgroup=true`
- **Kubernetes:** Sends SIGTERM before SIGKILL (grace period)
- **Docker:** `docker stop` sends SIGTERM

**Example systemd service:**

```ini
[Unit]
Description=Async Task Worker
After=network.target

[Service]
Type=simple
User=www-data
WorkingDirectory=/app
ExecStart=/usr/bin/python -m async_task worker --driver redis --queues default
Restart=always
KillSignal=SIGTERM
TimeoutStopSec=30

[Install]
WantedBy=multi-user.target
```

---

## Configuration

Async Task supports three configuration methods with clear precedence rules.

### Configuration Precedence (highest to lowest)

1. **Keyword arguments** to `set_global_config()` or `Config.from_env()`
2. **Environment variables**
3. **Default values**

---

### Method 1: Environment Variables (Recommended for Production)

**General Configuration:**

```bash
export ASYNC_TASK_DRIVER=redis              # Driver: memory, redis, postgres, mysql, sqs
export ASYNC_TASK_DEFAULT_QUEUE=default     # Default queue name
export ASYNC_TASK_MAX_RETRIES=3             # Default max retry attempts
export ASYNC_TASK_RETRY_DELAY=60            # Default retry delay (seconds)
export ASYNC_TASK_TIMEOUT=300               # Default task timeout (seconds, None = no timeout)
```

**Redis Configuration:**

```bash
export ASYNC_TASK_REDIS_URL=redis://localhost:6379
export ASYNC_TASK_REDIS_PASSWORD=secret
export ASYNC_TASK_REDIS_DB=0
export ASYNC_TASK_REDIS_MAX_CONNECTIONS=10
```

**PostgreSQL Configuration:**

```bash
export ASYNC_TASK_POSTGRES_DSN=postgresql://user:pass@localhost:5432/dbname
export ASYNC_TASK_POSTGRES_QUEUE_TABLE=task_queue
export ASYNC_TASK_POSTGRES_DEAD_LETTER_TABLE=dead_letter_queue
export ASYNC_TASK_POSTGRES_MAX_ATTEMPTS=3
export ASYNC_TASK_POSTGRES_RETRY_DELAY_SECONDS=60
export ASYNC_TASK_POSTGRES_VISIBILITY_TIMEOUT_SECONDS=300
export ASYNC_TASK_POSTGRES_MIN_POOL_SIZE=10
export ASYNC_TASK_POSTGRES_MAX_POOL_SIZE=10
```

**MySQL Configuration:**

```bash
export ASYNC_TASK_MYSQL_DSN=mysql://user:pass@localhost:3306/dbname
export ASYNC_TASK_MYSQL_QUEUE_TABLE=task_queue
export ASYNC_TASK_MYSQL_DEAD_LETTER_TABLE=dead_letter_queue
export ASYNC_TASK_MYSQL_MAX_ATTEMPTS=3
export ASYNC_TASK_MYSQL_RETRY_DELAY_SECONDS=60
export ASYNC_TASK_MYSQL_VISIBILITY_TIMEOUT_SECONDS=300
export ASYNC_TASK_MYSQL_MIN_POOL_SIZE=10
export ASYNC_TASK_MYSQL_MAX_POOL_SIZE=10
```

**AWS SQS Configuration:**

```bash
export ASYNC_TASK_SQS_REGION=us-east-1
export ASYNC_TASK_SQS_QUEUE_PREFIX=https://sqs.us-east-1.amazonaws.com/123456789/
export AWS_ACCESS_KEY_ID=your_access_key
export AWS_SECRET_ACCESS_KEY=your_secret_key
```

---

### Method 2: Programmatic Configuration

**Using `set_global_config()`:**

```python
from async_task.config import set_global_config

# Basic Redis configuration
set_global_config(
    driver='redis',
    redis_url='redis://localhost:6379',
    default_queue='default',
    default_max_retries=3
)

# PostgreSQL with custom settings
set_global_config(
    driver='postgres',
    postgres_dsn='postgresql://user:pass@localhost:5432/mydb',
    postgres_queue_table='my_queue',
    postgres_max_attempts=5,
    postgres_min_pool_size=5,
    postgres_max_pool_size=20
)

# MySQL with custom settings
set_global_config(
    driver='mysql',
    mysql_dsn='mysql://user:pass@localhost:3306/mydb',
    mysql_queue_table='my_queue',
    mysql_max_attempts=5,
    mysql_min_pool_size=5,
    mysql_max_pool_size=20
)

# SQS configuration
set_global_config(
    driver='sqs',
    sqs_region='us-west-2',
    sqs_queue_url_prefix='https://sqs.us-west-2.amazonaws.com/123456789/',
    aws_access_key_id='your_key',
    aws_secret_access_key='your_secret'
)
```

**Using `Config.from_env()` with Overrides:**

```python
from async_task.config import Config

# Create config from environment variables with overrides
config = Config.from_env(
    driver='redis',
    redis_url='redis://localhost:6379',
    default_max_retries=5
)
```

---

### Method 3: CLI Arguments

CLI arguments override both environment variables and programmatic configuration:

```bash
python -m async_task worker \
    --driver redis \
    --redis-url redis://localhost:6379 \
    --redis-password secret \
    --queues high,default,low \
    --concurrency 20
```

---

### Complete Configuration Reference

**General Options:**

| Option                | Env Var                    | Default   | Description                    |
| --------------------- | -------------------------- | --------- | ------------------------------ |
| `driver`              | `ASYNC_TASK_DRIVER`        | `redis`   | Queue driver                   |
| `default_queue`       | `ASYNC_TASK_DEFAULT_QUEUE` | `default` | Default queue name             |
| `default_max_retries` | `ASYNC_TASK_MAX_RETRIES`   | `3`       | Default max retry attempts     |
| `default_retry_delay` | `ASYNC_TASK_RETRY_DELAY`   | `60`      | Default retry delay (seconds)  |
| `default_timeout`     | `ASYNC_TASK_TIMEOUT`       | `None`    | Default task timeout (seconds) |

**Redis Options:**

| Option                  | Env Var                            | Default                  | Description                  |
| ----------------------- | ---------------------------------- | ------------------------ | ---------------------------- |
| `redis_url`             | `ASYNC_TASK_REDIS_URL`             | `redis://localhost:6379` | Redis connection URL         |
| `redis_password`        | `ASYNC_TASK_REDIS_PASSWORD`        | `None`                   | Redis password               |
| `redis_db`              | `ASYNC_TASK_REDIS_DB`              | `0`                      | Redis database number (0-15) |
| `redis_max_connections` | `ASYNC_TASK_REDIS_MAX_CONNECTIONS` | `10`                     | Redis connection pool size   |

**PostgreSQL Options:**

| Option                                | Env Var                                          | Default                                         | Description                  |
| ------------------------------------- | ------------------------------------------------ | ----------------------------------------------- | ---------------------------- |
| `postgres_dsn`                        | `ASYNC_TASK_POSTGRES_DSN`                        | `postgresql://test:test@localhost:5432/test_db` | PostgreSQL connection string |
| `postgres_queue_table`                | `ASYNC_TASK_POSTGRES_QUEUE_TABLE`                | `task_queue`                                    | Queue table name             |
| `postgres_dead_letter_table`          | `ASYNC_TASK_POSTGRES_DEAD_LETTER_TABLE`          | `dead_letter_queue`                             | Dead letter table name       |
| `postgres_max_attempts`               | `ASYNC_TASK_POSTGRES_MAX_ATTEMPTS`               | `3`                                             | Max attempts before DLQ      |
| `postgres_retry_delay_seconds`        | `ASYNC_TASK_POSTGRES_RETRY_DELAY_SECONDS`        | `60`                                            | Retry delay (seconds)        |
| `postgres_visibility_timeout_seconds` | `ASYNC_TASK_POSTGRES_VISIBILITY_TIMEOUT_SECONDS` | `300`                                           | Visibility timeout (seconds) |
| `postgres_min_pool_size`              | `ASYNC_TASK_POSTGRES_MIN_POOL_SIZE`              | `10`                                            | Min connection pool size     |
| `postgres_max_pool_size`              | `ASYNC_TASK_POSTGRES_MAX_POOL_SIZE`              | `10`                                            | Max connection pool size     |

**MySQL Options:**

| Option                             | Env Var                                       | Default                                    | Description                  |
| ---------------------------------- | --------------------------------------------- | ------------------------------------------ | ---------------------------- |
| `mysql_dsn`                        | `ASYNC_TASK_MYSQL_DSN`                        | `mysql://test:test@localhost:3306/test_db` | MySQL connection string      |
| `mysql_queue_table`                | `ASYNC_TASK_MYSQL_QUEUE_TABLE`                | `task_queue`                               | Queue table name             |
| `mysql_dead_letter_table`          | `ASYNC_TASK_MYSQL_DEAD_LETTER_TABLE`          | `dead_letter_queue`                        | Dead letter table name       |
| `mysql_max_attempts`               | `ASYNC_TASK_MYSQL_MAX_ATTEMPTS`               | `3`                                        | Max attempts before DLQ      |
| `mysql_retry_delay_seconds`        | `ASYNC_TASK_MYSQL_RETRY_DELAY_SECONDS`        | `60`                                       | Retry delay (seconds)        |
| `mysql_visibility_timeout_seconds` | `ASYNC_TASK_MYSQL_VISIBILITY_TIMEOUT_SECONDS` | `300`                                      | Visibility timeout (seconds) |
| `mysql_min_pool_size`              | `ASYNC_TASK_MYSQL_MIN_POOL_SIZE`              | `10`                                       | Min connection pool size     |
| `mysql_max_pool_size`              | `ASYNC_TASK_MYSQL_MAX_POOL_SIZE`              | `10`                                       | Max connection pool size     |

**AWS SQS Options:**

| Option                  | Env Var                       | Default     | Description                                          |
| ----------------------- | ----------------------------- | ----------- | ---------------------------------------------------- |
| `sqs_region`            | `ASYNC_TASK_SQS_REGION`       | `us-east-1` | AWS region                                           |
| `sqs_queue_url_prefix`  | `ASYNC_TASK_SQS_QUEUE_PREFIX` | `None`      | SQS queue URL prefix                                 |
| `aws_access_key_id`     | `AWS_ACCESS_KEY_ID`           | `None`      | AWS access key (optional, uses AWS credential chain) |
| `aws_secret_access_key` | `AWS_SECRET_ACCESS_KEY`       | `None`      | AWS secret key (optional, uses AWS credential chain) |

---

## CLI Reference

### Worker Command

Start a worker to process tasks from queues.

```bash
python -m async_task worker [OPTIONS]
```

**Options:**

| Option                          | Description                                    | Default                  |
| ------------------------------- | ---------------------------------------------- | ------------------------ |
| `--driver DRIVER`               | Queue driver (redis/postgres/mysql/sqs/memory) | `redis`                  |
| `--queues QUEUES`               | Comma-separated queue names (priority order)   | `default`                |
| `--concurrency N`               | Max concurrent tasks                           | `10`                     |
| `--redis-url URL`               | Redis connection URL                           | `redis://localhost:6379` |
| `--redis-password PASSWORD`     | Redis password                                 | `None`                   |
| `--redis-db N`                  | Redis database number (0-15)                   | `0`                      |
| `--postgres-dsn DSN`            | PostgreSQL connection DSN                      | -                        |
| `--postgres-queue-table TABLE`  | PostgreSQL queue table name                    | `task_queue`             |
| `--mysql-dsn DSN`               | MySQL connection DSN                           | -                        |
| `--mysql-queue-table TABLE`     | MySQL queue table name                         | `task_queue`             |
| `--sqs-region REGION`           | AWS SQS region                                 | `us-east-1`              |
| `--sqs-queue-url-prefix PREFIX` | SQS queue URL prefix                           | -                        |

**Examples:**

```bash
# Basic usage
python -m async_task worker

# Multiple queues with priority
python -m async_task worker --queues high,default,low --concurrency 20

# Redis with auth
python -m async_task worker \
    --driver redis \
    --redis-url redis://localhost:6379 \
    --redis-password secret

# PostgreSQL worker
python -m async_task worker \
    --driver postgres \
    --postgres-dsn postgresql://user:pass@localhost/db

# MySQL worker
python -m async_task worker \
    --driver mysql \
    --mysql-dsn mysql://user:pass@localhost:3306/db

# SQS worker
python -m async_task worker \
    --driver sqs \
    --sqs-region us-west-2
```

---

### Migrate Command

Initialize database schema for PostgreSQL or MySQL drivers.

```bash
python -m async_task migrate [OPTIONS]
```

**Options:**

| Option                               | Description                | Default             |
| ------------------------------------ | -------------------------- | ------------------- |
| `--driver DRIVER`                    | Driver (postgres or mysql) | `postgres`          |
| `--postgres-dsn DSN`                 | PostgreSQL connection DSN  | -                   |
| `--postgres-queue-table TABLE`       | Queue table name           | `task_queue`        |
| `--postgres-dead-letter-table TABLE` | Dead letter table name     | `dead_letter_queue` |
| `--mysql-dsn DSN`                    | MySQL connection DSN       | -                   |
| `--mysql-queue-table TABLE`          | Queue table name           | `task_queue`        |
| `--mysql-dead-letter-table TABLE`    | Dead letter table name     | `dead_letter_queue` |

**Examples:**

```bash
# PostgreSQL migration (default)
python -m async_task migrate \
    --postgres-dsn postgresql://user:pass@localhost/db

# PostgreSQL with custom tables
python -m async_task migrate \
    --postgres-dsn postgresql://user:pass@localhost/db \
    --postgres-queue-table my_queue \
    --postgres-dead-letter-table my_dlq

# MySQL migration
python -m async_task migrate \
    --driver mysql \
    --mysql-dsn mysql://user:pass@localhost:3306/db

# Using environment variables
export ASYNC_TASK_POSTGRES_DSN=postgresql://user:pass@localhost/db
python -m async_task migrate
```

**What it does:**

- Creates queue table with optimized indexes
- Creates dead-letter table for failed tasks
- Idempotent (safe to run multiple times)
- Only works with PostgreSQL and MySQL drivers

---

## Comparison with Alternatives

### Async Task vs. Celery

| Feature                 | Async Task                                         | Celery                              |
| ----------------------- | -------------------------------------------------- | ----------------------------------- |
| **Async Support**       | ✅ Async-first, built with asyncio                 | ❌ No native asyncio support        |
| **Type Safety**         | ✅ Full type hints, Generic[T]                     | ⚠️ Third-party stubs (celery-types) |
| **Multi-Driver**        | ✅ 5 drivers (Memory/Redis/PG/MySQL/SQS)           | ⚠️ Redis/RabbitMQ/SQS brokers       |
| **ORM Integration**     | ✅ Auto-serialization (SQLAlchemy/Django/Tortoise) | ❌ Manual serialization             |
| **Serialization**       | ✅ msgpack (fast, binary)                          | ⚠️ JSON/pickle (slower)             |
| **FastAPI Integration** | ✅ First-class, lifespan management                | ⚠️ Manual setup                     |
| **Dead-Letter Queue**   | ✅ Built-in (PG/MySQL)                             | ⚠️ Manual setup (RabbitMQ DLX)      |
| **ACID Guarantees**     | ✅ PostgreSQL/MySQL drivers                        | ❌ Not available                    |
| **Setup Complexity**    | ✅ Zero-config with env vars                       | ⚠️ Complex configuration            |
| **Learning Curve**      | ✅ Simple, intuitive API                           | ⚠️ Steep learning curve             |

**When to use Async Task:**

- Modern async Python applications
- Need for type safety and IDE support
- Multiple driver options (dev → production)
- Automatic ORM model handling
- FastAPI applications
- Enterprise ACID requirements

**When to use Celery:**

- Mature ecosystem with many plugins
- Need for complex workflows (chains, chords)
- Large existing Celery codebase

---

### Async Task vs. Dramatiq

| Feature                 | Async Task              | Dramatiq                    |
| ----------------------- | ----------------------- | --------------------------- |
| **Async Support**       | ✅ Async-first          | ⚠️ Limited (via middleware) |
| **Type Safety**         | ✅ Full type hints      | ✅ Type hints (py.typed)    |
| **Multi-Driver**        | ✅ 5 drivers            | ⚠️ Redis/RabbitMQ           |
| **ORM Integration**     | ✅ Auto-serialization   | ❌ Manual serialization     |
| **Dead-Letter Queue**   | ✅ Built-in             | ✅ Built-in                 |
| **FastAPI Integration** | ✅ First-class          | ⚠️ Manual setup             |
| **Database Drivers**    | ✅ PostgreSQL/MySQL     | ❌ Not available            |
| **Simplicity**          | ✅ Clean, intuitive API | ✅ Simple, well-designed    |

**When to use Async Task:**

- Async applications (FastAPI, aiohttp)
- Type-safe codebase
- Database-backed queues (ACID)
- ORM model handling

**When to use Dramatiq:**

- Synchronous applications
- Need for mature, battle-tested library
- Complex middleware requirements

---

### Async Task vs. RQ (Redis Queue)

| Feature               | Async Task                        | RQ                      |
| --------------------- | --------------------------------- | ----------------------- |
| **Async Support**     | ✅ Async-first                    | ❌ Sync only            |
| **Multi-Driver**      | ✅ 5 drivers                      | ❌ Redis only           |
| **Type Safety**       | ✅ Full type hints                | ✅ Type hints added     |
| **Retries**           | ✅ Configurable with custom logic | ✅ Configurable retries |
| **Dead-Letter Queue** | ✅ Built-in                       | ❌ Not available        |
| **Database Drivers**  | ✅ PostgreSQL/MySQL               | ❌ Not available        |
| **Simplicity**        | ✅ Intuitive, clean API           | ✅ Very simple          |

**When to use Async Task:**

- Async applications
- Multiple driver options
- Enterprise features (DLQ, ACID)
- Type safety

**When to use RQ:**

- Simple use cases
- Synchronous applications
- Redis-only infrastructure

---

### Async Task vs. Huey

| Feature                 | Async Task                       | Huey              |
| ----------------------- | -------------------------------- | ----------------- |
| **Async Support**       | ✅ Async-first                   | ⚠️ Limited async  |
| **Multi-Driver**        | ✅ 5 drivers                     | ⚠️ Redis/SQLite   |
| **Type Safety**         | ✅ Full type hints               | ❌ Limited        |
| **ORM Integration**     | ✅ Auto-serialization            | ❌ Manual         |
| **Enterprise Features** | ✅ ACID, DLQ, visibility timeout | ⚠️ Basic features |
| **Simplicity**          | ✅ Clean, modern API             | ✅ Simple         |

**When to use Async Task:**

- Async-first applications
- Enterprise requirements
- Type-safe codebase
- ORM integration

**When to use Huey:**

- Lightweight use cases
- Simple task queues
- SQLite-backed queues

---

### Key Differentiators

**Async Task stands out with:**

1. **True async-first design** – Built with asyncio from the ground up
2. **msgpack serialization** – Faster and more efficient than JSON
3. **Intelligent ORM handling** – Automatic model serialization for 3 major ORMs
4. **Multi-driver flexibility** – Seamlessly switch between 5 production-ready drivers
5. **Type safety** – Full type hints with Generic[T] support
6. **Enterprise ACID guarantees** – PostgreSQL/MySQL drivers with transactional dequeue
7. **Dead-letter queues** – Built-in support for failed task inspection
8. **FastAPI integration** – First-class support with lifecycle management
9. **Elegant, expressive API** – Method chaining and intuitive task definitions
10. **Zero configuration** – Works with environment variables out of the box

---

## Best Practices

### Task Design

✅ **Do:**

- Keep tasks small and focused (single responsibility)
- Make tasks idempotent when possible (safe to run multiple times)
- Use timeouts for long-running tasks
- Implement custom `failed()` handlers for cleanup
- Use `should_retry()` for intelligent retry logic based on exception type
- Pass ORM models directly as parameters - they're automatically serialized as lightweight references and re-fetched with fresh data when the task executes (Supported ORMs: SQLAlchemy, Django ORM, Tortoise ORM)

❌ **Don't:**

- Include blocking I/O in async tasks (use sync tasks with thread pool instead)
- Share mutable state between tasks
- Perform network calls without timeouts
- Store large objects in task parameters

### Queue Organization

✅ **Do:**

- Use separate queues for different priorities (high/default/low)
- Isolate slow tasks in dedicated queues
- Group related tasks by queue (emails, reports, notifications)
- Consider worker capacity when designing queues
- Use descriptive queue names

**Example:**

```bash
# Worker 1: Critical tasks
python -m async_task worker --queues critical --concurrency 20

# Worker 2: Normal tasks
python -m async_task worker --queues default --concurrency 10

# Worker 3: Background tasks
python -m async_task worker --queues low-priority,batch --concurrency 5
```

### Error Handling

✅ **Do:**

- Log errors comprehensively in `failed()` method
- Use retry limits to prevent infinite loops
- Monitor dead-letter queues regularly
- Implement alerting for critical failures
- Add context to exception messages

```python
class ProcessPayment(Task[bool]):
    async def failed(self, exception: Exception) -> None:
        # Log with context
        logger.error(
            f"Payment failed for user {self.user_id}",
            extra={
                "task_id": self._task_id,
                "attempts": self._attempts,
                "user_id": self.user_id,
                "amount": self.amount
            },
            exc_info=exception
        )
        # Alert on critical failures
        await notify_admin(exception)
```

### Performance

✅ **Do:**

- Tune worker concurrency based on task characteristics
  - I/O-bound tasks: High concurrency (20-50)
  - CPU-bound tasks: Low concurrency (number of CPU cores)
- Use connection pooling (configured automatically)
- Monitor queue sizes and adjust worker count accordingly
- Consider task batching for high-volume operations
- Use Redis driver for production (fastest)

### Production Deployment

✅ **Do:**

- **Use Redis, PostgreSQL, or MySQL** for production (not Memory driver)
- **Configure proper retry delays** to avoid overwhelming systems during outages
- **Set up monitoring and alerting** for queue sizes, worker health, failed tasks
- **Use environment variables** for configuration (never hardcode credentials)
- **Deploy multiple workers** for high availability and load distribution
- **Use process managers** (systemd, supervisor, Kubernetes) for automatic restarts
- **Monitor dead-letter queues** to catch permanently failed tasks
- **Set appropriate timeouts** to prevent tasks from hanging indefinitely
- **Test thoroughly** with Memory driver before deploying to production

**Example Production Setup:**

```bash
# Environment variables in production
export ASYNC_TASK_DRIVER=redis
export ASYNC_TASK_REDIS_URL=redis://redis-master:6379
export ASYNC_TASK_REDIS_PASSWORD=${REDIS_PASSWORD}
export ASYNC_TASK_DEFAULT_MAX_RETRIES=5
export ASYNC_TASK_DEFAULT_RETRY_DELAY=120
export ASYNC_TASK_DEFAULT_TIMEOUT=300

# Multiple worker processes
python -m async_task worker --queues critical --concurrency 20 &
python -m async_task worker --queues default --concurrency 10 &
python -m async_task worker --queues low-priority --concurrency 5 &
```

### Monitoring

✅ **Monitor:**

- Queue sizes (alert when queues grow too large)
- Task processing rate (tasks/second)
- Worker health (process uptime, memory usage)
- Dead-letter queue size (alert on growth)
- Task execution times (p50, p95, p99)
- Retry rates (alert on high retry rates)

**Example Monitoring Script:**

```python
from async_task.config import Config
from async_task.core.driver_factory import DriverFactory

async def check_queue_health():
    config = Config.from_env()
    driver = DriverFactory.create_from_config(config)
    await driver.connect()

    try:
        for queue in ['critical', 'default', 'low-priority']:
            size = await driver.get_queue_size(queue)
            print(f"Queue '{queue}': {size} tasks")

            # Alert if queue is too large
            if size > 1000:
                await send_alert(f"Queue '{queue}' has {size} tasks")
    finally:
        await driver.disconnect()
```

---

## Contributing

Contributions are welcome! Please see [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

**Development Setup:**

```bash
# Clone repository
git clone https://github.com/adamrefaey/async-task.git
cd async-task

# Install uv
curl -LsSf https://astral.sh/uv/install.sh | sh

# Sync dependencies
uv sync

# Install pre-commit hooks
uv run pre-commit install

# Run tests
uv run pytest

# Run with coverage
uv run pytest --cov=async_task --cov-branch --cov-report=term-missing

# Code quality
uv run ruff format .
uv run ruff check .
uv run pyright
```

---

## License

MIT License – see [LICENSE](LICENSE) file for details.

---

## Credits

Built with ❤️ by [Adam Refaey](https://github.com/adamrefaey). Inspired by [Laravel's queue system](https://laravel.com/docs/queues).

---

## Support

- **Repository:** [github.com/adamrefaey/async-task](https://github.com/adamrefaey/async-task)
- **Issues:** [github.com/adamrefaey/async-task/issues](https://github.com/adamrefaey/async-task/issues)
- **Discussions:** [github.com/adamrefaey/async-task/discussions](https://github.com/adamrefaey/async-task/discussions)

---

## Roadmap

- [ ] SQLite driver support
- [ ] Oracle driver support
- [ ] Task batching support
- [ ] Task chaining and workflows
- [ ] Rate limiting
- [ ] Task priority within queues
- [ ] Web UI for monitoring
- [ ] Prometheus metrics exporter
- [ ] Additional ORM support

---

**Async Task** – Production-grade async task queues for modern Python applications.
