#!/bin/bash
# drop_old_table.sh - Drop old backup table with safety checks
# Usage: drop_old_table.sh <table>

set -e -o pipefail

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

# Safety check - only allow dropping cb_*_old tables
if [[ ! "$TABLE" =~ ^cb_.*_old$ ]]; then
    echo "Error: Can only drop tables matching pattern cb_*_old"
    exit 1
fi

# Execute drop
#echo "Dropping old table $TABLE..."
SQL="DROP TABLE IF EXISTS \`$TABLE\`;"
if docker exec -i "$FLIBUSTA_DB_CONTAINER" mariadb -u "$FLIBUSTA_DB_USER" -p"$FLIBUSTA_DB_PASS" "$FLIBUSTA_DB_NAME" <<< "$SQL"; then
    echo "✅ Dropped $TABLE successfully"
else
    echo "❌ Failed to drop $TABLE"
    exit 1
fi