#!/bin/bash
# update_single_table.sh - Update single table workflow
# Usage: update_single_table.sh <table>

set -e -o pipefail

# Environment variables with defaults
#: "${FLIBUSTA_DB_DIR:=$HOME/flbst-bot-mdb/db_init}"
: "${FLIBUSTA_DB_DIR:=$(cd "$(dirname "$0")/.." && pwd)}"
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
#SCRIPT_DIR="$(dirname "$0")"
SCRIPT_DIR="$FLIBUSTA_DB_DIR/scripts"

echo "🔄 Starting single table update for: $TABLE"

# Step 1: Cleanup .sql.gz file for this table
echo "🧹 Step 1: Cleanup SQL file..."
"$SCRIPT_DIR/cleanup_sql_file.sh" "$TABLE"

# Step 2: Drop cb_<table>_old (safe if missing)
echo "🗑️ Step 2: Drop old backup table..."
"$SCRIPT_DIR/drop_old_table.sh" "cb_${TABLE}_old"

# Step 3: Download .sql.gz using tables.conf
echo "📥 Step 3: Download backup..."
"$SCRIPT_DIR/download_backup.sh" "$TABLE"

# Step 4: Restore into lib<table>
echo "💾 Step 4: Restore to lib table..."
"$SCRIPT_DIR/restore_to_lib.sh" "$TABLE"

# Step 5: Rename cb_<table> → cb_<table>_old
echo "🔄 Step 5: Rename cb_${TABLE} to cb_${TABLE}_old..."
"$SCRIPT_DIR/rename_table.sh" "cb_${TABLE}" "cb_${TABLE}_old"

# Step 6: Rename <table> → cb_<table> (table is already lib*)
echo "🔄 Step 6: Rename ${TABLE} to cb_${TABLE}..."
"$SCRIPT_DIR/rename_table.sh" "${TABLE}" "cb_${TABLE}"

echo "✅ Single table update completed successfully for: $TABLE"