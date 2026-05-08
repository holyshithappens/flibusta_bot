#!/bin/bash
# update_all_tables.sh - Full all-tables update workflow
# This script processes all tables/files defined in tables.conf using atomic scripts

set -e -o pipefail

# Configuration
#: "${FLIBUSTA_DB_DIR:=$HOME/flbst-bot-mdb/db_init}"
: "${FLIBUSTA_DB_DIR:=$(cd "$(dirname "$0")/.." && pwd)}"
DB_DIR="$FLIBUSTA_DB_DIR"
SQL_DIR="$DB_DIR/sql"
SCRIPTS_DIR="$(dirname "$0")"

# Environment variables with defaults
: "${FLIBUSTA_DB_CONTAINER:=flibusta-db}"
: "${FLIBUSTA_DB_USER:=flibusta}"
: "${FLIBUSTA_DB_PASS:=flibusta}"
: "${FLIBUSTA_DB_NAME:=flibusta}"
: "${FLIBUSTA_SQL_URL_BASE:=https://flibusta.is/sql/}"

: "${FLIBUSTA_DB_MAINT_USER:=root}"
: "${FLIBUSTA_DB_MAINT_PASS:=rootpassword}"

_run_sql_admin() {
    echo "$(date '+%Y-%m-%d %H:%M:%S') - Executing maintenance SQL: $1"
    docker exec -i "$FLIBUSTA_DB_CONTAINER" mariadb \
        -u "$FLIBUSTA_DB_MAINT_USER" \
        -p"$FLIBUSTA_DB_MAINT_PASS" \
        "$FLIBUSTA_DB_NAME" <<< "$1"
}

# SQL execution utility
_run_sql() {
    echo "$(date '+%Y-%m-%d %H:%M:%S') - Executing SQL: $1"
    docker exec -i "$FLIBUSTA_DB_CONTAINER" mariadb -u "$FLIBUSTA_DB_USER" -p"$FLIBUSTA_DB_PASS" "$FLIBUSTA_DB_NAME" <<< "$1"
}

# Function to execute SQL script file
_run_sql_file() {
    local script_name=$(basename "$1")
    echo "$(date '+%Y-%m-%d %H:%M:%S') - Executing SQL script: $script_name"
    docker exec -i "$FLIBUSTA_DB_CONTAINER" mariadb -u "$FLIBUSTA_DB_USER" -p"$FLIBUSTA_DB_PASS" "$FLIBUSTA_DB_NAME" < "$1"
    echo "$(date '+%Y-%m-%d %H:%M:%S') - Completed SQL script: $script_name"
}

# === Task Functions ===
prepare_system() {
#```
#For the `sudo` commands to work without a password prompt from cron, add this to `/etc/sudoers.d/flibusta-update`:
#```
#holy ALL=(root) NOPASSWD: /usr/bin/tee /proc/sys/vm/drop_caches
#holy ALL=(root) NOPASSWD: /sbin/swapoff -a
#holy ALL=(root) NOPASSWD: /sbin/swapon -a

    echo "$(date '+%Y-%m-%d %H:%M:%S') - 🧹 Preparing system for update..."

    # 1. Flush and clear InnoDB buffer pool
    _run_sql_admin "SET GLOBAL innodb_buffer_pool_size = 134217728;"
    _run_sql_admin "SET GLOBAL innodb_buffer_pool_size = 536870912;"

    # 2. Drop OS page cache (requires sudo — set up sudoers or run as root)
    sync
    echo 3 | sudo tee /proc/sys/vm/drop_caches > /dev/null

    # 3. Flush swap if enough free RAM exists
    FREE_MB=$(free -m | awk '/^Mem:/{print $7}')
    SWAP_USED=$(free -m | awk '/^Swap:/{print $3}')
    if [ "$SWAP_USED" -gt 50 ] && [ "$FREE_MB" -gt 700 ]; then
        echo "$(date '+%Y-%m-%d %H:%M:%S') - Flushing ${SWAP_USED}MB of swap..."
# Consider run sudo commands without prompting password!
#        sudo swapoff -a && sudo swapon -a
    else
        echo "$(date '+%Y-%m-%d %H:%M:%S') - Skipping swap flush (free RAM: ${FREE_MB}MB, swap used: ${SWAP_USED}MB)"
    fi

    echo "$(date '+%Y-%m-%d %H:%M:%S') - ✅ System prepared"
}

cleanup_sql_files() {
    echo "$(date '+%Y-%m-%d %H:%M:%S') - 🧹 Starting task: Cleanup SQL files..."
    mkdir -p "$SQL_DIR"
    cd "$SQL_DIR"

    local cleaned_count=0
    local total_count=0

    while IFS='=' read -r table filename; do
        # Skip comments and empty lines
        [[ "$table" =~ ^#.*$ ]] && continue
        [[ -z "$table" ]] && continue

        total_count=$((total_count + 1))
        if [ -f "$filename" ]; then
            echo "$(date '+%Y-%m-%d %H:%M:%S') - Removing $filename for table $table..."
            rm -f "$filename"
            cleaned_count=$((cleaned_count + 1))
        fi
    done < "$DB_DIR/scripts/tables.conf"

    echo "$(date '+%Y-%m-%d %H:%M:%S') - ✅ Task completed: Cleaned up $cleaned_count/$total_count SQL files"
}

download_sql_files() {
    echo "$(date '+%Y-%m-%d %H:%M:%S') - 📥 Starting task: Download SQL files..."
    mkdir -p "$SQL_DIR"
    cd "$SQL_DIR"

    local success_count=0
    local total_count=0

    while IFS='=' read -r table filename; do
        # Skip comments and empty lines
        [[ "$table" =~ ^#.*$ ]] && continue
        [[ -z "$table" ]] && continue
        total_count=$((total_count + 1)) || { echo "$(date '+%Y-%m-%d %H:%M:%S') - ❌ Arithmetic error with total_count"; exit 1; }
        local url="${FLIBUSTA_SQL_URL_BASE}${filename}"
        echo "$(date '+%Y-%m-%d %H:%M:%S') - Downloading $filename for table $table..."
        if wget -c -q -O "$filename" "$url" 2>/dev/null; then
            echo "$(date '+%Y-%m-%d %H:%M:%S') - ✅ Downloaded $filename successfully"
            success_count=$((success_count + 1))
        else
            echo "$(date '+%Y-%m-%d %H:%M:%S') - ❌ Failed to download $filename"
        fi
    done < "$DB_DIR/scripts/tables.conf"

    echo "$(date '+%Y-%m-%d %H:%M:%S') - ✅ Task completed: Downloaded $success_count/$total_count SQL files"
}

load_sql_to_lib_tables() {
    echo "$(date '+%Y-%m-%d %H:%M:%S') - 💾 Starting task: Load SQL to lib tables..."
    mkdir -p "$SQL_DIR"
    cd "$SQL_DIR"

    local imported_count=0
    local total_count=0

    # Process files from tables.conf instead of using find
    while IFS='=' read -r table filename; do
        # Skip comments and empty lines
        [[ "$table" =~ ^#.*$ ]] && continue
        [[ -z "$table" ]] && continue

        total_count=$((total_count + 1))
        if [ -f "$filename" ]; then
            local base=$(basename "$filename" .sql.gz)
            echo "$(date '+%Y-%m-%d %H:%M:%S') - Importing $base..."
            if gunzip -c "$filename" 2>/dev/null | docker exec -i "$FLIBUSTA_DB_CONTAINER" mariadb -u "$FLIBUSTA_DB_USER" -p"$FLIBUSTA_DB_PASS" "$FLIBUSTA_DB_NAME"; then
                echo "$(date '+%Y-%m-%d %H:%M:%S') - ✅ Imported $base successfully"
                imported_count=$((imported_count + 1))
            else
                echo "$(date '+%Y-%m-%d %H:%M:%S') - ❌ Failed to import $base"
            fi
        else
            echo "$(date '+%Y-%m-%d %H:%M:%S') - ❌ File not found: $filename"
        fi
    done < "$DB_DIR/scripts/tables.conf"

    echo "$(date '+%Y-%m-%d %H:%M:%S') - ✅ Task completed: Imported $imported_count/$total_count SQL files to lib* tables"
}

activate_cb_tables() {
    echo "$(date '+%Y-%m-%d %H:%M:%S') - 🚀 Starting task: Activate cb_lib tables..."

    local success_count=0
    local total_count=0

    # Process tables from tables.conf using atomic scripts
    while IFS='=' read -r table filename; do
        # Skip comments and empty lines
        [[ "$table" =~ ^#.*$ ]] && continue
        [[ -z "$table" ]] && continue

        total_count=$((total_count + 1))

#        # Drop old backup table
#        "$DB_DIR/scripts/drop_old_table.sh" "cb_${table}_old"

        # Rename cb_<table> to cb_<table>_old (backup)
        "$DB_DIR/scripts/rename_table.sh" "cb_${table}" "cb_${table}_old"

        # Rename <table> to cb_<table> (activate) - table is already lib*
        "$DB_DIR/scripts/rename_table.sh" "${table}" "cb_${table}"

        success_count=$((success_count + 1))
    done < "$DB_DIR/scripts/tables.conf"

    echo "$(date '+%Y-%m-%d %H:%M:%S') - ✅ Task completed: Activated $success_count/$total_count tables"
}

drop_old_cb_tables() {
    echo "$(date '+%Y-%m-%d %H:%M:%S') - 🚀 Starting task: Drop cb_lib*_old tables..."

    local success_count=0
    local total_count=0

    # Process tables from tables.conf using atomic scripts
    while IFS='=' read -r table filename; do
        # Skip comments and empty lines
        [[ "$table" =~ ^#.*$ ]] && continue
        [[ -z "$table" ]] && continue

        total_count=$((total_count + 1))

        # Drop old backup table
        "$DB_DIR/scripts/drop_old_table.sh" "cb_${table}_old"

        success_count=$((success_count + 1))
    done < "$DB_DIR/scripts/tables.conf"

    echo "$(date '+%Y-%m-%d %H:%M:%S') - ✅ Task completed: Dropped $success_count/$total_count tables"
}

apply_preparation_scripts() {
    echo "$(date '+%Y-%m-%d %H:%M:%S') - 🔧 Starting task: Apply preparation scripts..."

    local scripts=()
    scripts+=("zz_10_convert_charset.sql")
    scripts+=("zz_20_create_indexes.sql")
    scripts+=("zz_30_create_FT_indexes.sql")
    scripts+=("zz_40_fill_FT.sql")
#    scripts+=("zz_50_repair_FT.sql")

#    _run_sql "SET GLOBAL innodb_buffer_pool_size = 268435456;"  -- 256M

    local success_count=0
    for script in "${scripts[@]}"; do
        if [ -f "$DB_DIR/$script" ]; then
            _run_sql_file "$DB_DIR/$script"
            success_count=$((success_count + 1))
        else
            echo "$(date '+%Y-%m-%d %H:%M:%S') - ❌ Script not found: $script"
        fi
    done

#    _run_sql "SET GLOBAL innodb_buffer_pool_size = 536870912;"  -- restore 512M

    echo "$(date '+%Y-%m-%d %H:%M:%S') - ✅ Task completed: Applied $success_count preparation scripts"
}

process_libbook_fts() {
    echo "$(date '+%Y-%m-%d %H:%M:%S') - 📖 Processing aux table: libbook_fts"

    # Drop old backup table
    "$DB_DIR/scripts/drop_old_table.sh" "cb_libbook_fts_old"

    # Rename cb_libbook_fts to cb_libbook_fts_old (backup)
    "$DB_DIR/scripts/rename_table.sh" "cb_libbook_fts" "cb_libbook_fts_old"

    # Rename libbook_fts to cb_libbook_fts (activate)
    "$DB_DIR/scripts/rename_table.sh" "libbook_fts" "cb_libbook_fts"

    echo "$(date '+%Y-%m-%d %H:%M:%S') - ✅ Processed libbook_fts aux table"
}

# Function to ensure containers are healthy
ensure_containers_healthy() {
    echo "$(date '+%Y-%m-%d %H:%M:%S') - 🏥 Starting task: Ensure containers are healthy..."
    "$DB_DIR/scripts/ensure_containers_healthy.sh"
    echo "$(date '+%Y-%m-%d %H:%M:%S') - ✅ Task completed: Containers are healthy"
}

# === Main Execution ===
main() {
    echo "$(date '+%Y-%m-%d %H:%M:%S') - 🔄 Starting Automated Flibusta DB Update Process"

    local executed_count=0
    local total_count=0

    # Read and execute tasks from configuration file
    while read -r task_name; do
        # Skip comments and empty lines
        [[ "$task_name" =~ ^#.*$ ]] && continue
        [[ -z "$task_name" ]] && continue

        total_count=$((total_count + 1))
        echo "$(date '+%Y-%m-%d %H:%M:%S') - 📋 Executing task $total_count: $task_name"

        if [[ "$task_name" == "cleanup_sql_files" ]]; then
            cleanup_sql_files
        elif [[ "$task_name" == "download_sql_files" ]]; then
            download_sql_files
        elif [[ "$task_name" == "prepare_system" ]]; then
            prepare_system
        elif [[ "$task_name" == "load_sql_to_lib_tables" ]]; then
            load_sql_to_lib_tables
        elif [[ "$task_name" == "apply_preparation_scripts" ]]; then
            apply_preparation_scripts
        elif [[ "$task_name" == "drop_old_cb_tables" ]]; then
            drop_old_cb_tables
        elif [[ "$task_name" == "activate_cb_tables" ]]; then
            activate_cb_tables
        elif [[ "$task_name" == "process_libbook_fts" ]]; then
            process_libbook_fts
        elif [[ "$task_name" == "ensure_containers_healthy" ]]; then
            ensure_containers_healthy
        else
            echo "$(date '+%Y-%m-%d %H:%M:%S') - ❌ Unknown task: $task_name"
            continue
        fi

        executed_count=$((executed_count + 1))
    done < "$DB_DIR/scripts/tasks.conf"

    echo "$(date '+%Y-%m-%d %H:%M:%S') - 🎉 Completed $executed_count/$total_count tasks successfully!"
    echo "$(date '+%Y-%m-%d %H:%M:%S') - 📊 Final database statistics:"
    if [ -f "$DB_DIR/zz_56_db_statistics.sql" ]; then
        _run_sql_file "$DB_DIR/zz_56_db_statistics.sql"
    else
        echo "$(date '+%Y-%m-%d %H:%M:%S') - ℹ️  Statistics script not found"
    fi
}

# Run main function
main