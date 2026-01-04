# Queue Drivers

## Table of Contents

- [Queue Drivers](#queue-drivers)
  - [Table of Contents](#table-of-contents)
  - [Overview](#overview)
  - [Redis Driver](#redis-driver)
  - [PostgreSQL Driver](#postgresql-driver)
  - [MySQL Driver](#mysql-driver)
  - [AWS SQS Driver](#aws-sqs-driver)
  - [RabbitMQ Driver](#rabbitmq-driver)
  - [Driver Comparison](#driver-comparison)
  - [Configuration Reference](#configuration-reference)
    - [Complete Configuration Examples](#complete-configuration-examples)
    - [Common Patterns](#common-patterns)
  - [Migration and Schema Setup](#migration-and-schema-setup)
    - [PostgreSQL](#postgresql)
    - [MySQL](#mysql)
    - [Redis](#redis)
    - [AWS SQS](#aws-sqs)
    - [RabbitMQ](#rabbitmq)
  - [Best Practices](#best-practices)
    - [Connection Pooling](#connection-pooling)
    - [Error Handling](#error-handling)
    - [Performance Tuning](#performance-tuning)
    - [Security](#security)
    - [Monitoring](#monitoring)
    - [High Availability](#high-availability)
    - [Cost Optimization](#cost-optimization)

AsyncTasQ supports five production-ready queue drivers with identical APIs. This guide provides complete configuration details, setup instructions, and best practices for each driver.

**Configuration:** All drivers support code, environment variables, or .env files. See [Environment Variables Guide](environment-variables.md) and [Configuration - init() Function](configuration.md#init) for complete details.

## Overview

All drivers implement the same `BaseDriver` interface, providing:

✅ **Consistent API** - Same methods across all drivers
✅ **Task queueing** - Enqueue tasks with optional delays
✅ **Reliable dequeue** - Atomic operations with crash recovery
✅ **Acknowledgments** - ACK/NACK for reliable processing
✅ **Delayed tasks** - Schedule tasks for future execution
✅ **Visibility timeout** - Automatic recovery of crashed workers
✅ **Connection pooling** - Efficient resource utilization
✅ **Retry strategies** - Exponential backoff for failed tasks (PostgreSQL/MySQL)
✅ **Dead-letter queue** - Failed task handling (PostgreSQL/MySQL/SQS)

## Redis Driver

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
uv add "asynctasq[redis]"

# With pip
pip install "asynctasq[redis]"
```

**Configuration:**

```python
# Recommended: Use .env file (see Environment Variables Guide)
init()  # Loads from .env automatically

# Quick testing: Code configuration
from asynctasq import init, RedisConfig

init({
    'driver': 'redis',
    'redis': RedisConfig(
        url='redis://localhost:6379',
        password='secret',
        db=0,
        max_connections=100
    )
})
```

**Configuration Parameters:**

| Parameter         | Type          | Default                  | Description                  |
| ----------------- | ------------- | ------------------------ | ---------------------------- |
| `url`             | `str`         | `redis://localhost:6379` | Redis connection URL         |
| `password`        | `str \| None` | `None`                   | Redis password (optional)    |
| `db`              | `int`         | `0`                      | Redis database number (0-15) |
| `max_connections` | `int`         | `100`                    | Maximum connections in pool  |

**Architecture:**

- Immediate tasks: Redis List at `queue:{name}`
- Processing tasks: Redis List at `queue:{name}:processing`
- Delayed tasks: Sorted Set at `queue:{name}:delayed`

**Use cases:** Production apps, microservices, distributed systems, high-throughput scenarios

---

## PostgreSQL Driver

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
uv add "asynctasq[postgres]"

# With pip
pip install "asynctasq[postgres]"
```

**Configuration:**

```python
# Recommended: Use .env file (see Environment Variables Guide)
init()  # Loads from .env

# Quick testing: Code configuration
from asynctasq import init, PostgresConfig

init({
    'driver': 'postgres',
    'postgres': PostgresConfig(
        dsn='postgresql://user:pass@localhost:5432/dbname',
        queue_table='task_queue',
        dead_letter_table='dead_letter_queue',
        min_pool_size=10,
        max_pool_size=10
    )
})
```

**Configuration Parameters:**

| Parameter           | Type  | Default               | Description                                                           |
| ------------------- | ----- | --------------------- | --------------------------------------------------------------------- |
| `dsn`               | `str` | **Required**          | PostgreSQL connection string (e.g., `postgresql://user:pass@host/db`) |
| `queue_table`       | `str` | `'task_queue'`        | Main queue table name                                                 |
| `dead_letter_table` | `str` | `'dead_letter_queue'` | Dead-letter queue table name for failed tasks                         |
| `min_pool_size`     | `int` | `10`                  | Minimum number of connections in the pool                             |
| `max_pool_size`     | `int` | `10`                  | Maximum number of connections in the pool                             |

**Schema Setup:**

```bash
# Initialize database schema (creates queue and dead-letter tables)
python -m asynctasq migrate --driver postgres --postgres-dsn postgresql://user:pass@localhost/dbname

# Or with uv
uv run python -m asynctasq migrate --driver postgres --postgres-dsn postgresql://user:pass@localhost/dbname
```

**Use cases:** Enterprise apps, existing PostgreSQL infrastructure, need for ACID guarantees, complex failure handling

---

## MySQL Driver

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
uv add "asynctasq[mysql]"

# With pip
pip install "asynctasq[mysql]"
```

**Configuration:**

```python
# Recommended: Use .env file (see Environment Variables Guide)
init()  # Loads from .env

# Quick testing: Code configuration
from asynctasq import init, MySQLConfig

init({
    'driver': 'mysql',
    'mysql': MySQLConfig(
        dsn='mysql://user:pass@localhost:3306/dbname',
        queue_table='task_queue',
        dead_letter_table='dead_letter_queue',
        min_pool_size=10,
        max_pool_size=10
    )
})
```

**Configuration Parameters:**

| Parameter           | Type  | Default               | Description                                                      |
| ------------------- | ----- | --------------------- | ---------------------------------------------------------------- |
| `dsn`               | `str` | **Required**          | MySQL connection string (e.g., `mysql://user:pass@host:port/db`) |
| `queue_table`       | `str` | `'task_queue'`        | Main queue table name                                            |
| `dead_letter_table` | `str` | `'dead_letter_queue'` | Dead-letter queue table name for failed tasks                    |
| `min_pool_size`     | `int` | `10`                  | Minimum number of connections in the pool                        |
| `max_pool_size`     | `int` | `10`                  | Maximum number of connections in the pool                        |

**Schema Setup:**

```bash
# Initialize database schema
python -m asynctasq migrate --driver mysql --mysql-dsn mysql://user:pass@localhost:3306/dbname

# Or with uv
uv run python -m asynctasq migrate --driver mysql --mysql-dsn mysql://user:pass@localhost:3306/dbname
```

**Use cases:** Enterprise apps, existing MySQL infrastructure, need for ACID guarantees, complex failure handling

---

## AWS SQS Driver

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
uv add "asynctasq[sqs]"

# With pip
pip install "asynctasq[sqs]"
```

**Configuration:**

```python
# Recommended: Use .env file (see Environment Variables Guide)
init()  # Loads from .env

# Quick testing: Code configuration
from asynctasq import init, SQSConfig

init({
    'driver': 'sqs',
    'sqs': SQSConfig(
        region_name='us-east-1',
        queue_url_prefix='https://sqs.us-east-1.amazonaws.com/123456789/',
        aws_access_key_id='your_key',  # Optional
        aws_secret_access_key='your_secret',  # Optional
        endpoint_url='http://localhost:4566'  # Optional (LocalStack)
    )
})
```

**Configuration Parameters:**

| Parameter               | Type  | Default      | Description                                                              |
| ----------------------- | ----- | ------------ | ------------------------------------------------------------------------ |
| `region_name`           | `str` | **Required** | AWS region (e.g., `'us-east-1'`, `'eu-west-1'`)                          |
| `queue_url_prefix`      | `str` | **Required** | Base URL for queues (e.g., `'https://sqs.us-east-1.amazonaws.com/123/'`) |
| `aws_access_key_id`     | `str` | `None`       | AWS access key (uses boto3 default chain if omitted)                     |
| `aws_secret_access_key` | `str` | `None`       | AWS secret key (uses boto3 default chain if omitted)                     |
| `endpoint_url`          | `str` | `None`       | Custom endpoint URL for LocalStack or compatible services                |

**Queue URLs:** Constructed as `{queue_url_prefix}{queue_name}`

**Limitations:**

- Maximum delay: 15 minutes (use EventBridge Scheduler or Step Functions for longer delays)
- Approximate queue counts (not exact like databases)
- Base64 encoding overhead (SQS requires UTF-8 text)

**Use cases:** AWS/serverless apps, multi-region deployments, zero infrastructure management

---

## RabbitMQ Driver

**Best for:** Production applications, existing RabbitMQ infrastructure, AMQP-based systems

**Features:**

- AMQP 0.9.1 protocol support with aio-pika
- Direct exchange pattern for simple routing
- Delayed tasks without plugins (timestamp-based)
- Auto-reconnection with connect_robust for resilience
- Fair task distribution via prefetch_count
- Persistent messages for reliability
- Queue auto-creation on-demand
- Message acknowledgments for reliable processing

**Requirements:** RabbitMQ server 3.8+ (no plugins required)

**Installation:**

```bash
# With uv
uv add "asynctasq[rabbitmq]"

# With pip
pip install "asynctasq[rabbitmq]"
```

**Configuration:**

```python
# Recommended: Use .env file (see Environment Variables Guide)
init()  # Loads from .env

# Quick testing: Code configuration
from asynctasq import init, RabbitMQConfig

init({
    'driver': 'rabbitmq',
    'rabbitmq': RabbitMQConfig(
        url='amqp://guest:guest@localhost:5672/',
        exchange_name='asynctasq',
        prefetch_count=1
    )
})
```

**Configuration Parameters:**

| Parameter        | Type  | Default       | Description                                                       |
| ---------------- | ----- | ------------- | ----------------------------------------------------------------- |
| `url`            | `str` | **Required**  | AMQP connection URL (e.g., `'amqp://user:pass@host:port/'`)       |
| `exchange_name`  | `str` | `'asynctasq'` | Direct exchange name for routing messages                         |
| `prefetch_count` | `int` | `1`           | Number of messages to prefetch per worker (1 = fair distribution) |

**Architecture:**

- Immediate tasks: Direct exchange with queue (routing_key = queue_name)
- Delayed tasks: Stored in delayed queue with timestamp prepended to message body
- Delayed queue: Named `{queue_name}_delayed` for each main queue
- Exchange: Durable direct exchange for message routing
- Queues: Durable, not auto-delete (persistent queues)

**Delayed Task Implementation:**

- Timestamp-based approach (no plugins required)
- Ready timestamp encoded as 8-byte double prepended to task data
- `_process_delayed_tasks()` checks timestamps and moves ready messages to main queue
- Avoids RabbitMQ per-message TTL limitations

**Use cases:** Production apps with existing RabbitMQ infrastructure, AMQP-based systems, microservices using RabbitMQ

---

## Driver Comparison

| Driver         | Best For       | Pros                                          | Cons                           | Requirements   |
| -------------- | -------------- | --------------------------------------------- | ------------------------------ | -------------- |
| **Redis**      | Production     | Fast, reliable, distributed, mature           | Requires Redis server          | Redis 6.2+     |
| **PostgreSQL** | Enterprise     | ACID, DLQ, visibility timeout, transactions   | Requires PostgreSQL setup      | PostgreSQL 14+ |
| **MySQL**      | Enterprise     | ACID, DLQ, visibility timeout, transactions   | Requires MySQL setup           | MySQL 8.0+     |
| **RabbitMQ**   | Production     | AMQP standard, mature, no plugins needed      | Requires RabbitMQ server       | RabbitMQ 3.8+  |
| **AWS SQS**    | AWS/Serverless | Managed, auto-scaling, zero ops, multi-region | AWS-specific, cost per message | AWS account    |

**Recommendation:**

- **Production (general):** Use `redis` for most applications
- **Production (enterprise):** Use `postgres` or `mysql` when you need ACID guarantees
- **AMQP-based systems:** Use `rabbitmq` if you have existing RabbitMQ infrastructure
- **AWS/cloud-native:** Use `sqs` for managed infrastructure

---

## Configuration Reference

### Complete Configuration Examples

**Redis:**
```python
from asynctasq import init, RedisConfig

init({
    'driver': 'redis',
    'redis': RedisConfig(
        url='redis://localhost:6379',
        password='secret',
        db=0,
        max_connections=100
    )
})
```

**PostgreSQL:**
```python
from asynctasq import init, PostgresConfig

init({
    'driver': 'postgres',
    'postgres': PostgresConfig(
        dsn='postgresql://user:pass@localhost:5432/dbname',
        queue_table='task_queue',
        dead_letter_table='dead_letter_queue',
        min_pool_size=10,
        max_pool_size=10
    )
})
```

**MySQL:**
```python
from asynctasq import init, MySQLConfig

init({
    'driver': 'mysql',
    'mysql': MySQLConfig(
        dsn='mysql://user:pass@localhost:3306/dbname',
        queue_table='task_queue',
        dead_letter_table='dead_letter_queue',
        min_pool_size=10,
        max_pool_size=10
    )
})
```

**AWS SQS:**
```python
from asynctasq import init, SQSConfig

init({
    'driver': 'sqs',
    'sqs': SQSConfig(
        region_name='us-east-1',
        queue_url_prefix='https://sqs.us-east-1.amazonaws.com/123456789/',
        aws_access_key_id='your_key',  # Optional
        aws_secret_access_key='your_secret',  # Optional
        endpoint_url='http://localhost:4566'  # Optional (LocalStack)
    )
})
```

**RabbitMQ:**
```python
from asynctasq import init, RabbitMQConfig

init({
    'driver': 'rabbitmq',
    'rabbitmq': RabbitMQConfig(
        url='amqp://guest:guest@localhost:5672/',
        exchange_name='asynctasq',
        prefetch_count=1
    )
})
```

### Common Patterns

**Using Environment Variables:**
```python
import os
from asynctasq import init

init({
    'driver': os.getenv('QUEUE_DRIVER', 'redis'),
    'redis': {
        'url': os.getenv('REDIS_URL', 'redis://localhost:6379'),
        'password': os.getenv('REDIS_PASSWORD'),
        'max_connections': int(os.getenv('REDIS_MAX_CONNECTIONS', '100'))
    }
})
```

**Development vs Production:**
```python
from asynctasq import init
import os

# Use Redis in production, memory driver for tests (if available)
driver = 'redis' if os.getenv('ENV') == 'production' else 'redis'

init({
    'driver': driver,
    'redis': {
        'url': os.getenv('REDIS_URL', 'redis://localhost:6379')
    }
})
```

---

## Migration and Schema Setup

### PostgreSQL

Initialize database schema:

```bash
# Using python -m
python -m asynctasq migrate --driver postgres --postgres-dsn postgresql://user:pass@localhost/dbname

# Using uv
uv run python -m asynctasq migrate --driver postgres --postgres-dsn postgresql://user:pass@localhost/dbname

# With custom table names
python -m asynctasq migrate --driver postgres \
  --postgres-dsn postgresql://user:pass@localhost/dbname \
  --postgres-queue-table custom_queue \
  --postgres-dead-letter-table custom_dlq
```

**Schema Details:**
- Creates `task_queue` table with columns: `id`, `queue_name`, `payload`, `available_at`, `locked_until`, `status`, `current_attempt`, `max_attempts`, `visibility_timeout_seconds`, `created_at`, `updated_at`
- Creates `dead_letter_queue` table for failed tasks
- Adds indexes for efficient query performance
- Idempotent - safe to run multiple times

### MySQL

Initialize database schema:

```bash
# Using python -m
python -m asynctasq migrate --driver mysql --mysql-dsn mysql://user:pass@localhost:3306/dbname

# Using uv
uv run python -m asynctasq migrate --driver mysql --mysql-dsn mysql://user:pass@localhost:3306/dbname

# With custom table names
python -m asynctasq migrate --driver mysql \
  --mysql-dsn mysql://user:pass@localhost:3306/dbname \
  --mysql-queue-table custom_queue \
  --mysql-dead-letter-table custom_dlq
```

**Schema Details:**
- Creates InnoDB tables with UTF8MB4 charset
- Uses `DATETIME(6)` for microsecond precision
- Row-level locking with `FOR UPDATE SKIP LOCKED`
- Idempotent - safe to run multiple times

### Redis

No schema setup required - Redis is schemaless. Queues are created automatically on first use.

### AWS SQS

Queues are created automatically with default settings:
- Message retention: 14 days
- Visibility timeout: 30 seconds (queue default, overridden per task with 3600s/1 hour default)
- Long polling: 20 seconds
- Delivery delay: 0 seconds (overridden per task)

### RabbitMQ

Exchanges and queues are declared automatically:
- Durable direct exchange
- Durable queues (not auto-delete)
- Persistent messages
- Fair distribution (prefetch_count=1)

---

## Best Practices

**Worker Deployment:** For comprehensive guidance on running workers, deployment patterns, and production configurations, see [Running Workers](running-workers.md).

### Connection Pooling

**Redis:**
- Use `max_connections=100` for high-throughput apps
- One pool shared across all workers
- Connection reuse for efficiency

**PostgreSQL/MySQL:**
- Set `min_pool_size=10, max_pool_size=10` for predictable performance
- One connection per concurrent task
- Increase pool size if you see connection timeouts

### Error Handling

**PostgreSQL/MySQL:**
- Failed tasks automatically moved to dead-letter queue after task's `max_attempts` is reached
- Dead-letter queue includes: original payload, attempt count, error message, timestamp
- Query dead-letter queue for debugging: `SELECT * FROM dead_letter_queue WHERE queue_name = 'your_queue'`

**All Drivers:**
- Tasks retry automatically up to task's `max_attempts` (set via `ASYNCTASQ_TASK_DEFAULTS_MAX_ATTEMPTS` or per-task)
- Use task-level `timeout` to prevent hung tasks
- Monitor queue depths to detect processing bottlenecks

### Performance Tuning

**Redis:**
- Use pipelining for bulk operations (built-in)
- Keep payload sizes small (< 1MB recommended)
- Use separate Redis database for queues (`db=1`)

**PostgreSQL/MySQL:**
- Monitor connection pool utilization
- Add indexes on `queue_name` for multi-queue apps
- Use `VACUUM` (PostgreSQL) or `OPTIMIZE TABLE` (MySQL) periodically

**RabbitMQ:**
- Set appropriate `prefetch_count` (1 for fair distribution, higher for throughput)
- Monitor queue length and consumer count
- Use separate vhosts for isolation

**AWS SQS:**
- Use batch operations when possible (not yet implemented in driver)
- Monitor CloudWatch metrics for queue depth
- **⚠️ CRITICAL: Configure `visibility_timeout` per task** - See [Configuration - Visibility Timeout Warning](configuration.md#visibility-timeout-warning)

### Security

**Redis:**
```python
init({
    'driver': 'redis',
    'redis': {
        'url': 'rediss://localhost:6380',  # TLS
        'password': os.getenv('REDIS_PASSWORD')
    }
})
```

**PostgreSQL/MySQL:**
```python
# Use SSL/TLS in connection string
dsn='postgresql://user:pass@localhost:5432/dbname?sslmode=require'
dsn='mysql://user:pass@localhost:3306/dbname?ssl=true'
```

**AWS SQS:**
- Use IAM roles instead of access keys
- Restrict permissions to specific queues
- Enable encryption at rest

**RabbitMQ:**
```python
init({
    'driver': 'rabbitmq',
    'rabbitmq': {
        'url': 'amqps://user:pass@localhost:5671/',  # TLS
    }
})
```

### Monitoring

**Queue Metrics to Track:**
- Queue depth (backlog)
- Throughput (tasks/second)
- Processing time (average)
- Error rate (failed tasks)
- Dead-letter queue size

**Redis:**
```python
# Get queue length
client = driver.client
queue_length = await client.llen('queue:default')
processing_length = await client.llen('queue:default:processing')
delayed_length = await client.zcard('queue:default:delayed')
```

**PostgreSQL/MySQL:**
```sql
-- Queue depth
SELECT queue_name, COUNT(*) FROM task_queue
WHERE status = 'pending'
GROUP BY queue_name;

-- Dead-letter queue
SELECT queue_name, COUNT(*) FROM dead_letter_queue
GROUP BY queue_name;
```

**AWS SQS:**
- Use CloudWatch metrics: `ApproximateNumberOfMessagesVisible`, `ApproximateAgeOfOldestMessage`
- Set up alarms for queue depth thresholds

**RabbitMQ:**
- Use Management UI at `http://localhost:15672`
- Monitor queue depth, consumer count, message rates
- Set up alerts for queue buildup

### High Availability

**Redis:**
- Use Redis Cluster or Sentinel for failover
- Configure read replicas for scaling
- Enable persistence (RDB + AOF)

**PostgreSQL/MySQL:**
- Use streaming replication (PostgreSQL) or master-slave replication (MySQL)
- Configure automatic failover with tools like Patroni or ProxySQL
- Regular backups of database

**AWS SQS:**
- Multi-region replication (manual setup)
- Automatic failover within region
- Built-in redundancy

**RabbitMQ:**
- Use clustered RabbitMQ for high availability
- Configure mirrored queues
- Use federation for multi-datacenter setups

### Cost Optimization

**AWS SQS:**
- Minimize empty receives (use long polling)
- Batch operations when possible
- Delete messages promptly after processing
- Use standard queues unless FIFO required

**All Drivers:**
- **⚠️ Configure `visibility_timeout` properly** - See [Configuration - Visibility Timeout Warning](configuration.md#visibility-timeout-warning)
- Clean up completed tasks if not needed
- Monitor and optimize task payload sizes
- Use task-level delays instead of polling

---

## See Also

- **[Configuration Guide](configuration.md)** - Driver configuration structure, init() patterns, and configuration contexts
- **[Environment Variables](environment-variables.md)** - Environment variable formats for all drivers
- **[Running Workers](running-workers.md)** - Worker deployment patterns, CLI options, and production configurations
- **[Best Practices](best-practices.md)** - Queue organization, performance tuning, and production deployment strategies

This documentation covers all aspects of AsyncTasQ queue drivers. All examples are tested and production-ready. For driver-specific issues, refer to the underlying library documentation (redis-py, asyncpg, asyncmy, aioboto3, aio-pika).
