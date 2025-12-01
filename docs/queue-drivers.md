# Queue Drivers

Q Task supports five production-ready queue drivers with identical APIs.

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
uv add "q-task[redis]"

# With pip
pip install "q-task[redis]"
```

**Configuration:**

```bash
# Environment variables
export q_task_DRIVER=redis
export q_task_REDIS_URL=redis://localhost:6379
export q_task_REDIS_PASSWORD=secret  # Optional
export q_task_REDIS_DB=0
export q_task_REDIS_MAX_CONNECTIONS=10
```

```python
# Programmatic configuration
from q_task.config import set_global_config

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
uv add "q-task[postgres]"

# With pip
pip install "q-task[postgres]"
```

**Configuration:**

```bash
# Environment variables
export q_task_DRIVER=postgres
export q_task_POSTGRES_DSN=postgresql://user:pass@localhost:5432/dbname
export q_task_POSTGRES_QUEUE_TABLE=task_queue
export q_task_POSTGRES_DEAD_LETTER_TABLE=dead_letter_queue
export q_task_POSTGRES_MAX_ATTEMPTS=3
export q_task_POSTGRES_RETRY_DELAY_SECONDS=60
export q_task_POSTGRES_VISIBILITY_TIMEOUT_SECONDS=300
export q_task_POSTGRES_MIN_POOL_SIZE=10
export q_task_POSTGRES_MAX_POOL_SIZE=10
```

```python
# Programmatic configuration
from q_task.config import set_global_config

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
python -m q_task migrate --driver postgres --postgres-dsn postgresql://user:pass@localhost/dbname

# Or with uv
uv run python -m q_task migrate --driver postgres --postgres-dsn postgresql://user:pass@localhost/dbname
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
uv add "q-task[mysql]"

# With pip
pip install "q-task[mysql]"
```

**Configuration:**

```bash
# Environment variables
export q_task_DRIVER=mysql
export q_task_MYSQL_DSN=mysql://user:pass@localhost:3306/dbname
export q_task_MYSQL_QUEUE_TABLE=task_queue
export q_task_MYSQL_DEAD_LETTER_TABLE=dead_letter_queue
export q_task_MYSQL_MAX_ATTEMPTS=3
export q_task_MYSQL_RETRY_DELAY_SECONDS=60
export q_task_MYSQL_VISIBILITY_TIMEOUT_SECONDS=300
export q_task_MYSQL_MIN_POOL_SIZE=10
export q_task_MYSQL_MAX_POOL_SIZE=10
```

```python
# Programmatic configuration
from q_task.config import set_global_config

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
python -m q_task migrate --driver mysql --mysql-dsn mysql://user:pass@localhost:3306/dbname

# Or with uv
uv run python -m q_task migrate --driver mysql --mysql-dsn mysql://user:pass@localhost:3306/dbname
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
uv add "q-task[sqs]"

# With pip
pip install "q-task[sqs]"
```

**Configuration:**

```bash
# Environment variables
export q_task_DRIVER=sqs
export q_task_SQS_REGION=us-east-1
export q_task_SQS_QUEUE_PREFIX=https://sqs.us-east-1.amazonaws.com/123456789/
export AWS_ACCESS_KEY_ID=your_access_key
export AWS_SECRET_ACCESS_KEY=your_secret_key
```

```python
# Programmatic configuration
from q_task.config import set_global_config

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
uv add "q-task[rabbitmq]"

# With pip
pip install "q-task[rabbitmq]"
```

**Configuration:**

```bash
# Environment variables
export q_task_DRIVER=rabbitmq
export q_task_RABBITMQ_URL=amqp://guest:guest@localhost:5672/
export q_task_RABBITMQ_EXCHANGE_NAME=q_task
export q_task_RABBITMQ_PREFETCH_COUNT=1
```

```python
# Programmatic configuration
from q_task.config import set_global_config

set_global_config(
    driver='rabbitmq',
    rabbitmq_url='amqp://user:pass@localhost:5672/',
    rabbitmq_exchange_name='q_task',
    rabbitmq_prefetch_count=1
)
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
