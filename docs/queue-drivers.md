# Queue Drivers

## Table of Contents

- [Queue Drivers](#queue-drivers)
  - [Table of Contents](#table-of-contents)
  - [Redis Driver](#redis-driver)
  - [PostgreSQL Driver](#postgresql-driver)
  - [MySQL Driver](#mysql-driver)
  - [AWS SQS Driver](#aws-sqs-driver)
  - [RabbitMQ Driver](#rabbitmq-driver)
  - [Driver Comparison](#driver-comparison)

AsyncTasQ supports five production-ready queue drivers with identical APIs.

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
# Programmatic configuration
from asynctasq import init, RedisConfig

init({
    'driver': 'redis',
    'redis': RedisConfig(
        url='redis://localhost:6379',
        password='secret',  # Optional
        db=0,
        max_connections=100
    )
})
```

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
# Programmatic configuration
from asynctasq import init, PostgresConfig

init({
    'driver': 'postgres',
    'postgres': PostgresConfig(
        dsn='postgresql://user:pass@localhost:5432/dbname',
        queue_table='task_queue',
        dead_letter_table='dead_letter_queue',
        max_attempts=3,
        min_pool_size=10,
        max_pool_size=10
    )
})
```

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
# Programmatic configuration
from asynctasq import init, MySQLConfig

init({
    'driver': 'mysql',
    'mysql': MySQLConfig(
        dsn='mysql://user:pass@localhost:3306/dbname',
        queue_table='task_queue',
        dead_letter_table='dead_letter_queue',
        max_attempts=3,
        min_pool_size=10,
        max_pool_size=10
    )
})
```

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
# Programmatic configuration
from asynctasq import init, SQSConfig

init({
    'driver': 'sqs',
    'sqs': SQSConfig(
        region='us-east-1',
        queue_url_prefix='https://sqs.us-east-1.amazonaws.com/123456789/',
        aws_access_key_id='your_access_key',     # Optional (uses AWS credentials chain)
        aws_secret_access_key='your_secret_key'  # Optional
    )
})
```

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
# Programmatic configuration
from asynctasq import init, RabbitMQConfig

init({
    'driver': 'rabbitmq',
    'rabbitmq': RabbitMQConfig(
        url='amqp://user:pass@localhost:5672/',
        exchange_name='asynctasq',
        prefetch_count=1
    )
})
```

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
