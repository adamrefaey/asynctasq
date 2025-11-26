# Installation

## Using uv (Recommended)

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

## Using pip

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
