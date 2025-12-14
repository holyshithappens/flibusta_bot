-- ============================================
-- Переименование lib* таблиц в cb_lib*
-- ============================================
--
-- Этот скрипт переименовывает существующие таблицы
-- с префиксом lib* в cb_lib* для использования ботом
--
-- ВАЖНО: Выполнять ПОСЛЕ создания всех индексов!
--
-- Использование:
--   mysql -u flibusta -p flibusta < migrate_to_cb_tables.sql
--

--SET NAMES utf8mb3;
--SET CHARACTER SET utf8mb3;
--
---- Проверка что таблицы существуют
--SELECT 'Checking tables...' as Status;
--SELECT COUNT(*) as lib_tables_count
--FROM information_schema.tables
--WHERE table_schema = 'flibusta' AND table_name LIKE 'lib%';

-- ============================================
-- Переименование таблиц
-- ============================================

-- Основные таблицы
RENAME TABLE libbook TO cb_libbook;
RENAME TABLE libavtor TO cb_libavtor;
RENAME TABLE libavtorname TO cb_libavtorname;
RENAME TABLE libgenre TO cb_libgenre;
RENAME TABLE libgenrelist TO cb_libgenrelist;
RENAME TABLE libseq TO cb_libseq;
RENAME TABLE libseqname TO cb_libseqname;
RENAME TABLE librate TO cb_librate;
RENAME TABLE librecs TO cb_librecs;
RENAME TABLE libreviews TO cb_libreviews;
RENAME TABLE libapics TO cb_libapics;
RENAME TABLE libbpics TO cb_libbpics;

-- Аннотации
RENAME TABLE libbannotations TO cb_libbannotations;
RENAME TABLE libaannotations TO cb_libaannotations;

-- Полнотекстовый индекс
RENAME TABLE libbook_fts TO cb_libbook_fts;

-- ============================================
-- Проверка результата
-- ============================================

--SELECT 'Migration completed!' as Status;
--
--SELECT COUNT(*) as cb_tables_count
--FROM information_schema.tables
--WHERE table_schema = 'flibusta' AND table_name LIKE 'cb_lib%';
--
--SELECT
--    table_name,
--    table_rows,
--    ROUND((data_length + index_length) / 1024 / 1024, 2) as size_mb
--FROM information_schema.tables
--WHERE table_schema = 'flibusta' AND table_name LIKE 'cb_lib%'
--ORDER BY table_name;