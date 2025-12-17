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
RENAME TABLE cb_libbook TO cb_libbook_old;
RENAME TABLE cb_libavtor TO cb_libavtor_old;
RENAME TABLE cb_libavtorname TO cb_libavtorname_old;
RENAME TABLE cb_libgenre TO cb_libgenre_old;
RENAME TABLE cb_libgenrelist TO cb_libgenrelist_old;
RENAME TABLE cb_libseq TO cb_libseq_old;
RENAME TABLE cb_libseqname TO cb_libseqname_old;
RENAME TABLE cb_librate TO cb_librate_old;
RENAME TABLE cb_librecs TO cb_librecs_old;
RENAME TABLE cb_libreviews TO cb_libreviews_old;
RENAME TABLE cb_libapics TO cb_libapics_old;
RENAME TABLE cb_libbpics TO cb_libbpics_old;

-- Аннотации
RENAME TABLE cb_libbannotations TO cb_libbannotations_old;
RENAME TABLE cb_libaannotations TO cb_libaannotations_old;

-- Полнотекстовый индекс
RENAME TABLE cb_libbook_fts TO cb_libbook_fts_old;

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