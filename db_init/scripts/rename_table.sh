#!/bin/bash
# rename_table.sh - Rename database table with safety checks
# Usage: rename_table.sh <from_table> <to_table>

set -e -o pipefail

# Environment variables with defaults
: "${FLIBUSTA_DB_CONTAINER:=flibusta-db}"
: "${FLIBUSTA_DB_USER:=flibusta}"
: "${FLIBUSTA_DB_PASS:=flibusta}"
: "${FLIBUSTA_DB_NAME:=flibusta}"

# Validate input
if [ $# -ne 2 ]; then
    echo "Usage: $0 <from_table> <to_table>"
    exit 1
fi

FROM_TABLE="$1"
TO_TABLE="$2"

# Safety checks according to table lifecycle rules:
# - lib* → cb_lib* (allowed: activation)
# - cb_lib* → cb_lib*_old (allowed: backup)
# - cb_lib*_old → cb_lib* (allowed: restore)

# Check if this is a lib* to cb_lib* rename (activation)
if [[ "$FROM_TABLE" =~ ^lib.*$ ]] && [[ "$TO_TABLE" =~ ^cb_lib.*$ ]]; then
    # This is allowed for activation
    :
# Check if this is a cb_lib* to cb_lib*_old rename (backup)
elif [[ "$FROM_TABLE" =~ ^cb_lib.*$ ]] && [[ "$TO_TABLE" =~ ^cb_lib.*_old$ ]]; then
    # This is allowed for backup
    :
# Check if this is a cb_lib* to lib* rename (restore 1 step)
elif [[ "$FROM_TABLE" =~ ^cb_lib.*$ ]] && [[ "$TO_TABLE" =~ ^lib.*$ ]]; then
    # This is allowed for restore
    :
# Check if this is a cb_lib*_old to cb_lib* rename (restore 2 step)
elif [[ "$FROM_TABLE" =~ ^cb_lib.*_old$ ]] && [[ "$TO_TABLE" =~ ^cb_lib.*$ ]]; then
    # This is allowed for restore
    :
else
    echo "Error: Invalid rename operation. Only allowed:"
    echo "  - lib* → cb_lib* (activation)"
    echo "  - cb_lib* → cb_lib*_old (backup)"
    echo "  - cb_lib* → lib* (restore 1)"
    echo "  - cb_lib*_old → cb_lib* (restore 2)"
    exit 1
fi

# Execute rename
#echo "Renaming table $FROM_TABLE to $TO_TABLE..."
SQL="RENAME TABLE IF EXISTS \`$FROM_TABLE\` TO \`$TO_TABLE\`;"
if docker exec -i "$FLIBUSTA_DB_CONTAINER" mariadb -u "$FLIBUSTA_DB_USER" -p"$FLIBUSTA_DB_PASS" "$FLIBUSTA_DB_NAME" <<< "$SQL"; then
    echo "✅ Renamed $FROM_TABLE to $TO_TABLE successfully"
else
    echo "❌ Failed to rename $FROM_TABLE to $TO_TABLE"
    exit 1
fi