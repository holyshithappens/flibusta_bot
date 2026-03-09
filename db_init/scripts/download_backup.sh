#!/bin/bash
# download_backup.sh - Download backup file for specified table
# Usage: download_backup.sh <table>

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
: "${FLIBUSTA_SQL_URL_BASE:=https://flibusta.is/sql/}"

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

# Create SQL directory
mkdir -p "$SQL_DIR"
cd "$SQL_DIR"

# Download file
URL="${FLIBUSTA_SQL_URL_BASE}${FILENAME}"
#echo "Downloading $FILENAME for table $TABLE..."
if wget -c -q -O "$FILENAME" "$URL" 2>/dev/null; then
    echo "✅ Downloaded $FILENAME successfully"
else
    echo "❌ Failed to download $FILENAME"
    exit 1
fi