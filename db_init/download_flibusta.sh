#!/bin/bash

# 1. Запрос директории
read -p "Укажите директорию для скачивания (по умолчанию: /media/sf_FlibustaBot/sql/): " DOWNLOAD_DIR
DOWNLOAD_DIR="${DOWNLOAD_DIR:-/media/sf_FlibustaBot/sql/}"
mkdir -p "$DOWNLOAD_DIR"

# 2. Обязательные файлы
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

# 3. Запрос на дополнительные файлы
read -p "Скачать дополнительные файлы? (y/N): " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
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

# 4. Скачивание с поддержкой докачки и прогрессом
cd "$DOWNLOAD_DIR" || exit 1
for url in "${FILES[@]}"; do
  filename=$(basename "$url")
  echo "Скачивание: $filename"
  wget -c --show-progress -O "$filename" "$url"
done

echo "Готово."