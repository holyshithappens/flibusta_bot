#!/bin/bash
# update_all_tables.sh - Full all-tables update workflow
# This script processes all tables/files defined in tables.conf using atomic scripts

set -e -o pipefail

# Configuration
#: "${FLIBUSTA_DB_DIR:=$HOME/flbst-bot-mdb/db_init}"
: "${FLIBUSTA_DB_DIR:=$(cd "$(dirname "$0")/.." && pwd)}"
DB_DIR="$FLIBUSTA_DB_DIR"
SQL_DIR="$DB_DIR/sql"
#SCRIPTS_DIR="$(dirname "$0")"

# Environment variables with defaults
: "${FLIBUSTA_DB_CONTAINER:=flibusta-db}"
: "${FLIBUSTA_DB_USER:=flibusta}"
: "${FLIBUSTA_DB_PASS:=flibusta}"
: "${FLIBUSTA_DB_NAME:=flibusta}"
#: "${FLIBUSTA_SQL_URL_BASE:=https://flibusta.is/sql/}"

## SQL execution utility
#_run_sql() {
#    echo "Executing SQL: $1"
#    docker exec -i "$FLIBUSTA_DB_CONTAINER" mariadb -u "$FLIBUSTA_DB_USER" -p"$FLIBUSTA_DB_PASS" "$FLIBUSTA_DB_NAME" <<< "$1"
#}

# Function to execute SQL script file
_run_sql_file() {
    local script_name=$(basename "$1")
    echo "Executing SQL script: $script_name"
    docker exec -i "$FLIBUSTA_DB_CONTAINER" mariadb -u "$FLIBUSTA_DB_USER" -p"$FLIBUSTA_DB_PASS" "$FLIBUSTA_DB_NAME" < "$1"
    echo "Completed SQL script: $script_name"
}

# === Task Functions ===


rollback_cb_tables() {
    echo "🚀 Starting task: Rollback tables..."

    local success_count=0
    local total_count=0

    # Process tables from tables.conf using atomic scripts
    while IFS='=' read -r table filename; do
        # Skip comments and empty lines
        [[ "$table" =~ ^#.*$ ]] && continue
        [[ -z "$table" ]] && continue

        total_count=$((total_count + 1))

        # Rename cb_<table> to <table> (rollback)
        "$DB_DIR/scripts/rename_table.sh" "cb_${table}" "${table}"

        # Rename cb_<table>_old to cb_<table> (rollback)
        "$DB_DIR/scripts/rename_table.sh" "cb_${table}_old" "cb_${table}"

        success_count=$((success_count + 1))
    done < "$DB_DIR/scripts/tables.conf"

    echo "✅ Task completed: Rolled back $success_count/$total_count tables"
}

# === Main Execution ===
main() {
    echo "🔄 Starting DB Rollback Process"

    # Task 1: Rollback all tables
    rollback_cb_tables

    echo "🎉 All tasks completed successfully!"
    echo "📊 Final database statistics:"
    if [ -f "$DB_DIR/zz_56_db_statistics.sql" ]; then
        _run_sql_file "$DB_DIR/zz_56_db_statistics.sql"
    else
        echo "ℹ️  Statistics script not found"
    fi
}

# Run main function
main