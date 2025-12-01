# Installation

## Using uv (Recommended)

[uv](https://github.com/astral-sh/uv) is a fast Python package installer and resolver.

```bash
# Basic installation
uv add async-task-q

# With specific drivers
uv add "async-task-q[redis]"      # Redis support
uv add "async-task-q[postgres]"   # PostgreSQL support
uv add "async-task-q[mysql]"      # MySQL support
uv add "async-task-q[rabbitmq]"   # RabbitMQ support
uv add "async-task-q[sqs]"        # AWS SQS support

# With ORM support
uv add "async-task-q[sqlalchemy]" # SQLAlchemy
uv add "async-task-q[django]"     # Django
uv add "async-task-q[tortoise]"   # Tortoise ORM

# With framework integrations
uv add "async-task-q[fastapi]"    # FastAPI integration

# Complete installation with all features
uv add "async-task-q[all]"
```

## Using pip

```bash
# Basic installation
pip install async-task-q

# With specific drivers
pip install "async-task-q[redis]"
pip install "async-task-q[postgres]"
pip install "async-task-q[mysql]"
pip install "async-task-q[rabbitmq]"
pip install "async-task-q[sqs]"

# With ORM support
pip install "async-task-q[sqlalchemy]"
pip install "async-task-q[django]"
pip install "async-task-q[tortoise]"

# With framework integrations
pip install "async-task-q[fastapi]"

# Complete installation
pip install "async-task-q[all]"
```
