#!/bin/bash
# Helper script to create custom MySQL queue schema with custom table names
# Usage: ./create-custom-schema.sh <queue_table_name> <dead_letter_table_name>
# Example: ./create-custom-schema.sh my_queue my_dlq
#
# NOTE: This script is meant to be run manually when you need custom table names.
# It will exit silently if run during Docker initialization without arguments.

set -e

# Exit silently if being run during Docker init without arguments
# This prevents auto-execution during container startup
if [ $# -eq 0 ] && [ -z "$RUN_DURING_INIT" ]; then
    exit 0
fi

QUEUE_TABLE="${1:-task_queue}"
DLQ_TABLE="${2:-dead_letter_queue}"
DB_USER="${3:-test}"

# ANSI color codes
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${BLUE}Creating custom MySQL schema...${NC}"
echo -e "${BLUE}  Queue Table: ${QUEUE_TABLE}${NC}"
echo -e "${BLUE}  Dead Letter Table: ${DLQ_TABLE}${NC}"
echo -e "${BLUE}  Database User: ${DB_USER}${NC}"
echo ""

# Generate SQL
SQL=$(cat <<EOF
-- Custom Schema Creation for asynctasq Queue System
-- Queue Table: ${QUEUE_TABLE}
-- Dead Letter Table: ${DLQ_TABLE}

-- Create queue table
CREATE TABLE IF NOT EXISTS ${QUEUE_TABLE} (
    id INT AUTO_INCREMENT PRIMARY KEY,
    queue_name VARCHAR(255) NOT NULL,
    payload BLOB NOT NULL,
    available_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
    locked_until DATETIME(6) NULL,
    status VARCHAR(50) NOT NULL DEFAULT 'pending',
    attempts INT NOT NULL DEFAULT 0,
    max_attempts INT NOT NULL DEFAULT 3,
    created_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
    updated_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6) ON UPDATE CURRENT_TIMESTAMP(6),
    INDEX idx_${QUEUE_TABLE}_lookup (queue_name, status, available_at, locked_until)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Create dead letter queue table
CREATE TABLE IF NOT EXISTS ${DLQ_TABLE} (
    id INT AUTO_INCREMENT PRIMARY KEY,
    queue_name VARCHAR(255) NOT NULL,
    payload BLOB NOT NULL,
    attempts INT NOT NULL,
    error_message TEXT,
    failed_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Grant permissions
GRANT ALL PRIVILEGES ON test_db.${QUEUE_TABLE} TO '${DB_USER}'@'%';
GRANT ALL PRIVILEGES ON test_db.${DLQ_TABLE} TO '${DB_USER}'@'%';
FLUSH PRIVILEGES;
EOF
)

# Check if we're running inside Docker container or from host
if [ -n "$MYSQL_HOST" ]; then
    # Running from host - connect to Docker container
    mysql \
        -h "${MYSQL_HOST:-localhost}" \
        -P "${MYSQL_PORT:-3306}" \
        -u "${DB_USER}" \
        -p"${MYSQL_PASSWORD:-test}" \
        "${MYSQL_DATABASE:-test_db}" \
        -e "$SQL"
else
    # Running inside container - use local connection
    mysql -u "${DB_USER}" -p"${MYSQL_PASSWORD:-test}" "${MYSQL_DATABASE:-test_db}" -e "$SQL"
fi

echo ""
echo -e "${GREEN}✓ Custom schema created successfully!${NC}"
echo -e "${GREEN}  - Created table: ${QUEUE_TABLE}${NC}"
echo -e "${GREEN}  - Created index: idx_${QUEUE_TABLE}_lookup${NC}"
echo -e "${GREEN}  - Created table: ${DLQ_TABLE}${NC}"
echo -e "${GREEN}  - Granted permissions to user: ${DB_USER}${NC}"
echo ""
echo -e "${YELLOW}Usage in Python:${NC}"
echo -e "${YELLOW}driver = MySQLDriver(${NC}"
echo -e "${YELLOW}    dsn='mysql://test:test@localhost:3306/test_db',${NC}"
echo -e "${YELLOW}    queue_table='${QUEUE_TABLE}',${NC}"
echo -e "${YELLOW}    dead_letter_table='${DLQ_TABLE}'${NC}"
echo -e "${YELLOW})${NC}"
