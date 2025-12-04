#!/bin/bash
# Helper script to create custom PostgreSQL queue schema with custom table names
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

echo -e "${BLUE}Creating custom PostgreSQL schema...${NC}"
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
    id SERIAL PRIMARY KEY,
    queue_name TEXT NOT NULL,
    payload BYTEA NOT NULL,
    available_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    locked_until TIMESTAMPTZ,
    status TEXT NOT NULL DEFAULT 'pending',
    attempts INTEGER NOT NULL DEFAULT 0,
    max_attempts INTEGER NOT NULL DEFAULT 3,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Create index for efficient queue lookup
-- Composite index on queue_name, status, available_at, and locked_until
CREATE INDEX IF NOT EXISTS idx_${QUEUE_TABLE}_lookup
ON ${QUEUE_TABLE} (queue_name, status, available_at, locked_until);

-- Create dead letter queue table
CREATE TABLE IF NOT EXISTS ${DLQ_TABLE} (
    id SERIAL PRIMARY KEY,
    queue_name TEXT NOT NULL,
    payload BYTEA NOT NULL,
    attempts INTEGER NOT NULL,
    error_message TEXT,
    failed_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Grant permissions
GRANT ALL PRIVILEGES ON TABLE ${QUEUE_TABLE} TO ${DB_USER};
GRANT ALL PRIVILEGES ON TABLE ${DLQ_TABLE} TO ${DB_USER};
GRANT ALL PRIVILEGES ON SEQUENCE ${QUEUE_TABLE}_id_seq TO ${DB_USER};
GRANT ALL PRIVILEGES ON SEQUENCE ${DLQ_TABLE}_id_seq TO ${DB_USER};
EOF
)

# Check if we're running inside Docker container or from host
if [ -n "$POSTGRES_HOST" ]; then
    # Running from host - connect to Docker container
    PGPASSWORD="${POSTGRES_PASSWORD:-test}" psql \
        -h "${POSTGRES_HOST:-localhost}" \
        -p "${POSTGRES_PORT:-5432}" \
        -U "${DB_USER}" \
        -d "${POSTGRES_DB:-test_db}" \
        -c "$SQL"
else
    # Running inside container - use local connection
    psql -U "${DB_USER}" -d "${POSTGRES_DB:-test_db}" -c "$SQL"
fi

echo ""
echo -e "${GREEN}✓ Custom schema created successfully!${NC}"
echo -e "${GREEN}  - Created table: ${QUEUE_TABLE}${NC}"
echo -e "${GREEN}  - Created index: idx_${QUEUE_TABLE}_lookup${NC}"
echo -e "${GREEN}  - Created table: ${DLQ_TABLE}${NC}"
echo -e "${GREEN}  - Granted permissions to user: ${DB_USER}${NC}"
echo ""
echo -e "${YELLOW}Usage in Python:${NC}"
echo -e "${YELLOW}driver = PostgresDriver(${NC}"
echo -e "${YELLOW}    dsn='postgresql://test:test@localhost:5432/test_db',${NC}"
echo -e "${YELLOW}    queue_table='${QUEUE_TABLE}',${NC}"
echo -e "${YELLOW}    dead_letter_table='${DLQ_TABLE}'${NC}"
echo -e "${YELLOW})${NC}"
