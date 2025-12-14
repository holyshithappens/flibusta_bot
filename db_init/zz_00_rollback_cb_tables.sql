-- ============================================
-- Откат: Переименование cb_lib* обратно в lib*
-- ============================================
--
-- Использование:
--   mysql -u flibusta -p flibusta < rollback_cb_tables.sql
--

SET NAMES utf8mb3;
SET CHARACTER SET utf8mb3;

SELECT 'Rolling back...' as Status;

-- Переименование обратно
RENAME TABLE cb_libaannotations TO libaannotations;
RENAME TABLE cb_libbook TO libbook;
RENAME TABLE cb_libavtor TO libavtor;
RENAME TABLE cb_libavtorname TO libavtorname;
RENAME TABLE cb_libgenre TO libgenre;
RENAME TABLE cb_libgenrelist TO libgenrelist;
RENAME TABLE cb_libseq TO libseq;
RENAME TABLE cb_libseqname TO libseqname;
RENAME TABLE cb_librate TO librate;
RENAME TABLE cb_librecs TO librecs;
RENAME TABLE cb_libreviews TO libreviews;
RENAME TABLE cb_libbannotations TO libbannotations;
RENAME TABLE cb_libbook_fts TO libbook_fts;

SELECT 'Rollback completed!' as Status;