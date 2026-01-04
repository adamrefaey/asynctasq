# ORM Integrations

## Table of Contents

- [ORM Integrations](#orm-integrations)
  - [Table of Contents](#table-of-contents)
  - [How It Works](#how-it-works)
  - [SQLAlchemy](#sqlalchemy)
  - [Django ORM](#django-orm)
  - [Tortoise ORM](#tortoise-orm)
  - [Custom Type Support](#custom-type-support)

AsyncTasQ automatically handles ORM model serialization and deserialization, reducing queue payload size and ensuring fresh data.

## How It Works

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

## SQLAlchemy

**Supports:** Both async and sync SQLAlchemy sessions

**Installation:**

```bash
# With uv
uv add "asynctasq[sqlalchemy]"

# With pip
pip install "asynctasq[sqlalchemy]"
```

**Requirements:**

- SQLAlchemy >= 2.0.22
- greenlet >= 3.0.0

**Configuration:**

Set the session factory **once** on your Base class. All models automatically inherit it - no per-model configuration needed!

**For Development/Single Process:**

```python
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from asynctasq import task

# Define your models
class Base(DeclarativeBase):
    pass

class User(Base):
    __tablename__ = 'users'
    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str]
    name: Mapped[str]

# Setup async engine and session factory
engine = create_async_engine(
    'postgresql+asyncpg://user:pass@localhost/db',
    pool_pre_ping=True,  # Verify connections are alive
    pool_recycle=3600,   # Recycle connections after 1 hour
)
SessionFactory = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False  # Prevent lazy-load queries after commit
)

# Set session factory ONCE on Base class - all models inherit automatically!
Base._asynctasq_session_factory = SessionFactory

# Define task - no manual session management needed!
@task(queue='users')
async def send_welcome_email(user: User):
    # User model automatically serialized as reference on dispatch
```

**For Production/Workers (Multiprocessing):**

```python
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from asynctasq import task, create_worker_session_factory

# Define your models
class Base(DeclarativeBase):
    pass

class User(Base):
    __tablename__ = 'users'
    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str]
    name: Mapped[str]

# ✅ Use helper for worker processes (automatically uses NullPool)
WorkerSessionFactory = create_worker_session_factory(
    'postgresql+asyncpg://user:pass@localhost/db',
    pool_pre_ping=True,
)

Base._asynctasq_session_factory = WorkerSessionFactory

@task(queue='users')
async def send_welcome_email(user: User):
    # Safe for multiprocessing - NullPool prevents connection sharing issues

    # Workers automatically create sessions from factory to fetch the model
    print(f"Sending welcome email to {user.email}")
    # User data is fresh from database

# Dispatch task - simple and clean!
async def main():
    async with SessionFactory() as session:
        user = await session.get(User, 1)
        # Only user.id is serialized to queue
        await send_welcome_email(user=user).dispatch()
```

**Alternative: Manual configuration** (for advanced users):

```python
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.pool import NullPool

# Worker engine with NullPool - creates new connection for each checkout
# Avoids connection pool sharing across forked processes
worker_engine = create_async_engine(
    'postgresql+asyncpg://user:pass@localhost/db',
    poolclass=NullPool,      # CRITICAL for multiprocessing safety
    pool_pre_ping=True,      # Verify connections are alive
)

WorkerSessionFactory = async_sessionmaker(
    worker_engine,
    class_=AsyncSession,
    expire_on_commit=False
)
```

**Why NullPool?**
- ✅ No connection pool = no fork() issues
- ✅ Each worker safely manages its own connections
- ✅ Production-tested pattern (Celery best practice)
- ❌ Slightly higher connection overhead (acceptable for workers)

**Alternative: Dispose engine after fork** (more complex):

```python
import os
from sqlalchemy import event

# Before workers fork
@event.listens_for(worker_engine.sync_engine, "connect")
def receive_connect(dbapi_conn, connection_record):
    connection_record.info['pid'] = os.getpid()

@event.listens_for(worker_engine.sync_engine, "checkout")
def receive_checkout(dbapi_conn, connection_record, connection_proxy):
    pid = os.getpid()
    if connection_record.info['pid'] != pid:
        connection_record.dbapi_connection = connection_proxy.dbapi_connection = None
        raise Exception(
            "Connection record belongs to pid %s, attempting to check out in pid %s"
            % (connection_record.info['pid'], pid)
        )
```

**Recommendation:** Use NullPool for simplicity and safety unless you have specific performance requirements.

**Benefits:**
- ✅ **Set once, works everywhere** - Configure Base class only
- ✅ **All models inherit automatically** - No per-model registration
- ✅ **Workers handle sessions** - Automatic session lifecycle management
- ✅ **Cleaner code** - No manual session management in tasks
- ✅ **Production-ready** - Follows Celery best practices for multiprocessing

**Engine Cleanup:**

If you want AsyncTasQ to handle disposing (cleaning up) the SQLAlchemy engine for you, pass your engine to `asynctasq.init()`:

```python
from asynctasq import init, RedisConfig

# Pass your SQLAlchemy engine to AsyncTasQ for automatic cleanup
init({
    "driver": "redis",
    "redis": RedisConfig(url="redis://localhost:6379"),
    "sqlalchemy_engine": engine  # AsyncTasQ will dispose this on shutdown
})
```

This prevents connection leaks and ensures graceful shutdown of database connections.

**How It Works:**

1. **Serialization (Dispatch):** ORM models are converted to lightweight references `{"__orm:sqlalchemy__": pk, "__orm_class__": "app.models.User"}` containing only the primary key
2. **Deserialization (Execution):** Models are automatically fetched from database using the stored PK when the task executes
3. **Session Management:** Workers automatically create sessions from `Base._asynctasq_session_factory` when fetching models

**Features:**

- ✅ **Simple setup** - One line on Base class
- ✅ **Automatic inheritance** - All models get session access automatically
- ✅ **Worker-friendly** - Workers create sessions on-demand from factory
- ✅ **Fresh data** - Models fetched from database ensure consistency
- ✅ **Efficient** - 90%+ payload reduction (only PK stored)
- ✅ **Parallel fetching** - Multiple models fetched concurrently
- ✅ **Multiprocessing-safe** - NullPool option for forked workers
- ✅ **Production-ready** - Connection pool best practices included

**Supports:**

- Composite primary keys (returned as tuple)
- Both async (`AsyncSession`) and sync (`Session`) sessions
- Auto-detection of SQLAlchemy models via mapper inspection
- Parallel fetching of multiple models with `asyncio.gather()`
- Connection pool options (NullPool, QueuePool, etc.)
- Production-grade pooling settings (`pool_pre_ping`, `pool_recycle`)

**Production Deployment Checklist:**

✅ **Use NullPool for multiprocessing workers** (prevents fork() issues)
✅ **Set `pool_pre_ping=True`** (detect stale connections)
✅ **Set `pool_recycle=3600`** (recycle connections hourly)
✅ **Set `expire_on_commit=False`** (prevent lazy-load queries)
✅ **Monitor connection pool metrics** (pool size, overflow, timeouts)
✅ **Use separate engines for API vs workers** (different pool configs)
✅ **Test with multiple worker processes** (verify no connection sharing)

**Common Issues & Solutions:**

| Issue             | Symptom                               | Solution                                            |
| ----------------- | ------------------------------------- | --------------------------------------------------- |
| Protocol errors   | `sslSocket error`, `connection reset` | Use NullPool for workers                            |
| Stale connections | `connection terminated unexpectedly`  | Set `pool_pre_ping=True`                            |
| Connection leaks  | Pool exhaustion, timeouts             | Verify sessions are closed, increase `max_overflow` |
| Lazy-load errors  | `DetachedInstanceError` after commit  | Set `expire_on_commit=False`                        |
| Fork issues       | Workers inherit parent connections    | Use NullPool or dispose engine after fork           |

---

## Django ORM

**Supports:** Both async and sync Django ORM operations

**Installation:**

```bash
# With uv
uv add "asynctasq[django]"

# With pip
pip install "asynctasq[django]"
```

**Requirements:**

- Django >= 5.0 (for full async support)
- psycopg2-binary >= 2.9.9

**Configuration:**

```python
from django.db import models
from asynctasq import task

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
    user = await User.objects.aget(id=1)  # Django 4.1+ async ORM methods
    await send_welcome_email(user=user).dispatch()
```

**Supports:**

- Django 4.1+ async ORM methods (`aget`, `acreate`, etc.)
- Fallback to sync with executor for older Django versions
- Uses `pk` property for primary key access

---

## Tortoise ORM

**Supports:** Fully async Tortoise ORM with native asyncio support

**Installation:**

```bash
# With uv
uv add "asynctasq[tortoise]"

# With pip
pip install "asynctasq[tortoise]"
```

**Requirements:**

- tortoise-orm >= 0.21.0
- asyncpg or aiomysql (depending on your database)

**Key Features:**

- ✅ **Native async** - Built on asyncio from the ground up
- ✅ **Automatic serialization** - Models converted to lightweight references (PK only)
- ✅ **Fresh data guarantee** - Models re-fetched from database in workers
- ✅ **Two initialization modes** - Automatic via `init()` or manual in tasks
- ✅ **Connection management** - Proper connection lifecycle handling
- ✅ **Multiple database support** - PostgreSQL, MySQL, SQLite
- ✅ **Multiprocessing-safe** - Works with forked worker processes
- ✅ **90%+ payload reduction** - Only primary keys stored in queue

**Configuration:**

AsyncTasQ supports two ways to use Tortoise ORM models in tasks:

**Option 1: Automatic Initialization (Recommended for Production)**

Pass Tortoise configuration to `init()` - AsyncTasQ automatically initializes Tortoise when models are accessed in workers. This is the preferred approach for production deployments as it ensures consistent initialization across all workers.

```python
from tortoise import fields
from tortoise.models import Model
from asynctasq import init, task, RedisConfig

# Define your Tortoise model
class User(Model):
    id = fields.IntField(pk=True)
    email = fields.CharField(max_length=255, index=True)
    name = fields.CharField(max_length=100)
    created_at = fields.DatetimeField(auto_now_add=True)

    class Meta:
        table = "users"

# Initialize AsyncTasQ with Tortoise auto-initialization
init(
    {
        'driver': 'redis',
        'redis': RedisConfig(url='redis://localhost:6379')
    },
    tortoise_config={
        'db_url': 'postgres://user:pass@localhost/db',
        'modules': {'models': ['app.models']},
        # Optional: Connection pool configuration
        'use_tz': True,
        'timezone': 'UTC',
    }
)

# Define task - Tortoise auto-initializes when user is accessed
@task(queue='users')
async def send_welcome_email(user: User):
    # Tortoise model automatically serialized as reference on dispatch
    # Model auto-fetched from database when accessed in worker
    # Connection automatically initialized using config from init()
    print(f"Sending welcome email to {user.email}")
    print(f"User created at: {user.created_at}")

# Dispatch task
async def main():
    from tortoise import Tortoise

    # Initialize Tortoise in dispatch context (your API/app)
    await Tortoise.init(
        db_url='postgres://user:pass@localhost/db',
        modules={'models': ['app.models']}
    )
    await Tortoise.generate_schemas()  # Create tables if needed

    # Fetch user and dispatch task
    user = await User.get(id=1)
    # Only user.id (PK) is serialized to queue - 90%+ payload reduction
    await send_welcome_email(user=user).dispatch()

    # Clean up
    await Tortoise.close_connections()
```

**Option 2: Manual Initialization (Advanced)**

Initialize Tortoise manually in your task function. This approach gives you more control over connection lifecycle and is useful for custom initialization logic or when you need different database configurations per task.

```python
from tortoise import Tortoise, fields
from tortoise.models import Model
from asynctasq import task

class User(Model):
    id = fields.IntField(pk=True)
    email = fields.CharField(max_length=255)
    name = fields.CharField(max_length=100)
    is_active = fields.BooleanField(default=True)

    class Meta:
        table = "users"

@task(queue='users')
async def send_welcome_email(user: User):
    # Initialize Tortoise in task if needed (checks if already initialized)
    if not Tortoise._inited:
        await Tortoise.init(
            db_url='postgres://user:pass@localhost/db',
            modules={'models': ['app.models']},
            # Optional: Production connection pool settings
            connection_config={
                'min_pool_size': 5,
                'max_pool_size': 20,
            }
        )

    # Access model data - automatically fetched if not already loaded
    print(f"Sending welcome email to {user.email}")
    print(f"User active: {user.is_active}")

    # Update model after processing
    user.is_active = True
    await user.save()

# Dispatch task
async def main():
    await Tortoise.init(
        db_url='postgres://user:pass@localhost/db',
        modules={'models': ['app.models']}
    )

    user = await User.get(id=1)
    await send_welcome_email(user=user).dispatch()

    await Tortoise.close_connections()
```

**Advanced Features:**

```python
from tortoise import fields
from tortoise.models import Model
from asynctasq import task
import logging

logger = logging.getLogger(__name__)

class Order(Model):
    id = fields.IntField(pk=True)
    user_id = fields.IntField()
    total = fields.DecimalField(max_digits=10, decimal_places=2)
    status = fields.CharField(max_length=50)

    class Meta:
        table = "orders"

@task(queue='orders', max_attempts=5, retry_delay=120)
async def process_order(order: Order):
    """Process order with automatic model fetching and error handling."""
    try:
        # Model is automatically fetched fresh from database
        logger.info(f"Processing order {order.id} with total ${order.total}")

        # Perform business logic
        order.status = 'processing'
        await order.save()

        # ... process payment, send notifications, etc.

        order.status = 'completed'
        await order.save()

    except Exception as e:
        logger.error(f"Order {order.id} processing failed: {e}")
        order.status = 'failed'
        await order.save()
        raise  # Re-raise to trigger AsyncTasQ retry mechanism
```

**Multiple Models in One Task:**

```python
from tortoise.models import Model
from tortoise import fields
from asynctasq import task

class User(Model):
    id = fields.IntField(pk=True)
    email = fields.CharField(max_length=255)

class Product(Model):
    id = fields.IntField(pk=True)
    name = fields.CharField(max_length=255)
    price = fields.DecimalField(max_digits=10, decimal_places=2)

@task(queue='notifications')
async def send_purchase_confirmation(user: User, product: Product, quantity: int):
    """Both models are automatically serialized and fetched."""
    # Models are fetched in parallel with asyncio.gather() for efficiency
    print(f"Sending confirmation to {user.email}")
    print(f"Product: {product.name} x {quantity}")
    print(f"Total: ${product.price * quantity}")
```

**Connection Lifecycle Management:**

For production deployments, properly manage Tortoise connections:

```python
from asynctasq import init, RedisConfig
from tortoise import Tortoise

# Initialize AsyncTasQ with Tortoise auto-initialization
init(
    {
        'driver': 'redis',
        'redis': RedisConfig(url='redis://localhost:6379'),
    },
    tortoise_config={
        'db_url': 'postgres://user:pass@localhost/db',
        'modules': {'models': ['app.models']},
        # Production connection pool settings
        'use_tz': True,
        'timezone': 'UTC',
        'minsize': 5,    # Minimum connections in pool
        'maxsize': 20,   # Maximum connections in pool
    }
)

# Workers will automatically:
# 1. Initialize Tortoise with these settings on first model access
# 2. Reuse connections efficiently
# 3. Handle connection cleanup on shutdown
```

**Supports:**

- ✅ Full async operations with native asyncio support
- ✅ Uses `pk` property for primary key access (works with any PK type)
- ✅ Native Tortoise async methods (`get()`, `filter()`, `save()`, etc.)
- ✅ **Automatic initialization** via `init(tortoise_config=...)` for seamless worker setup
- ✅ **Lazy loading** - models fetched on-demand when accessed in workers
- ✅ **Manual initialization** - initialize Tortoise in task functions if preferred
- ✅ **Multiple models** - pass multiple Tortoise models to a single task
- ✅ **Parallel fetching** - multiple models fetched concurrently with `asyncio.gather()`
- ✅ **Connection pooling** - efficient connection management with configurable pool sizes
- ✅ **Multiprocessing-safe** - each worker process manages its own connections
- ✅ **Foreign key support** - related models can be passed as task parameters
- ✅ **UUID primary keys** - supports int, UUID, and composite primary keys
- ✅ **Multiple databases** - PostgreSQL, MySQL, SQLite all supported

**Production Deployment Checklist:**

✅ **Use automatic initialization** via `init(tortoise_config=...)` for consistency
✅ **Configure connection pools** - set appropriate `minsize` and `maxsize`
✅ **Enable timezone support** - set `use_tz=True` and `timezone='UTC'`
✅ **Add database indexes** - index foreign keys and frequently queried fields
✅ **Monitor connection pool** - watch for connection exhaustion or timeouts
✅ **Test with multiple workers** - verify no connection sharing issues
✅ **Handle initialization errors** - log and retry if Tortoise init fails
✅ **Set up health checks** - verify database connectivity in workers
✅ **Use read replicas** - configure separate URLs for read-heavy tasks

**Common Issues & Solutions:**

| Issue                        | Symptom                                | Solution                                               |
| ---------------------------- | -------------------------------------- | ------------------------------------------------------ |
| Connection pool exhausted    | `asyncpg.exceptions.TooManyConnections` | Increase `maxsize` in connection config                |
| Stale connections            | Random query failures                  | Enable connection validation or reduce idle timeout    |
| Model not found              | `DoesNotExist` exception              | Ensure model still exists (may have been deleted)      |
| Multiple initialization      | Tortoise warnings                      | Check `Tortoise._inited` before calling `init()`       |
| Foreign key issues           | Related models not loaded              | Use `prefetch_related()` or pass related models separately |
| Timezone inconsistencies     | Datetime comparison errors             | Set `use_tz=True` and `timezone='UTC'`                 |
| Module import errors         | Models not found                       | Verify `modules` config includes all model modules     |

**Performance Optimization:**

```python
from tortoise.models import Model
from tortoise import fields
from asynctasq import task

class Article(Model):
    id = fields.IntField(pk=True)
    title = fields.CharField(max_length=255)
    author = fields.ForeignKeyField('models.User', related_name='articles')

    class Meta:
        table = "articles"
        indexes = [("author_id", "created_at")]  # Composite index

@task(queue='articles')
async def publish_article(article: Article):
    # Model is fetched with SELECT query
    # Use prefetch_related in dispatch context to avoid N+1 queries
    print(f"Publishing: {article.title}")

    # Efficient bulk operations
    await Article.filter(author_id=article.author_id).update(status='published')
```

**Testing with Tortoise ORM:**

```python
import pytest
from tortoise import Tortoise
from tortoise.contrib.test import initializer, finalizer

@pytest.fixture(scope="session")
async def db():
    # Initialize test database
    await initializer(
        modules={'models': ['app.models']},
        db_url='sqlite://:memory:',
    )
    yield
    await finalizer()

@pytest.mark.asyncio
async def test_task_with_tortoise_model(db):
    from app.models import User
    from app.tasks import send_welcome_email

    # Create test user
    user = await User.create(email='test@example.com', name='Test User')

    # Test task execution
    task = send_welcome_email(user=user)
    await task.execute()  # Direct execution for testing

    # Verify results
    assert user.email == 'test@example.com'
```

---

## Custom Type Support

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

## See Also

- **[Function-Based Tasks Examples](examples/function-based-tasks.md)** - Complete examples including ORM model usage patterns
- **[Class-Based Tasks Examples](examples/class-based-tasks.md)** - Advanced ORM integration patterns with lifecycle hooks
- **[Best Practices](best-practices.md)** - ORM-specific best practices and production deployment guidelines
