# Переименование таблиц в cb_ префикс

## Зачем нужны cb_ таблицы?

- **Безопасность**: Обновление БД не влияет на работающий бот
- **Откат**: Можно быстро вернуться (RENAME обратно)
- **Изоляция**: Staging (lib*) и Production (cb_lib*) разделены

---

## 🚀 Процесс обновления БД Flibusta

### Вариант А: Первичная миграция (если таблицы lib* уже существуют)

Если у вас уже есть lib* таблицы с данными и индексами:
```bash
# 1. Остановите бот
docker-compose stop bot

# 2. Переименуйте lib* → cb_lib*
docker exec -i flibusta-db mariadb -u flibusta -pflibusta flibusta < db_init/migrate_to_cb_tables.sql

# 3. Запустите бот с обновлённым кодом (использующим cb_*)
docker-compose start bot
```

**Результат:** lib* → cb_lib* (данные остались те же, операция мгновенная)

---

### Вариант Б: Обновление БД из новых дампов Flibusta

Когда появилась новая версия дампов Flibusta (например, от 2025-12-XX):

#### Шаг 1: Сохранение текущих данных (бэкап)
```bash
# 1. Остановите бот
docker-compose stop bot

# 2. Переименуйте текущие cb_lib* → cb_lib_old* (бэкап на случай проблем)
docker exec -i flibusta-db mariadb -u flibusta -pflibusta flibusta << 'SQL'
RENAME TABLE 
  cb_libbook TO cb_libbook_old,
  cb_libavtor TO cb_libavtor_old,
  cb_libavtorname TO cb_libavtorname_old,
  cb_libgenre TO cb_libgenre_old,
  cb_libgenrelist TO cb_libgenrelist_old,
  cb_libseq TO cb_libseq_old,
  cb_libseqname TO cb_libseqname_old,
  cb_librate TO cb_librate_old,
  cb_librecs TO cb_librecs_old,
  cb_libreviews TO cb_libreviews_old,
  cb_libbannotations TO cb_libbannotations_old,
  cb_libaannotations TO cb_libaannotations_old,
  cb_libbook_fts TO cb_libbook_fts_old;
SQL

echo "✅ Бэкап создан: cb_lib* → cb_lib_old*"
```

#### Шаг 2: Восстановление дампов в lib* таблицы (staging)
```bash
# Положите новые .sql.gz файлы в db_init/sql/
# Например:
# - lib.a.annotations.sql.gz
# - lib.a.annotations_pics.sql.gz
# и т.д.

cd db_init/sql/

# Импортируйте все дампы в lib* таблицы
gunzip -c lib.a.annotations.sql.gz | docker exec -i flibusta-db mariadb -u flibusta -pflibusta flibusta
gunzip -c lib.a.annotations_pics.sql.gz | docker exec -i flibusta-db mariadb -u flibusta -pflibusta flibusta
gunzip -c lib.b.annotations.sql.gz | docker exec -i flibusta-db mariadb -u flibusta -pflibusta flibusta
gunzip -c lib.b.annotations_pics.sql.gz | docker exec -i flibusta-db mariadb -u flibusta -pflibusta flibusta
# ... и остальные файлы

# Или скриптом (если все файлы в db_init/sql/):
cd db_init/sql/
for file in *.sql.gz; do
    echo "Importing $file..."
    gunzip -c "$file" | docker exec -i flibusta-db mariadb -u flibusta -pflibusta flibusta
done

cd ../..

echo "✅ Дампы восстановлены в lib* таблицы"
```

**Результат:** Базовые lib* таблицы созданы и заполнены

#### Шаг 3: Выполнение скриптов инициализации (zz_*.sql)

Эти скрипты создают дополнительные индексы и таблицы:
```bash
# 1. zz_10_convert_charset.sql - выравнивание набора символов для всех таблиц
docker exec -i flibusta-db mariadb -u flibusta -pflibusta flibusta < db_init/zz_10_convert_charset.sql
echo "✅ Выравнивание набора символов"

# 2. zz_20_create_indexes.sql - создание дополнительных индексов для ускорения запросов
docker exec -i flibusta-db mariadb -u flibusta -pflibusta flibusta < db_init/zz_20_create_indexes.sql
echo "✅ Создание дополнительных индексов"

# 3. zz_30_create_FT_indexes.sql - создание FT индексов для полнотекстового поиска
docker exec -i flibusta-db mariadb -u flibusta -pflibusta flibusta < db_init/zz_30_create_FT.sql
echo "✅ Создание FT индексов"

# 4. zz_40_fill_FT.sql - создание и заполнение таблицы libbook_fts основными данными книг для полнотекстового поиска
docker exec -i flibusta-db mariadb -u flibusta -pflibusta flibusta < db_init/zz_40_fill_FT.sql
echo "✅ Создание и заполнение FTS таблицы"

# 5. zz_50_repair_FT.sql - дополнительная оптимизация таблицы libbook_fts (можно пропустить)
docker exec -i flibusta-db mariadb -u flibusta -pflibusta flibusta < db_init/zz_50_repair_FT.sql
echo "✅ Оптимизация FTS таблицы"
```

**Что делают эти скрипты:**

- **zz_10_convert_charset.sql**: 
  - Устанавливает единый набор символов utf8mb3 для БД и всех её таблиц 

- **zz_20_create_indexes.sql**: 
  - Создаёт все необходимые индексы на lib* таблицах:
    - `idx_libreviews_bookid_time_desc`, `idx_libapics_avtorid`
    - `idx_libaannotations_avtorid`, `idx_libbannotations_bookid`
    - `idx_libbpics_bookid`
    - И другие для оптимизации запросов
   
- **zz_30_create_FT_indexes.sql**: 
  - Создаёт FULLTEXT индексы:
    - На `libbannotations.Body`
    - На `libaannotations.Body`

- **zz_40_fill_FT.sql**: 
  - Создаёт и заполняет таблицу `libbook_fts`:
    - Агрегирует данные из libbook, авторов, жанров, серий
    - Создаёт FULLTEXT индекс для быстрого поиска

- **zz_50_repair_FT.sql**: 
  - Выполняет ANALYZE TABLE для оптимизации

#### Шаг 4: Переименование lib* → cb_lib* (production)
```bash
# Переименуйте staging таблицы в production (мгновенная операция)
docker exec -i flibusta-db mariadb -u flibusta -pflibusta flibusta < db_init/migrate_to_cb_tables.sql

echo "✅ Таблицы переименованы: lib* → cb_lib*"
```

#### Шаг 5: Запуск бота
```bash
# Запустите бот - он будет использовать новые cb_lib* таблицы
docker-compose start bot

# Проверьте логи
docker-compose logs -f bot

echo "✅ Бот запущен с новыми данными"
```

#### Шаг 6: Проверка работоспособности

Протестируйте основные функции:
- ✅ Поиск книг работает
- ✅ Популярные книги отображаются
- ✅ Информация о книге загружается
- ✅ Скачивание работает

#### Шаг 7: Очистка старых данных (опционально)

Если всё работает стабильно несколько дней, удалите бэкап:
```bash
docker exec -i flibusta-db mariadb -u flibusta -pflibusta flibusta << 'SQL'
DROP TABLE IF EXISTS 
  cb_libbook_old,
  cb_libavtor_old,
  cb_libavtorname_old,
  cb_libgenre_old,
  cb_libgenrelist_old,
  cb_libseq_old,
  cb_libseqname_old,
  cb_librate_old,
  cb_librecs_old,
  cb_libreviews_old,
  cb_libbannotations_old,
  cb_libaannotations_old,
  cb_libbook_fts_old;
  cb_libapics_old;
  cb_libbpica_old;
SQL

echo "✅ Старые таблицы удалены"
```

---

## 🔄 Откат к предыдущей версии

Если что-то пошло не так после обновления:

### Быстрый откат (вернуть старые cb_lib_old*)
```bash
# 1. Остановите бот
docker-compose stop bot

# 2. Удалите новые cb_lib* (с проблемами)
docker exec -i flibusta-db mariadb -u flibusta -pflibusta flibusta << 'SQL'
DROP TABLE IF EXISTS 
  cb_libbook, cb_libavtor, cb_libavtorname, cb_libgenre, 
  cb_libgenrelist, cb_libseq, cb_libseqname, cb_librate, 
  cb_libreviews, cb_libbannotations, cb_libaannotations, 
  cb_libbook_fts, cb_librecs, cb_libapics, cb_libbpics;
SQL

# 3. Переименуйте old обратно
docker exec -i flibusta-db mariadb -u flibusta -pflibusta flibusta << 'SQL'
RENAME TABLE 
  cb_libbook_old TO cb_libbook,
  cb_libavtor_old TO cb_libavtor,
  cb_libavtorname_old TO cb_libavtorname,
  cb_libgenre_old TO cb_libgenre,
  cb_libgenrelist_old TO cb_libgenrelist,
  cb_libseq_old TO cb_libseq,
  cb_libseqname_old TO cb_libseqname,
  cb_librate_old TO cb_librate,
  cb_librecs_old TO cb_librecs,
  cb_libreviews_old TO cb_libreviews,
  cb_libbannotations_old TO cb_libbannotations,
  cb_libaannotations_old TO cb_libaannotations,
  cb_libbook_fts_old TO cb_libbook_fts;
  cb_libapics_old TO cb_libapics;
  cb_libbpics_old TO cb_libbpics;
SQL

# 4. Запустите бот
docker-compose start bot

echo "✅ Откат выполнен, работают старые данные"
```

---

## 📊 Проверка статуса таблиц
```bash
# Посмотреть все таблицы с lib/cb_lib префиксом
docker exec -i flibusta-db mariadb -u flibusta -pflibusta flibusta << 'SQL'
SELECT 
    table_name, 
    table_rows, 
    ROUND((data_length + index_length) / 1024 / 1024, 2) as size_mb,
    create_time
FROM information_schema.tables 
WHERE table_schema = 'flibusta' 
  AND (table_name LIKE 'lib%' OR table_name LIKE 'cb_lib%')
ORDER BY table_name;
SQL
```

---

## 🎯 Итоговая структура БД

После успешной миграции:
```
MariaDB (flibusta):
├── cb_lib* (production) ← используется ботом
│   ├── cb_libbook
│   ├── cb_libavtor
│   ├── cb_libavtorname
│   ├── cb_libgenre
│   ├── cb_libgenrelist
│   ├── cb_libseq
│   ├── cb_libseqname
│   ├── cb_librate
│   ├── cb_librecs
│   ├── cb_libreviews
│   ├── cb_libbannotations
│   ├── cb_libaannotations
│   ├── cb_libapics
│   ├── cb_libbpics
│   └── cb_libbook_fts (полнотекстовый индекс)
│
├── cb_lib*_old (бэкап) ← можно удалить после проверки
│   └── ... (старая версия данных)
│
└── lib* (staging) ← временные, удаляются после RENAME
    └── создаются при импорте → переименовываются в cb_lib*
```

---

## 📝 Краткая шпаргалка

### Полное обновление одной командой:
```bash
#!/bin/bash
# update_flibusta.sh - полный процесс обновления

set -e  # Остановка при ошибке

echo "🛑 Остановка бота..."
docker-compose stop bot

echo "💾 Создание бэкапа cb_lib* → cb_lib_old*..."
docker exec -i flibusta-db mariadb -u flibusta -pflibusta flibusta << 'SQL'
RENAME TABLE 
  cb_libbook TO cb_libbook_old,
  cb_libavtor TO cb_libavtor_old,
  cb_libavtorname TO cb_libavtorname_old,
  cb_libgenre TO cb_libgenre_old,
  cb_libgenrelist TO cb_libgenrelist_old,
  cb_libseq TO cb_libseq_old,
  cb_libseqname TO cb_libseqname_old,
  cb_librate TO cb_librate_old,
  cb_librecs TO cb_librecs_old,
  cb_libreviews TO cb_libreviews_old,
  cb_libbannotations TO cb_libbannotations_old,
  cb_libaannotations TO cb_libaannotations_old,
  cb_libbook_fts TO cb_libbook_fts_old;
  cb_libapics TO cb_libapics_old;
  cb_libbpics TO cb_libbpics_old;
SQL

echo "📦 Импорт дампов в lib* таблицы..."
cd db_init/sql/
for file in *.sql.gz; do
    echo "  - $file"
    gunzip -c "$file" | docker exec -i flibusta-db mariadb -u flibusta -pflibusta flibusta
done
cd ../..

echo "⚙️  Выполнение скриптов инициализации..."
docker exec -i flibusta-db mariadb -u flibusta -pflibusta flibusta < db_init/zz_10_convert_charset.sql
docker exec -i flibusta-db mariadb -u flibusta -pflibusta flibusta < db_init/zz_20_create_indexes.sql
docker exec -i flibusta-db mariadb -u flibusta -pflibusta flibusta < db_init/zz_30_create_FT_indexes.sql
docker exec -i flibusta-db mariadb -u flibusta -pflibusta flibusta < db_init/zz_40_fill_FT.sql
docker exec -i flibusta-db mariadb -u flibusta -pflibusta flibusta < db_init/zz_50_repair_FT.sql

echo "🔄 Переименование lib* → cb_lib*..."
docker exec -i flibusta-db mariadb -u flibusta -pflibusta flibusta < db_init/migrate_to_cb_tables.sql

echo "🚀 Запуск бота..."
docker-compose start bot

echo "✅ Обновление завершено!"
echo "📊 Проверьте логи: docker-compose logs -f bot"
```

Сохраните как `update_flibusta.sh`, сделайте исполняемым:
```bash
chmod +x update_flibusta.sh
```

И запускайте при обновлении:
```bash
./update_flibusta.sh
```

---

## ⚠️ Важные примечания

1. **Время выполнения**: Создание FTS может занять 10-30 минут для большой БД
2. **Место на диске**: Нужно ~2x места от размера БД (старые + новые таблицы)
3. **Бэкап**: Всегда держите cb_lib_old* таблицы несколько дней после обновления
4. **Тестирование**: Проверяйте все функции бота после обновления
5. **Откат**: Процесс отката занимает ~30 секунд (просто RENAME обратно)
