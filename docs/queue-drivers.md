# Queue Drivers

Async Task supports four production-ready queue drivers with identical APIs.

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
uv add "async-task[redis]"

# With pip
pip install "async-task[redis]"
```

**Configuration:**

```bash
# Environment variables
export ASYNC_TASK_DRIVER=redis
export ASYNC_TASK_REDIS_URL=redis://localhost:6379
export ASYNC_TASK_REDIS_PASSWORD=secret  # Optional
export ASYNC_TASK_REDIS_DB=0
export ASYNC_TASK_REDIS_MAX_CONNECTIONS=10
```

```python
# Programmatic configuration
from async_task.config import set_global_config

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
uv add "async-task[postgres]"

# With pip
pip install "async-task[postgres]"
```

**Configuration:**

```bash
# Environment variables
export ASYNC_TASK_DRIVER=postgres
export ASYNC_TASK_POSTGRES_DSN=postgresql://user:pass@localhost:5432/dbname
export ASYNC_TASK_POSTGRES_QUEUE_TABLE=task_queue
export ASYNC_TASK_POSTGRES_DEAD_LETTER_TABLE=dead_letter_queue
export ASYNC_TASK_POSTGRES_MAX_ATTEMPTS=3
export ASYNC_TASK_POSTGRES_RETRY_DELAY_SECONDS=60
export ASYNC_TASK_POSTGRES_VISIBILITY_TIMEOUT_SECONDS=300
export ASYNC_TASK_POSTGRES_MIN_POOL_SIZE=10
export ASYNC_TASK_POSTGRES_MAX_POOL_SIZE=10
```

```python
# Programmatic configuration
from async_task.config import set_global_config

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
python -m async_task migrate --driver postgres --postgres-dsn postgresql://user:pass@localhost/dbname

# Or with uv
uv run python -m async_task migrate --driver postgres --postgres-dsn postgresql://user:pass@localhost/dbname
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
uv add "async-task[mysql]"

# With pip
pip install "async-task[mysql]"
```

**Configuration:**

```bash
# Environment variables
export ASYNC_TASK_DRIVER=mysql
export ASYNC_TASK_MYSQL_DSN=mysql://user:pass@localhost:3306/dbname
export ASYNC_TASK_MYSQL_QUEUE_TABLE=task_queue
export ASYNC_TASK_MYSQL_DEAD_LETTER_TABLE=dead_letter_queue
export ASYNC_TASK_MYSQL_MAX_ATTEMPTS=3
export ASYNC_TASK_MYSQL_RETRY_DELAY_SECONDS=60
export ASYNC_TASK_MYSQL_VISIBILITY_TIMEOUT_SECONDS=300
export ASYNC_TASK_MYSQL_MIN_POOL_SIZE=10
export ASYNC_TASK_MYSQL_MAX_POOL_SIZE=10
```

```python
# Programmatic configuration
from async_task.config import set_global_config

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
python -m async_task migrate --driver mysql --mysql-dsn mysql://user:pass@localhost:3306/dbname

# Or with uv
uv run python -m async_task migrate --driver mysql --mysql-dsn mysql://user:pass@localhost:3306/dbname
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
uv add "async-task[sqs]"

# With pip
pip install "async-task[sqs]"
```

**Configuration:**

```bash
# Environment variables
export ASYNC_TASK_DRIVER=sqs
export ASYNC_TASK_SQS_REGION=us-east-1
export ASYNC_TASK_SQS_QUEUE_PREFIX=https://sqs.us-east-1.amazonaws.com/123456789/
export AWS_ACCESS_KEY_ID=your_access_key
export AWS_SECRET_ACCESS_KEY=your_secret_key
```

```python
# Programmatic configuration
from async_task.config import set_global_config

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

## Driver Comparison

| Driver         | Best For       | Pros                                          | Cons                           | Requirements   |
| -------------- | -------------- | --------------------------------------------- | ------------------------------ | -------------- |
| **Redis**      | Production     | Fast, reliable, distributed, mature           | Requires Redis server          | Redis 6.2+     |
| **PostgreSQL** | Enterprise     | ACID, DLQ, visibility timeout, transactions   | Requires PostgreSQL setup      | PostgreSQL 14+ |
| **MySQL**      | Enterprise     | ACID, DLQ, visibility timeout, transactions   | Requires MySQL setup           | MySQL 8.0+     |
| **SQS**        | AWS/Serverless | Managed, auto-scaling, zero ops, multi-region | AWS-specific, cost per message | AWS account    |

**Recommendation:**

- **Production (general):** Use `redis` for most applications
- **Production (enterprise):** Use `postgres` or `mysql` if you need ACID guarantees
- **AWS/Cloud-native:** Use `sqs` for managed infrastructure
