#!/bin/bash
# restore_to_lib.sh - Restore backup file to lib table
# Usage: restore_to_lib.sh <table>

set -e -o pipefail

# Load configuration
CONFIG_FILE="$(dirname "$0")/tables.conf"
#: "${FLIBUSTA_DB_DIR:=$HOME/flbst-bot-mdb/db_init}"
: "${FLIBUSTA_DB_DIR:=$(cd "$(dirname "$0")/.." && pwd)}"
DB_DIR="$FLIBUSTA_DB_DIR"
SQL_DIR="$DB_DIR/sql"

# Environment variables with defaults
: "${FLIBUSTA_DB_CONTAINER:=flibusta-db}"
: "${FLIBUSTA_DB_USER:=flibusta}"
: "${FLIBUSTA_DB_PASS:=flibusta}"
: "${FLIBUSTA_DB_NAME:=flibusta}"

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

# Check if file exists
cd "$SQL_DIR"
if [ ! -f "$FILENAME" ]; then
    echo "Error: Backup file $FILENAME not found in $SQL_DIR"
    exit 1
fi

# Restore to lib table
#echo "Restoring $FILENAME to lib_$TABLE table..."
if gunzip -c "$FILENAME" 2>/dev/null | docker exec -i "$FLIBUSTA_DB_CONTAINER" mariadb -u "$FLIBUSTA_DB_USER" -p"$FLIBUSTA_DB_PASS" "$FLIBUSTA_DB_NAME"; then
    echo "✅ Restored $FILENAME to lib_$TABLE successfully"
else
    echo "❌ Failed to restore $FILENAME to lib_$TABLE"
    exit 1
fi