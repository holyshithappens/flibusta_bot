#!/bin/bash
# manage_flibusta_db.sh - Local DB management on VPS
# Place this script in ~/flbst-bot-mdb/db_init and run it directly on VPS

set -euo pipefail

DB_DIR="$HOME/flbst-bot-mdb/db_init"
SQL_DIR="$DB_DIR/sql"
SCRIPTS_DIR="$DB_DIR"

DB_USER="flibusta"
DB_PASS="flibusta"
DB_NAME="flibusta"
CONTAINER="flibusta-db"

# Утилита выполнения SQL
_run_sql() {
    docker exec -i "$CONTAINER" mariadb -u "$DB_USER" -p"$DB_PASS" "$DB_NAME" <<< "$1"
}

show_menu() {
    cat <<EOF

🔧 Flibusta DB Manager
1) Скачать SQL-файлы (в $SQL_DIR)
2) Загрузить lib*.sql в БД (staging)
3) Применить скрипты подготовки (zz_10 → zz_50)
4) Переименовать lib* → cb_lib* (активация)
5) Откат: cb_lib*_old → cb_lib*
6) Удалить старые cb_lib*_old
0) Выйти

EOF
}

# === Подфункции ===

download_sql_files() {
    echo "⬇️  Скачивание SQL-файлов..."
    mkdir -p "$SQL_DIR"
    cd "$SQL_DIR"

    REQUIRED=(
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
    )

    read -rp "Скачать доп. файлы? (y/N): " -n1 extra
    echo
    if [[ $extra =~ ^[Yy]$ ]]; then
        EXTRA=(
            "https://flibusta.is/sql/lib.libtranslator.sql.gz"
            "https://flibusta.is/sql/lib.libfilename.sql.gz"
            "https://flibusta.is/sql/lib.libgenrelist.sql.gz"
            "https://flibusta.is/sql/lib.libgenretranslate.sql.gz"
            "https://flibusta.is/sql/lib.libjoinedbooks.sql.gz"
            "https://flibusta.is/sql/lib.libseqname.sql.gz"
            "https://flibusta.is/sql/lib.b.annotations_pics.sql.gz"
            "https://flibusta.is/sql/lib.a.annotations_pics.sql.gz"
        )
        FILES=("${REQUIRED[@]}" "${EXTRA[@]}")
    else
        FILES=("${REQUIRED[@]}")
    fi

    for url in "${FILES[@]}"; do
        filename=$(basename "$url")
        echo "📥 $filename"
        wget -c --show-progress -O "$filename" "$url"
    done
    echo "✅ Скачивание завершено"
}

load_sql_to_lib_tables() {
    echo "💾 Восстановление в lib* таблицы..."
    cd "$SQL_DIR"
    for gz in *.sql.gz; do
        [[ -f "$gz" ]] || continue
        base=$(basename "$gz" .sql.gz)
        echo "  → $base"
        gunzip -c "$gz" | docker exec -i "$CONTAINER" mariadb -u "$DB_USER" -p"$DB_PASS" "$DB_NAME"
    done
    echo "✅ Данные загружены в lib*"
}

apply_preparation_scripts() {
    echo "⚙️  Применение скриптов подготовки..."
    for script in zz_10_convert_charset.sql \
                  zz_20_create_indexes.sql \
                  zz_30_create_FT_indexes.sql \
                  zz_40_fill_FT.sql \
                  zz_50_repair_FT.sql; do
        echo "  → $script"
        docker exec -i "$CONTAINER" mariadb -u "$DB_USER" -p"$DB_PASS" "$DB_NAME" < "$SCRIPTS_DIR/$script"
    done
    echo "✅ Подготовка завершена"
}

activate_cb_tables() {
    echo "🚀 Активация cb_lib* таблиц..."
    docker exec -i "$CONTAINER" mariadb -u "$DB_USER" -p"$DB_PASS" "$DB_NAME" < "$SCRIPTS_DIR/zz_59_migrate_cb_tables_to_old.sql"
    docker exec -i "$CONTAINER" mariadb -u "$DB_USER" -p"$DB_PASS" "$DB_NAME" < "$SCRIPTS_DIR/zz_60_migrate_to_cb_tables.sql"
    echo "✅ Переименование выполнено: lib* → cb_lib*"
}

rollback_to_old() {
    echo "🔙 Откат к cb_lib_old*..."
    docker exec -i "$CONTAINER" mariadb -u "$DB_USER" -p"$DB_PASS" "$DB_NAME" < "$SCRIPTS_DIR/zz_00_rollback_cb_tables.sql"
    echo "✅ Откат выполнен"
}

cleanup_old_tables() {
    echo "🗑️  Удаление cb_lib_old*..."
    docker exec -i "$CONTAINER" mariadb -u "$DB_USER" -p"$DB_PASS" "$DB_NAME" < "$SCRIPTS_DIR/zz_01_cleanup_old_tables.sql"
    echo "✅ Старые таблицы удалены"
}

# === Основной цикл ===
while true; do
    show_menu
    read -rp "Выберите действие: " choice
    case $choice in
        1) download_sql_files ;;
        2) load_sql_to_lib_tables ;;
        3) apply_preparation_scripts ;;
        4) activate_cb_tables ;;
        5) rollback_to_old ;;
        6) cleanup_old_tables ;;
        0) exit 0 ;;
        *) echo "❌ Неверный выбор" ;;
    esac
    echo
done