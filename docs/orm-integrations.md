# ORM Integrations

Async TasQ automatically handles ORM model serialization and deserialization, reducing queue payload size and ensuring fresh data.

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

```python
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from asynctasq.core.task import task
from asynctasq.serializers.orm_handler import set_sqlalchemy_session_factory

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
from asynctasq.core.task import task

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
from asynctasq.core.task import task

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
