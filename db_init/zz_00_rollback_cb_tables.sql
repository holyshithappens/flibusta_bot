-- ============================================
-- Откат: Переименование cb_lib* обратно в lib*
-- ============================================
--
-- Использование:
--   mysql -u flibusta -p flibusta < zz_00_rollback_cb_tables.sql
--

--SET NAMES utf8mb3;
--SET CHARACTER SET utf8mb3;
--
SELECT 'Rolling back...' as Status;

DROP TABLE IF EXISTS cb_libbook, cb_libavtor, cb_libavtorname, cb_libgenre,
    cb_libgenrelist, cb_libseq, cb_libseqname, cb_librate, cb_librecs,
    cb_libreviews, cb_libbannotations, cb_libaannotations, cb_libbook_fts,
    cb_libapics, cb_libbpics;
-- Переименование обратно
RENAME TABLE cb_libaannotations_old TO cb_libaannotations;
RENAME TABLE cb_libbook_old TO cb_libbook;
RENAME TABLE cb_libavtor_old TO cb_libavtor;
RENAME TABLE cb_libavtorname_old TO cb_libavtorname;
RENAME TABLE cb_libgenre_old TO cb_libgenre;
RENAME TABLE cb_libgenrelist_old TO cb_libgenrelist;
RENAME TABLE cb_libseq_old TO cb_libseq;
RENAME TABLE cb_libseqname_old TO cb_libseqname;
RENAME TABLE cb_librate_old TO cb_librate;
RENAME TABLE cb_librecs_old TO cb_librecs;
RENAME TABLE cb_libreviews_old TO cb_libreviews;
RENAME TABLE cb_libbannotations_old TO cb_libbannotations;
RENAME TABLE cb_libbook_fts_old TO cb_libbook_fts;

SELECT 'Rollback completed!' as Status;