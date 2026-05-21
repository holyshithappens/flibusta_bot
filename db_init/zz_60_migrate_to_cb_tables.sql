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
--   mysql -u flibusta -p flibusta < zz_60_migrate_to_cb_tables.sql
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

SELECT 'Starting migration: lib* tables to cb_lib*' AS OperationStatus;

-- Основные таблицы
RENAME TABLE IF EXISTS libbook TO cb_libbook;
SELECT 'Renamed libbook to cb_libbook' AS OperationStatus;
RENAME TABLE IF EXISTS libavtor TO cb_libavtor;
SELECT 'Renamed libavtor to cb_libavtor' AS OperationStatus;
RENAME TABLE IF EXISTS libavtorname TO cb_libavtorname;
SELECT 'Renamed libavtorname to cb_libavtorname' AS OperationStatus;
RENAME TABLE IF EXISTS libgenre TO cb_libgenre;
SELECT 'Renamed libgenre to cb_libgenre' AS OperationStatus;
RENAME TABLE IF EXISTS libgenrelist TO cb_libgenrelist;
SELECT 'Renamed libgenrelist to cb_libgenrelist' AS OperationStatus;
RENAME TABLE IF EXISTS libseq TO cb_libseq;
SELECT 'Renamed libseq to cb_libseq' AS OperationStatus;
RENAME TABLE IF EXISTS libseqname TO cb_libseqname;
SELECT 'Renamed libseqname to cb_libseqname' AS OperationStatus;
RENAME TABLE IF EXISTS librate TO cb_librate;
SELECT 'Renamed librate to cb_librate' AS OperationStatus;
RENAME TABLE IF EXISTS librecs TO cb_librecs;
SELECT 'Renamed librecs to cb_librecs' AS OperationStatus;
RENAME TABLE IF EXISTS libreviews TO cb_libreviews;
SELECT 'Renamed libreviews to cb_libreviews' AS OperationStatus;
RENAME TABLE IF EXISTS libapics TO cb_libapics;
SELECT 'Renamed libapics to cb_libapics' AS OperationStatus;
RENAME TABLE IF EXISTS libbpics TO cb_libbpics;
SELECT 'Renamed libbpics to cb_libbpics' AS OperationStatus;

-- Аннотации
RENAME TABLE IF EXISTS libbannotations TO cb_libbannotations;
SELECT 'Renamed libbannotations to cb_libbannotations' AS OperationStatus;
RENAME TABLE IF EXISTS libaannotations TO cb_libaannotations;
SELECT 'Renamed libaannotations to cb_libaannotations' AS OperationStatus;

-- Полнотекстовый индекс
RENAME TABLE IF EXISTS libbook_fts TO cb_libbook_fts;
SELECT 'Renamed libbook_fts to cb_libbook_fts' AS OperationStatus;

SELECT 'Migration completed: All lib* tables renamed to cb_lib*' AS OperationStatus;

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