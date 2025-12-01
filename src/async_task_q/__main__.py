"""CLI entry point for async-task-q.

Async Task Q provides a command-line interface for managing task queues and workers.

Commands:
    worker       Start a worker to process tasks from queues
    migrate      Initialize database schema for PostgreSQL or MySQL driver

Usage:
    python -m async_task_q <command> [OPTIONS]

Examples:
    # Start a worker with default settings
    python -m async_task_q worker

    # Start a worker with specific queues and concurrency
    python -m async_task_q worker --queues high-priority,default,low-priority --concurrency 20

    # Start a worker with Redis driver
    python -m async_task_q worker --driver redis --redis-url redis://localhost:6379

    # Initialize PostgreSQL schema
    python -m async_task_q migrate --postgres-dsn postgresql://user:pass@localhost/dbname

Worker Command:
    Start a worker to process tasks from queues.

    Usage:
        python -m async_task_q worker [OPTIONS]

    Options:
        --driver DRIVER
            Queue driver to use. Choices: redis, sqs, postgres, mysql
            Default: from async_task_q_DRIVER env var or 'redis'

        --queues QUEUES
            Comma-separated list of queue names to process in priority order
            (first queue has highest priority)
            Default: 'default'

        --concurrency N
            Maximum number of concurrent tasks to process
            Default: 10

        Redis Options:
            --redis-url URL
                Redis connection URL
                Default: from async_task_q_REDIS_URL env var or 'redis://localhost:6379'

            --redis-password PASSWORD
                Redis password
                Default: from async_task_q_REDIS_PASSWORD env var

            --redis-db N
                Redis database number (0-15)
                Default: from async_task_q_REDIS_DB env var or 0

            --redis-max-connections N
                Redis max connections in pool
                Default: from async_task_q_REDIS_MAX_CONNECTIONS env var or 10

        PostgreSQL Options:
            --postgres-dsn DSN
                PostgreSQL connection DSN
                Default: from async_task_q_POSTGRES_DSN env var or
                'postgresql://test:test@localhost:5432/test_db'

            --postgres-queue-table TABLE
                PostgreSQL queue table name
                Default: from async_task_q_POSTGRES_QUEUE_TABLE env var or 'task_queue'

            --postgres-dead-letter-table TABLE
                PostgreSQL dead letter table name
                Default: from async_task_q_POSTGRES_DEAD_LETTER_TABLE env var or
                'dead_letter_queue'

        MySQL Options:
            --mysql-dsn DSN
                MySQL connection DSN
                Default: from async_task_q_MYSQL_DSN env var or
                'mysql://test:test@localhost:3306/test_db'

            --mysql-queue-table TABLE
                MySQL queue table name
                Default: from async_task_q_MYSQL_QUEUE_TABLE env var or 'task_queue'

            --mysql-dead-letter-table TABLE
                MySQL dead letter table name
                Default: from async_task_q_MYSQL_DEAD_LETTER_TABLE env var or
                'dead_letter_queue'

        SQS Options:
            --sqs-region REGION
                AWS SQS region
                Default: from async_task_q_SQS_REGION env var or 'us-east-1'

            --sqs-queue-url-prefix PREFIX
                SQS queue URL prefix
                Default: from async_task_q_SQS_QUEUE_PREFIX env var

            --aws-access-key-id KEY
                AWS access key ID
                Default: from AWS_ACCESS_KEY_ID env var

            --aws-secret-access-key SECRET
                AWS secret access key
                Default: from AWS_SECRET_ACCESS_KEY env var

    Examples:
        # Basic usage with default settings
        python -m async_task_q worker

        # Multiple queues with priority order
        python -m async_task_q worker --queues high,default,low --concurrency 20

        # Redis with authentication
        python -m async_task_q worker \\
            --driver redis \\
            --redis-url redis://localhost:6379 \\
            --redis-password secret \\
            --redis-db 1

        # PostgreSQL with custom configuration
        python -m async_task_q worker \\
            --driver postgres \\
            --postgres-dsn postgresql://user:pass@localhost/dbname \\
            --postgres-queue-table my_queue \\
            --queues default,emails \\
            --concurrency 15

        # MySQL with custom configuration
        python -m async_task_q worker \\
            --driver mysql \\
            --mysql-dsn mysql://user:pass@localhost:3306/dbname \\
            --mysql-queue-table my_queue \\
            --queues default,emails \\
            --concurrency 15

        # SQS with custom region
        python -m async_task_q worker \\
            --driver sqs \\
            --sqs-region us-west-2 \\
            --sqs-queue-url-prefix https://sqs.us-west-2.amazonaws.com/123456789/ \\
            --queues default \\
            --concurrency 10

Migrate Command:
    Initialize database schema for PostgreSQL or MySQL driver.

    This command creates the necessary tables and indexes in PostgreSQL or MySQL
    for the task queue system. It works with both PostgreSQL and MySQL drivers.

    Usage:
        python -m async_task_q migrate [OPTIONS]

    Options:
        --driver DRIVER
            Queue driver (must be 'postgres' or 'mysql' for migrate command)
            Default: 'postgres'

        --postgres-dsn DSN
            PostgreSQL connection DSN
            Default: from async_task_q_POSTGRES_DSN env var or
            'postgresql://test:test@localhost:5432/test_db'

        --postgres-queue-table TABLE
            PostgreSQL queue table name
            Default: from async_task_q_POSTGRES_QUEUE_TABLE env var or 'task_queue'

        --postgres-dead-letter-table TABLE
            PostgreSQL dead letter table name
            Default: from async_task_q_POSTGRES_DEAD_LETTER_TABLE env var or
            'dead_letter_queue'

        --mysql-dsn DSN
            MySQL connection DSN
            Default: from async_task_q_MYSQL_DSN env var or
            'mysql://test:test@localhost:3306/test_db'

        --mysql-queue-table TABLE
            MySQL queue table name
            Default: from async_task_q_MYSQL_QUEUE_TABLE env var or 'task_queue'

        --mysql-dead-letter-table TABLE
            MySQL dead letter table name
            Default: from async_task_q_MYSQL_DEAD_LETTER_TABLE env var or
            'dead_letter_queue'

    Examples:
        # Basic migration with default settings
        python -m async_task_q migrate

        # Migration with custom DSN
        python -m async_task_q migrate \\
            --postgres-dsn postgresql://user:pass@localhost:5432/mydb

        # Migration with custom table names
        python -m async_task_q migrate \\
            --postgres-dsn postgresql://user:pass@localhost:5432/mydb \\
            --postgres-queue-table my_task_queue \\
            --postgres-dead-letter-table my_dlq

        # MySQL migration
        python -m async_task_q migrate \\
            --driver mysql \\
            --mysql-dsn mysql://user:pass@localhost:3306/mydb

        # MySQL migration with custom table names
        python -m async_task_q migrate \\
            --driver mysql \\
            --mysql-dsn mysql://user:pass@localhost:3306/mydb \\
            --mysql-queue-table my_task_queue \\
            --mysql-dead-letter-table my_dlq

Environment Variables:
    All configuration options can be set via environment variables. CLI arguments
    take precedence over environment variables.

    General:
        async_task_q_DRIVER              Queue driver (redis, postgres, mysql, sqs)
        async_task_q_DEFAULT_QUEUE       Default queue name

    Redis:
        async_task_q_REDIS_URL           Redis connection URL
        async_task_q_REDIS_PASSWORD      Redis password
        async_task_q_REDIS_DB            Redis database number
        async_task_q_REDIS_MAX_CONNECTIONS  Redis max connections

    PostgreSQL:
        async_task_q_POSTGRES_DSN        PostgreSQL connection DSN
        async_task_q_POSTGRES_QUEUE_TABLE  Queue table name
        async_task_q_POSTGRES_DEAD_LETTER_TABLE  Dead letter table name

    MySQL:
        async_task_q_MYSQL_DSN           MySQL connection DSN
        async_task_q_MYSQL_QUEUE_TABLE   Queue table name
        async_task_q_MYSQL_DEAD_LETTER_TABLE  Dead letter table name

    SQS:
        async_task_q_SQS_REGION          AWS region
        async_task_q_SQS_QUEUE_PREFIX    SQS queue URL prefix
        AWS_ACCESS_KEY_ID              AWS access key ID
        AWS_SECRET_ACCESS_KEY          AWS secret access key

Exit Codes:
    0   Success
    1   Error (command failed, migration error, etc.)

See Also:
    README.md for detailed documentation and examples
"""

from .cli import main

if __name__ == "__main__":
    main()
