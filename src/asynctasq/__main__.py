"""CLI entry point for asynctasq.

AsyncTasQ provides a command-line interface for managing task queues and workers.

Commands:
    worker       Start a worker to process tasks from queues
    migrate      Initialize database schema for PostgreSQL or MySQL driver

Usage:
    python -m asynctasq <command> [OPTIONS]

Examples:
    # Start a worker with default settings
    python -m asynctasq worker

    # Start a worker with specific queues and concurrency
    python -m asynctasq worker --queues high-priority,default,low-priority --concurrency 20

    # Start a worker with Redis driver
    python -m asynctasq worker --driver redis --redis-url redis://localhost:6379

    # Initialize PostgreSQL schema
    python -m asynctasq migrate --postgres-dsn postgresql://user:pass@localhost/dbname

Worker Command:
    Start a worker to process tasks from queues.

    Usage:
        python -m asynctasq worker [OPTIONS]

    Options:
        --driver DRIVER
            Queue driver to use. Choices: redis, sqs, postgres, mysql
            Default: 'redis'

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
                Default: 'redis://localhost:6379'

            --redis-password PASSWORD
                Redis password
                Default: None

            --redis-db N
                Redis database number (0-15)
                Default: 0

            --redis-max-connections N
                Redis max connections in pool
                Default: 100

        PostgreSQL Options:
            --postgres-dsn DSN
                PostgreSQL connection DSN
                Default: 'postgresql://test:test@localhost:5432/test_db'

            --postgres-queue-table TABLE
                PostgreSQL queue table name
                Default: 'task_queue'

            --postgres-dead-letter-table TABLE
                PostgreSQL dead letter table name
                Default: 'dead_letter_queue'

        MySQL Options:
            --mysql-dsn DSN
                MySQL connection DSN
                Default: 'mysql://test:test@localhost:3306/test_db'

            --mysql-queue-table TABLE
                MySQL queue table name
                Default: 'task_queue'

            --mysql-dead-letter-table TABLE
                MySQL dead letter table name
                Default: 'dead_letter_queue'

        SQS Options:
            --sqs-region REGION
                AWS SQS region
                Default: 'us-east-1'

            --sqs-queue-url-prefix PREFIX
                SQS queue URL prefix
                Default: None

            --aws-access-key-id KEY
                AWS access key ID
                Default: from AWS_ACCESS_KEY_ID env var

            --aws-secret-access-key SECRET
                AWS secret access key
                Default: from AWS_SECRET_ACCESS_KEY env var

    Examples:
        # Basic usage with default settings
        python -m asynctasq worker

        # Multiple queues with priority order
        python -m asynctasq worker --queues high,default,low --concurrency 20

        # Redis with authentication
        python -m asynctasq worker \\
            --driver redis \\
            --redis-url redis://localhost:6379 \\
            --redis-password secret \\
            --redis-db 1

        # PostgreSQL with custom configuration
        python -m asynctasq worker \\
            --driver postgres \\
            --postgres-dsn postgresql://user:pass@localhost/dbname \\
            --postgres-queue-table my_queue \\
            --queues default,emails \\
            --concurrency 15

        # MySQL with custom configuration
        python -m asynctasq worker \\
            --driver mysql \\
            --mysql-dsn mysql://user:pass@localhost:3306/dbname \\
            --mysql-queue-table my_queue \\
            --queues default,emails \\
            --concurrency 15

        # SQS with custom region
        python -m asynctasq worker \\
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
        python -m asynctasq migrate [OPTIONS]

    Options:
        --driver DRIVER
            Queue driver (must be 'postgres' or 'mysql' for migrate command)
            Default: 'postgres'

        --postgres-dsn DSN
            PostgreSQL connection DSN
            Default: 'postgresql://test:test@localhost:5432/test_db'

        --postgres-queue-table TABLE
            PostgreSQL queue table name
            Default: 'task_queue'

        --postgres-dead-letter-table TABLE
            PostgreSQL dead letter table name
            Default: 'dead_letter_queue'

        --mysql-dsn DSN
            MySQL connection DSN
            Default: 'mysql://test:test@localhost:3306/test_db'

        --mysql-queue-table TABLE
            MySQL queue table name
            Default: 'task_queue'

        --mysql-dead-letter-table TABLE
            MySQL dead letter table name
            Default: 'dead_letter_queue'

    Examples:
        # Basic migration with default settings
        python -m asynctasq migrate

        # Migration with custom DSN
        python -m asynctasq migrate \\
            --postgres-dsn postgresql://user:pass@localhost:5432/mydb

        # Migration with custom table names
        python -m asynctasq migrate \\
            --postgres-dsn postgresql://user:pass@localhost:5432/mydb \\
            --postgres-queue-table my_task_queue \\
            --postgres-dead-letter-table my_dlq

        # MySQL migration
        python -m asynctasq migrate \\
            --driver mysql \\
            --mysql-dsn mysql://user:pass@localhost:3306/mydb

        # MySQL migration with custom table names
        python -m asynctasq migrate \\
            --driver mysql \\
            --mysql-dsn mysql://user:pass@localhost:3306/mydb \\
            --mysql-queue-table my_task_queue \\
            --mysql-dead-letter-table my_dlq

Exit Codes:
    0   Success
    1   Error (command failed, migration error, etc.)

See Also:
    README.md for detailed documentation and examples
"""

from .cli import main

if __name__ == "__main__":
    main()
