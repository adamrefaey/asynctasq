# ORM Integrations

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

- SQLAlchemy >= 2.0.44
- greenlet >= 3.2.4

**Configuration:**

Set the session factory **once** on your Base class. All models automatically inherit it - no per-model configuration needed!

**For Development/Single Process:**

```python
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from asynctasq.tasks import task

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
from asynctasq.tasks import task
from asynctasq.serializers.hooks import create_worker_session_factory

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
```
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

**For Production/Multiprocessing Workers:**

When using multiprocessing (multiple worker processes), SQLAlchemy's connection pooling can cause issues with `os.fork()`. Workers inherit engine/pool from parent process, leading to connection conflicts.

**Solution: Use NullPool for workers** (recommended by SQLAlchemy docs):

```python
from sqlalchemy.orm import DeclarativeBase
from asynctasq.tasks import task
from asynctasq.serializers.hooks import create_worker_session_factory

class Base(DeclarativeBase):
    pass

# ✅ EASIEST: Use helper function (handles NullPool automatically)
WorkerSessionFactory = create_worker_session_factory(
    'postgresql+asyncpg://user:pass@localhost/db',
    pool_pre_ping=True,      # Verify connections are alive
)

# Configure for workers
Base._asynctasq_session_factory = WorkerSessionFactory

@task(queue='users')
async def send_welcome_email(user: User):
    # Each worker process safely creates its own connections
    print(f"Sending welcome email to {user.email}")
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

| Issue | Symptom | Solution |
|-------|---------|----------|
| Protocol errors | `sslSocket error`, `connection reset` | Use NullPool for workers |
| Stale connections | `connection terminated unexpectedly` | Set `pool_pre_ping=True` |
| Connection leaks | Pool exhaustion, timeouts | Verify sessions are closed, increase `max_overflow` |
| Lazy-load errors | `DetachedInstanceError` after commit | Set `expire_on_commit=False` |
| Fork issues | Workers inherit parent connections | Use NullPool or dispose engine after fork |

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

- Django >= 5.2.8 (for full async support)
- psycopg2-binary >= 2.9.11

**Configuration:**

```python
from django.db import models
from asynctasq.tasks import task

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
    await send_welcome_email(user=user).dispatch()
```

**Supports:**

- Django 3.1+ async methods (`aget`, `acreate`, etc.)
- Fallback to sync with executor for older Django versions
- Uses `pk` property for primary key access

---

## Tortoise ORM

**Supports:** Fully async Tortoise ORM

**Installation:**

```bash
# With uv
uv add "asynctasq[tortoise]"

# With pip
pip install "asynctasq[tortoise]"
```

**Requirements:**

- tortoise-orm >= 0.25.1

**Configuration:**

```python
from tortoise import fields
from tortoise.models import Model
from asynctasq.tasks import task

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
    await send_welcome_email(user=user).dispatch()
```

**Supports:**

- Full async operations
- Uses `pk` property for primary key access
- Native Tortoise async methods

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
