#!/bin/bash
# Helper script to create ORM test tables in MySQL
# Usage: ./create-orm-tables.sh
#
# NOTE: This script is meant to be run manually when you need to recreate ORM tables.
# It will exit silently if run during Docker initialization without arguments.

set -e

# Exit silently if being run during Docker init without arguments
# This prevents auto-execution during container startup
if [ $# -eq 0 ] && [ -z "$RUN_DURING_INIT" ]; then
    exit 0
fi

DB_USER="${1:-test}"

# ANSI color codes
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${BLUE}Creating ORM test tables in MySQL...${NC}"
echo -e "${BLUE}  Database User: ${DB_USER}${NC}"
echo ""

# Read SQL from the migration file
SQL_FILE="$(dirname "$0")/02-create-orm-tables.sql"
if [ ! -f "$SQL_FILE" ]; then
    echo -e "${YELLOW}Warning: SQL file not found: ${SQL_FILE}${NC}"
    exit 1
fi

SQL=$(cat "$SQL_FILE")

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
echo -e "${GREEN}✓ ORM test tables created successfully!${NC}"
echo -e "${GREEN}  - Created SQLAlchemy tables: sqlalchemy_test_users, sqlalchemy_test_user_sessions${NC}"
echo -e "${GREEN}  - Created Django table: django_test_products${NC}"
echo -e "${GREEN}  - Created Tortoise table: tortoise_test_orders${NC}"
echo -e "${GREEN}  - Granted permissions to user: ${DB_USER}${NC}"

