# Environment Variables Configuration

## Table of Contents

- [Environment Variables Configuration](#environment-variables-configuration)
  - [Table of Contents](#table-of-contents)
  - [Getting Started with .env Files](#getting-started-with-env-files)
  - [Configuration Priority](#configuration-priority)
  - [Using Environment Variables](#using-environment-variables)
    - [Basic Setup](#basic-setup)
    - [Overriding Environment Variables](#overriding-environment-variables)
  - [Available Environment Variables](#available-environment-variables)
    - [Core Configuration](#core-configuration)
    - [Redis Driver](#redis-driver)
    - [AWS SQS Driver](#aws-sqs-driver)
    - [PostgreSQL Driver](#postgresql-driver)
    - [MySQL Driver](#mysql-driver)
    - [RabbitMQ Driver](#rabbitmq-driver)
    - [Events and Monitoring](#events-and-monitoring)
    - [Task Defaults](#task-defaults)
    - [Process Pool (Worker Only)](#process-pool-worker-only)
    - [Repository (Worker Only)](#repository-worker-only)
  - [Example Configurations](#example-configurations)
    - [Development Environment](#development-environment)
    - [Production Environment](#production-environment)
    - [Testing Environment](#testing-environment)
    - [AWS SQS Production](#aws-sqs-production)
  - [Usage Examples](#usage-examples)
    - [Using .env File Only](#using-env-file-only)
    - [Mixing .env and Code Configuration](#mixing-env-and-code-configuration)
  - [Docker and Container Deployment](#docker-and-container-deployment)
    - [Docker Compose Example](#docker-compose-example)
    - [Kubernetes ConfigMap Example](#kubernetes-configmap-example)
  - [Best Practices](#best-practices)
    - [1. Never Commit Secrets](#1-never-commit-secrets)
    - [2. Validate Configuration on Startup](#2-validate-configuration-on-startup)
    - [3. Use Type-Safe Access](#3-use-type-safe-access)
  - [Common Issues](#common-issues)
    - [Configuration Not Loading](#configuration-not-loading)
    - [Overriding Priority](#overriding-priority)
    - [Type Validation](#type-validation)
  - [Quick Migration Guide](#quick-migration-guide)
    - [From Code Configuration](#from-code-configuration)
    - [To Environment Variables](#to-environment-variables)
  - [See Also](#see-also)

AsyncTasQ supports configuration through environment variables and `.env` files, making it easy to configure your application for different environments without changing code.

## Getting Started with .env Files

The quickest way to set up environment-based configuration is to use the `publish` command:

```bash
# Publish the .env.example template to your project
asynctasq publish

# Copy it to create your environment file
cp .env.example .env

# Edit .env with your actual configuration values
```

The published `.env.example` file contains:
- All available environment variables with descriptions
- Recommended default values
- Examples for each driver configuration
- Best practices and usage tips

For more details on the publish command, see the [CLI Reference](cli-reference.md#publish-command).

## Configuration Priority

AsyncTasQ uses the following configuration priority (highest to lowest):

1. **Constructor arguments** - Values passed directly to `init()`
2. **Environment variables** - Values from your system environment
3. **`.env` file** - Values from a `.env` file in your project root
4. **Default values** - Built-in defaults

## Using Environment Variables

### Basic Setup

Create a `.env` file in your project root:

```bash
# .env
ASYNCTASQ_DRIVER=redis
ASYNCTASQ_REDIS_URL=redis://localhost:6379
ASYNCTASQ_REDIS_DB=0
```

Then initialize AsyncTasQ without any configuration:

```python
from asynctasq import init

# Configuration is automatically loaded from .env
init()
```

### Overriding Environment Variables

You can override environment variables by passing configuration directly:

```python
from asynctasq import init

# This overrides ASYNCTASQ_REDIS_DB from .env
init({
    'redis': {'db': 5}  # Takes precedence over env var
})
```

## Available Environment Variables

### Core Configuration

#### Driver Selection

```bash
# Select the queue driver
ASYNCTASQ_DRIVER=redis  # Options: redis, sqs, postgres, mysql, rabbitmq
```

### Redis Driver

```bash
# Redis connection URL
ASYNCTASQ_REDIS_URL=redis://localhost:6379

# Redis password (optional)
ASYNCTASQ_REDIS_PASSWORD=your_password

# Redis database number (0-15)
ASYNCTASQ_REDIS_DB=0

# Maximum connections in pool
ASYNCTASQ_REDIS_MAX_CONNECTIONS=100
```

### AWS SQS Driver

```bash
# AWS region
ASYNCTASQ_SQS_REGION=us-east-1

# Queue URL prefix (optional)
ASYNCTASQ_SQS_QUEUE_URL_PREFIX=https://sqs.us-east-1.amazonaws.com/123456789012/

# Custom endpoint URL (for LocalStack or testing)
ASYNCTASQ_SQS_ENDPOINT_URL=http://localhost:4566

# AWS credentials (optional, uses boto3 defaults if not set)
ASYNCTASQ_SQS_AWS_ACCESS_KEY_ID=your_access_key
ASYNCTASQ_SQS_AWS_SECRET_ACCESS_KEY=your_secret_key
```

### PostgreSQL Driver

```bash
# PostgreSQL connection DSN
ASYNCTASQ_POSTGRES_DSN=postgresql://user:password@localhost:5432/dbname

# Table names
ASYNCTASQ_POSTGRES_QUEUE_TABLE=task_queue
ASYNCTASQ_POSTGRES_DEAD_LETTER_TABLE=dead_letter_queue

# Connection pool settings
ASYNCTASQ_POSTGRES_MIN_POOL_SIZE=10
ASYNCTASQ_POSTGRES_MAX_POOL_SIZE=10
```

### MySQL Driver

```bash
# MySQL connection DSN
ASYNCTASQ_MYSQL_DSN=mysql://user:password@localhost:3306/dbname

# Table names
ASYNCTASQ_MYSQL_QUEUE_TABLE=task_queue
ASYNCTASQ_MYSQL_DEAD_LETTER_TABLE=dead_letter_queue

# Connection pool settings
ASYNCTASQ_MYSQL_MIN_POOL_SIZE=10
ASYNCTASQ_MYSQL_MAX_POOL_SIZE=10
```

### RabbitMQ Driver

```bash
# RabbitMQ connection URL
ASYNCTASQ_RABBITMQ_URL=amqp://guest:guest@localhost:5672/

# Exchange name
ASYNCTASQ_RABBITMQ_EXCHANGE_NAME=asynctasq

# Prefetch count (number of messages to prefetch)
ASYNCTASQ_RABBITMQ_PREFETCH_COUNT=1
```

### Events and Monitoring

```bash
# Redis URL for event emitter (optional)
ASYNCTASQ_EVENTS_REDIS_URL=redis://localhost:6379

# Event channel name
ASYNCTASQ_EVENTS_CHANNEL=asynctasq:events

# Enable Redis event emitter
ASYNCTASQ_EVENTS_ENABLE_EVENT_EMITTER_REDIS=true
```

### Task Defaults

```bash
# Default queue name
ASYNCTASQ_TASK_DEFAULTS_QUEUE=default

# Default maximum retry attempts
ASYNCTASQ_TASK_DEFAULTS_MAX_ATTEMPTS=3

# Default retry strategy (fixed or exponential)
ASYNCTASQ_TASK_DEFAULTS_RETRY_STRATEGY=exponential

# Default retry delay in seconds
ASYNCTASQ_TASK_DEFAULTS_RETRY_DELAY=60
```

### Process Pool (Worker Only)

```bash
# Process pool size (defaults to CPU count if not set)
ASYNCTASQ_PROCESS_POOL_SIZE=4

# Maximum tasks per child process (unlimited if not set)
ASYNCTASQ_PROCESS_POOL_MAX_TASKS_PER_CHILD=100
```

### Repository (Worker Only)

```bash
# Keep completed tasks in the queue
ASYNCTASQ_REPOSITORY_KEEP_COMPLETED_TASKS=false
```

## Example Configurations

### Development Environment

```bash
# .env.development
ASYNCTASQ_DRIVER=redis
ASYNCTASQ_REDIS_URL=redis://localhost:6379
ASYNCTASQ_REDIS_DB=0
ASYNCTASQ_TASK_DEFAULTS_QUEUE=dev_queue
ASYNCTASQ_EVENTS_ENABLE_EVENT_EMITTER_REDIS=true
```

### Production Environment

```bash
# .env.production
ASYNCTASQ_DRIVER=postgres
ASYNCTASQ_POSTGRES_DSN=postgresql://user:password@prod-db:5432/asynctasq
ASYNCTASQ_POSTGRES_MIN_POOL_SIZE=20
ASYNCTASQ_POSTGRES_MAX_POOL_SIZE=50
ASYNCTASQ_TASK_DEFAULTS_MAX_ATTEMPTS=5
ASYNCTASQ_TASK_DEFAULTS_RETRY_STRATEGY=exponential
ASYNCTASQ_REPOSITORY_KEEP_COMPLETED_TASKS=true
```

### Testing Environment

```bash
# .env.test
ASYNCTASQ_DRIVER=redis
ASYNCTASQ_REDIS_URL=redis://localhost:6379
ASYNCTASQ_REDIS_DB=15
ASYNCTASQ_TASK_DEFAULTS_QUEUE=test_queue
```

### AWS SQS Production

```bash
# .env.aws
ASYNCTASQ_DRIVER=sqs
ASYNCTASQ_SQS_REGION=us-west-2
ASYNCTASQ_SQS_QUEUE_URL_PREFIX=https://sqs.us-west-2.amazonaws.com/123456789012/
# AWS credentials are usually loaded from IAM roles in production
```

## Usage Examples

### Using .env File Only

```python
# app.py
from asynctasq import init, task

# All configuration loaded from .env
init()

@task()
async def process_data(data: str):
    print(f"Processing: {data}")
```

### Mixing .env and Code Configuration

```python
# app.py
from asynctasq import init, RedisConfig

# Base config from .env, override specific settings
init({
    'redis': RedisConfig(db=5, max_connections=200)
})
```

## Docker and Container Deployment

### Docker Compose Example

```yaml
# docker-compose.yml
version: '3.8'

services:
  worker:
    image: myapp:latest
    environment:
      ASYNCTASQ_DRIVER: redis
      ASYNCTASQ_REDIS_URL: redis://redis:6379
      ASYNCTASQ_REDIS_DB: 0
      ASYNCTASQ_TASK_DEFAULTS_QUEUE: production
      ASYNCTASQ_TASK_DEFAULTS_MAX_ATTEMPTS: 5
    depends_on:
      - redis

  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
```

### Kubernetes ConfigMap Example

```yaml
# deployment.yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: asynctasq-config
data:
  ASYNCTASQ_DRIVER: "postgres"
  ASYNCTASQ_POSTGRES_DSN: "postgresql://user:password@postgres:5432/asynctasq"
  ASYNCTASQ_POSTGRES_MIN_POOL_SIZE: "20"
  ASYNCTASQ_POSTGRES_MAX_POOL_SIZE: "50"
  ASYNCTASQ_TASK_DEFAULTS_QUEUE: "production"
  ASYNCTASQ_TASK_DEFAULTS_MAX_ATTEMPTS: "5"
```

## Best Practices

### 1. Never Commit Secrets

Add `.env` to your `.gitignore`:

```gitignore
# .gitignore
.env
.env.local
.env.production
```

Provide a template instead:

```bash
# .env.example
ASYNCTASQ_DRIVER=redis
ASYNCTASQ_REDIS_URL=redis://localhost:6379
ASYNCTASQ_REDIS_PASSWORD=your_password_here
```

### 2. Validate Configuration on Startup

```python
from asynctasq import init, Config

init()

# Validate configuration
config = Config.get()
assert config.driver in ['redis', 'sqs', 'postgres', 'mysql', 'rabbitmq']
print(f"✓ Using {config.driver} driver")
```

### 3. Use Type-Safe Access

```python
from asynctasq import Config

config = Config.get()

# Type-safe access to configuration
if config.driver == 'redis':
    print(f"Redis URL: {config.redis.url}")
    print(f"Redis DB: {config.redis.db}")
```

## Common Issues

### Configuration Not Loading

The `.env` file must be in the directory where you run your application. Variable names are case-sensitive and must start with `ASYNCTASQ_` prefix.

### Overriding Priority

Remember the priority order:
1. Constructor arguments (highest)
2. Environment variables
3. .env file
4. Defaults (lowest)

```python
# Constructor arguments always win
init({
    'driver': 'redis'  # Overrides ASYNCTASQ_DRIVER env var
})
```

### Type Validation

Pydantic validates and converts types automatically:

```bash
# This works - string "5" is converted to int 5
ASYNCTASQ_REDIS_DB=5

# This also works
ASYNCTASQ_REDIS_DB="5"

# This fails validation - must be 0-15
ASYNCTASQ_REDIS_DB=20
```

## Quick Migration Guide

### From Code Configuration

```python
from asynctasq import init, RedisConfig

init({
    'driver': 'redis',
    'redis': RedisConfig(
        url='redis://localhost:6379',
        db=0,
        max_connections=100
    ),
    'task_defaults': {
        'queue': 'production',
        'max_attempts': 5
    }
})
```

### To Environment Variables

```bash
# .env
ASYNCTASQ_DRIVER=redis
ASYNCTASQ_REDIS_URL=redis://localhost:6379
ASYNCTASQ_REDIS_DB=0
ASYNCTASQ_REDIS_MAX_CONNECTIONS=100
ASYNCTASQ_TASK_DEFAULTS_QUEUE=production
ASYNCTASQ_TASK_DEFAULTS_MAX_ATTEMPTS=5
```

```python
from asynctasq import init

init()  # Loads from .env automatically
```

## See Also

- [Configuration Guide](configuration.md) - Detailed configuration options
- [Installation Guide](installation.md) - Getting started
- [Queue Drivers](queue-drivers.md) - Driver-specific configuration
