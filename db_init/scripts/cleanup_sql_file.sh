#!/bin/bash
# cleanup_sql_file.sh - Cleanup SQL file for specified table
# Usage: cleanup_sql_file.sh <table>

set -e -o pipefail

# Load configuration
CONFIG_FILE="$(dirname "$0")/tables.conf"
: "${FLIBUSTA_DB_DIR:=$(cd "$(dirname "$0")/.." && pwd)}"
DB_DIR="$FLIBUSTA_DB_DIR"
SQL_DIR="$DB_DIR/sql"

# Validate input
if [ $# -ne 1 ]; then
    echo "Usage: $0 <table>"
    exit 1
fi

TABLE="$1"

# Get filename from config
if [ ! -f "$CONFIG_FILE" ]; then
    echo "Error: Config file $CONFIG_FILE not found"
    exit 1
fi

FILENAME=$(grep "^$TABLE=" "$CONFIG_FILE" | cut -d= -f2)
if [ -z "$FILENAME" ]; then
    echo "Error: Table $TABLE not found in config"
    exit 1
fi

# Cleanup file
cd "$SQL_DIR"
if [ -f "$FILENAME" ]; then
#    echo "Cleaning up $FILENAME..."
    rm -f "$FILENAME"
    echo "✅ Cleaned up $FILENAME"
else
    echo "✅ No file $FILENAME to clean up"
fi