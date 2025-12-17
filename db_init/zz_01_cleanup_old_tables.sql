-- ============================================
-- Откат: Переименование cb_lib* обратно в lib*
-- ============================================
--
-- Использование:
--   mysql -u flibusta -p flibusta < rollback_cb_tables.sql
--

--SET NAMES utf8mb3;
--SET CHARACTER SET utf8mb3;
--
SELECT 'Cleanup old tables...' as Status;

DROP TABLE IF EXISTS cb_libbook_old, cb_libavtor_old, cb_libavtorname_old, cb_libgenre_old,
    cb_libgenrelist_old, cb_libseq_old, cb_libseqname_old, cb_librate_old, cb_librecs_old,
    cb_libreviews_old, cb_libbannotations_old, cb_libaannotations_old, cb_libbook_fts_old,
    cb_libapics_old, cb_libbpics_old;

SELECT 'Cleanup completed!' as Status;