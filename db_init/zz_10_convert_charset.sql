-- db_init/sql/00_convert_charset.sql
-- SET FOREIGN_KEY_CHECKS=0;

ALTER DATABASE flibusta CHARACTER SET utf8mb3 COLLATE utf8mb3_unicode_ci;
SELECT 'Database charset converted to utf8mb3' AS OperationStatus;

ALTER TABLE IF EXISTS libbook CONVERT TO CHARACTER SET utf8mb3 COLLATE utf8mb3_unicode_ci;
ALTER TABLE IF EXISTS libavtor CONVERT TO CHARACTER SET utf8mb3 COLLATE utf8mb3_unicode_ci;
ALTER TABLE IF EXISTS libavtorname CONVERT TO CHARACTER SET utf8mb3 COLLATE utf8mb3_unicode_ci;
ALTER TABLE IF EXISTS libseq CONVERT TO CHARACTER SET utf8mb3 COLLATE utf8mb3_unicode_ci;
ALTER TABLE IF EXISTS libseqname CONVERT TO CHARACTER SET utf8mb3 COLLATE utf8mb3_unicode_ci;
ALTER TABLE IF EXISTS libgenre CONVERT TO CHARACTER SET utf8mb3 COLLATE utf8mb3_unicode_ci;
ALTER TABLE IF EXISTS libgenrelist CONVERT TO CHARACTER SET utf8mb3 COLLATE utf8mb3_unicode_ci;
ALTER TABLE IF EXISTS libreviews CONVERT TO CHARACTER SET utf8mb3 COLLATE utf8mb3_unicode_ci;
ALTER TABLE IF EXISTS librecs CONVERT TO CHARACTER SET utf8mb3 COLLATE utf8mb3_unicode_ci;
ALTER TABLE IF EXISTS librate CONVERT TO CHARACTER SET utf8mb3 COLLATE utf8mb3_unicode_ci;
ALTER TABLE IF EXISTS libaannotations CONVERT TO CHARACTER SET utf8mb3 COLLATE utf8mb3_unicode_ci;
ALTER TABLE IF EXISTS libbannotations CONVERT TO CHARACTER SET utf8mb3 COLLATE utf8mb3_unicode_ci;
ALTER TABLE IF EXISTS libapics CONVERT TO CHARACTER SET utf8mb3 COLLATE utf8mb3_unicode_ci;
ALTER TABLE IF EXISTS libbpics CONVERT TO CHARACTER SET utf8mb3 COLLATE utf8mb3_unicode_ci;
--ALTER TABLE libfilename CONVERT TO CHARACTER SET utf8mb3 COLLATE utf8mb3_unicode_ci;
--ALTER TABLE libjoinedbooks CONVERT TO CHARACTER SET utf8mb3 COLLATE utf8mb3_unicode_ci;
--ALTER TABLE libgenretranslate CONVERT TO CHARACTER SET utf8mb3 COLLATE utf8mb3_unicode_ci;
--ALTER TABLE libtranslator CONVERT TO CHARACTER SET utf8mb3 COLLATE utf8mb3_unicode_ci;

SELECT 'All tables charset conversion completed' AS OperationStatus;
-- SET FOREIGN_KEY_CHECKS=1;

