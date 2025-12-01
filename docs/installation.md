# Installation

## Using uv (Recommended)

[uv](https://github.com/astral-sh/uv) is a fast Python package installer and resolver.

```bash
# Basic installation
uv add q-task

# With specific drivers
uv add "q-task[redis]"      # Redis support
uv add "q-task[postgres]"   # PostgreSQL support
uv add "q-task[mysql]"      # MySQL support
uv add "q-task[rabbitmq]"   # RabbitMQ support
uv add "q-task[sqs]"        # AWS SQS support

# With ORM support
uv add "q-task[sqlalchemy]" # SQLAlchemy
uv add "q-task[django]"     # Django
uv add "q-task[tortoise]"   # Tortoise ORM

# With framework integrations
uv add "q-task[fastapi]"    # FastAPI integration

# Complete installation with all features
uv add "q-task[all]"
```

## Using pip

```bash
# Basic installation
pip install q-task

# With specific drivers
pip install "q-task[redis]"
pip install "q-task[postgres]"
pip install "q-task[mysql]"
pip install "q-task[rabbitmq]"
pip install "q-task[sqs]"

# With ORM support
pip install "q-task[sqlalchemy]"
pip install "q-task[django]"
pip install "q-task[tortoise]"

# With framework integrations
pip install "q-task[fastapi]"

# Complete installation
pip install "q-task[all]"
```
