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
--   mysql -u flibusta -p flibusta < zz_59_migrate_cb_tables_to_old.sql
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

SELECT 'Starting migration: cb_lib* tables to cb_lib*_old' AS OperationStatus;

-- Основные таблицы
RENAME TABLE IF EXISTS cb_libbook TO cb_libbook_old;
SELECT 'Renamed cb_libbook to cb_libbook_old' AS OperationStatus;
RENAME TABLE IF EXISTS cb_libavtor TO cb_libavtor_old;
SELECT 'Renamed cb_libavtor to cb_libavtor_old' AS OperationStatus;
RENAME TABLE IF EXISTS cb_libavtorname TO cb_libavtorname_old;
SELECT 'Renamed cb_libavtorname to cb_libavtorname_old' AS OperationStatus;
RENAME TABLE IF EXISTS cb_libgenre TO cb_libgenre_old;
SELECT 'Renamed cb_libgenre to cb_libgenre_old' AS OperationStatus;
RENAME TABLE IF EXISTS cb_libgenrelist TO cb_libgenrelist_old;
SELECT 'Renamed cb_libgenrelist to cb_libgenrelist_old' AS OperationStatus;
RENAME TABLE IF EXISTS cb_libseq TO cb_libseq_old;
SELECT 'Renamed cb_libseq to cb_libseq_old' AS OperationStatus;
RENAME TABLE IF EXISTS cb_libseqname TO cb_libseqname_old;
SELECT 'Renamed cb_libseqname to cb_libseqname_old' AS OperationStatus;
RENAME TABLE IF EXISTS cb_librate TO cb_librate_old;
SELECT 'Renamed cb_librate to cb_librate_old' AS OperationStatus;
RENAME TABLE IF EXISTS cb_librecs TO cb_librecs_old;
SELECT 'Renamed cb_librecs to cb_librecs_old' AS OperationStatus;
RENAME TABLE IF EXISTS cb_libreviews TO cb_libreviews_old;
SELECT 'Renamed cb_libreviews to cb_libreviews_old' AS OperationStatus;
RENAME TABLE IF EXISTS cb_libapics TO cb_libapics_old;
SELECT 'Renamed cb_libapics to cb_libapics_old' AS OperationStatus;
RENAME TABLE IF EXISTS cb_libbpics TO cb_libbpics_old;
SELECT 'Renamed cb_libbpics to cb_libbpics_old' AS OperationStatus;

-- Аннотации
RENAME TABLE IF EXISTS cb_libbannotations TO cb_libbannotations_old;
SELECT 'Renamed cb_libbannotations to cb_libbannotations_old' AS OperationStatus;
RENAME TABLE IF EXISTS cb_libaannotations TO cb_libaannotations_old;
SELECT 'Renamed cb_libaannotations to cb_libaannotations_old' AS OperationStatus;

-- Полнотекстовый индекс
RENAME TABLE IF EXISTS cb_libbook_fts TO cb_libbook_fts_old;
SELECT 'Renamed cb_libbook_fts to cb_libbook_fts_old' AS OperationStatus;

SELECT 'Migration completed: All cb_lib* tables renamed to cb_lib*_old' AS OperationStatus;

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