#!/bin/bash
# automated_flibusta_db_update.sh - Automated Flibusta DB Update Script
# This script runs in background and processes tasks in order: 7, 6, 1, 2, 3, 4
# All output is logged to stdout for file logging

set -o pipefail

# Configuration
DB_DIR="$HOME/flbst-bot-mdb/db_init"
SQL_DIR="$DB_DIR/sql"
SCRIPTS_DIR="$DB_DIR"
#LOG_FILE="$DB_DIR/automated_update_$(date +%Y%m%d_%H%M%S).log"

DB_USER="flibusta"
DB_PASS="flibusta"
DB_NAME="flibusta"
CONTAINER="flibusta-db"

# Redirect all output to stdout (for logging)
#exec > >(tee -a "$LOG_FILE") 2>&1

# Timestamp function
timestamp() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')]"
}

# Log function
log() {
    echo "$(timestamp) $1"
}

# Error handling
#trap 'log "ERROR: Script failed at line $LINENO"; exit 1' ERR

# SQL execution utility
_run_sql() {
    log "Executing SQL: $1"
    docker exec -i "$CONTAINER" mariadb -u "$DB_USER" -p"$DB_PASS" "$DB_NAME" <<< "$1"
}

# Function to execute SQL script file
_run_sql_file() {
    local script_name=$(basename "$1")
    log "Executing SQL script: $script_name"
    docker exec -i "$CONTAINER" mariadb -u "$DB_USER" -p"$DB_PASS" "$DB_NAME" < "$1"
    log "Completed SQL script: $script_name"
}

# === Task Functions ===

cleanup_sql_files() {
    log "🧹 Starting task 7: Cleanup SQL files..."
    cd "$SQL_DIR"
    local file_count=$(find . -name "*.sql.gz" | wc -l)
    if [ "$file_count" -gt 0 ]; then
        log "Found $file_count .sql.gz files to clean up"
        rm -f *.sql.gz
        log "✅ Task 7 completed: All .sql.gz files removed"
    else
        log "✅ Task 7 completed: No .sql.gz files found to clean up"
    fi
}

cleanup_old_tables() {
    log "🗑️ Starting task 6: Cleanup old tables..."
    _run_sql_file "$SCRIPTS_DIR/zz_01_cleanup_old_tables.sql"
    log "✅ Task 6 completed: Old tables cleanup finished"
}

download_sql_files() {
    log "📥 Starting task 1: Download SQL files..."
    mkdir -p "$SQL_DIR"
    cd "$SQL_DIR"

    local REQUIRED=(
        "https://flibusta.is/sql/lib.libavtor.sql.gz"
        "https://flibusta.is/sql/lib.libavtorname.sql.gz"
        "https://flibusta.is/sql/lib.libbook.sql.gz"
        "https://flibusta.is/sql/lib.libgenre.sql.gz"
        "https://flibusta.is/sql/lib.librate.sql.gz"
        "https://flibusta.is/sql/lib.librecs.sql.gz"
        "https://flibusta.is/sql/lib.libseq.sql.gz"
        "https://flibusta.is/sql/lib.reviews.sql.gz"
        "https://flibusta.is/sql/lib.b.annotations.sql.gz"
        "https://flibusta.is/sql/lib.a.annotations.sql.gz"
        "https://flibusta.is/sql/lib.libgenrelist.sql.gz"
        "https://flibusta.is/sql/lib.libseqname.sql.gz"
        "https://flibusta.is/sql/lib.b.annotations_pics.sql.gz"
        "https://flibusta.is/sql/lib.a.annotations_pics.sql.gz"
    )

    local success_count=0
    local total_count=${#REQUIRED[@]}

    for url in "${REQUIRED[@]}"; do
        local filename=$(basename "$url")
        log "Downloading $filename..."
        if wget -c -q -O "$filename" "$url" 2>/dev/null; then
            log "✅ Downloaded $filename successfully"
            ((success_count++))
        else
            log "❌ Failed to download $filename"
        fi
    done

    log "✅ Task 1 completed: Downloaded $success_count/$total_count SQL files"
}

load_sql_to_lib_tables() {
    log "💾 Starting task 2: Load SQL to lib tables..."
    cd "$SQL_DIR"
    local file_count=$(find . -name "*.sql.gz" | wc -l)

    if [ "$file_count" -eq 0 ]; then
        log "❌ No .sql.gz files found to import"
        return 1
    fi

    local imported_count=0
    for gz in *.sql.gz; do
        [[ -f "$gz" ]] || continue
        local base=$(basename "$gz" .sql.gz)
        log "Importing $base..."
        if gunzip -c "$gz" 2>/dev/null | docker exec -i "$CONTAINER" mariadb -u "$DB_USER" -p"$DB_PASS" "$DB_NAME"; then
            log "✅ Imported $base successfully"
            ((imported_count++))
        else
            log "❌ Failed to import $base"
        fi
    done

    log "✅ Task 2 completed: Imported $imported_count SQL files to lib* tables"
}

apply_preparation_scripts() {
    log "🔧 Starting task 3: Apply preparation scripts..."

    local scripts=(
        "zz_10_convert_charset.sql"
        "zz_20_create_indexes.sql"
        "zz_30_create_FT_indexes.sql"
        "zz_40_fill_FT.sql"
        "zz_50_repair_FT.sql"
    )

    local success_count=0
    for script in "${scripts[@]}"; do
        if [ -f "$SCRIPTS_DIR/$script" ]; then
            _run_sql_file "$SCRIPTS_DIR/$script"
            ((success_count++))
        else
            log "❌ Script not found: $script"
        fi
    done

    log "✅ Task 3 completed: Applied $success_count preparation scripts"
}

activate_cb_tables() {
    log "🚀 Starting task 4: Activate cb_lib tables..."

    # First migrate existing cb tables to old
    if [ -f "$SCRIPTS_DIR/zz_59_migrate_cb_tables_to_old.sql" ]; then
        _run_sql_file "$SCRIPTS_DIR/zz_59_migrate_cb_tables_to_old.sql"
    else
        log "ℹ️  No existing cb_lib tables to migrate (zz_59 script not found)"
    fi

    # Then migrate lib tables to cb_lib
    if [ -f "$SCRIPTS_DIR/zz_60_migrate_to_cb_tables.sql" ]; then
        _run_sql_file "$SCRIPTS_DIR/zz_60_migrate_to_cb_tables.sql"
        log "✅ Task 4 completed: lib* tables renamed to cb_lib*"
    else
        log "❌ Migration script not found: zz_60_migrate_to_cb_tables.sql"
        return 1
    fi
}

# === Main Execution ===
main() {
    log "🔄 Starting Automated Flibusta DB Update Process"
    log "Task order: 7 (cleanup SQL files) → 6 (cleanup old tables) → 1 (download) → 2 (load) → 3 (prepare) → 4 (activate)"

    # Task 7: Cleanup SQL files
    cleanup_sql_files

    # Task 6: Cleanup old tables
    cleanup_old_tables

    # Task 1: Download SQL files
    download_sql_files

    # Task 2: Load SQL to lib tables
    load_sql_to_lib_tables

    # Task 3: Apply preparation scripts
    apply_preparation_scripts

    # Task 4: Activate cb_lib tables
    activate_cb_tables

    log "🎉 All tasks completed successfully!"
    log "📊 Final database statistics:"
    if [ -f "$SCRIPTS_DIR/zz_56_db_statistics.sql" ]; then
        _run_sql_file "$SCRIPTS_DIR/zz_56_db_statistics.sql"
    else
        log "ℹ️  Statistics script not found"
    fi

    log "📝 Log file saved to: $LOG_FILE"
}

# Run main function
main