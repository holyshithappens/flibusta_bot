-- ============================================
-- Copy lib* tables to cb_lib* tables
-- ============================================
--
-- This script COPIES (not renames) existing lib* tables
-- into new cb_lib* tables, preserving the original tables.
--
-- What gets copied with CREATE TABLE ... LIKE:
--   ✅ Column definitions (types, NULL/NOT NULL)
--   ✅ DEFAULT values
--   ✅ AUTO_INCREMENT
--   ✅ PRIMARY KEY
--   ✅ UNIQUE constraints
--   ✅ FOREIGN KEY constraints
--   ✅ ALL INDEXES (including full-text indexes!)
--   ✅ Column comments & collation
--   ✅ Character set
--
-- Use cases:
--   1. Create backup before renaming
--   2. Test migration without losing original data
--   3. Parallel table operation
--   4. Safe copy with full index preservation
--
-- IMPORTANT: Run AFTER creating all indexes (zz_50_repair_FT.sql)
--
-- WARNING: Existing cb_lib* tables will be dropped before copying!
--
-- Usage:
--   mysql -u flibusta -p flibusta < zz_65_copy_lib_to_cb_tables.sql
--
-- Time estimate: 5-30 minutes depending on data size
--

-- ============================================
-- 1. Drop existing cb_lib* tables (if any)
-- ============================================

SET FOREIGN_KEY_CHECKS = 0;

DROP TABLE IF EXISTS cb_libbook_fts;
DROP TABLE IF EXISTS cb_libreviews;
DROP TABLE IF EXISTS cb_librecs;
DROP TABLE IF EXISTS cb_libaannotations;
DROP TABLE IF EXISTS cb_libbannotations;
DROP TABLE IF EXISTS cb_libbpics;
DROP TABLE IF EXISTS cb_libapics;
DROP TABLE IF EXISTS cb_librate;
DROP TABLE IF EXISTS cb_libseqname;
DROP TABLE IF EXISTS cb_libseq;
DROP TABLE IF EXISTS cb_libgenrelist;
DROP TABLE IF EXISTS cb_libgenre;
DROP TABLE IF EXISTS cb_libavtorname;
DROP TABLE IF EXISTS cb_libavtor;
DROP TABLE IF EXISTS cb_libbook;

SET FOREIGN_KEY_CHECKS = 1;

-- ============================================
-- 2. Copy main tables (data + structure)
-- ============================================

CREATE TABLE cb_libbook LIKE libbook;
INSERT INTO cb_libbook SELECT * FROM libbook;

CREATE TABLE cb_libavtor LIKE libavtor;
INSERT INTO cb_libavtor SELECT * FROM libavtor;

CREATE TABLE cb_libavtorname LIKE libavtorname;
INSERT INTO cb_libavtorname SELECT * FROM libavtorname;

CREATE TABLE cb_libgenre LIKE libgenre;
INSERT INTO cb_libgenre SELECT * FROM libgenre;

CREATE TABLE cb_libgenrelist LIKE libgenrelist;
INSERT INTO cb_libgenrelist SELECT * FROM libgenrelist;

CREATE TABLE cb_libseq LIKE libseq;
INSERT INTO cb_libseq SELECT * FROM libseq;

CREATE TABLE cb_libseqname LIKE libseqname;
INSERT INTO cb_libseqname SELECT * FROM libseqname;

CREATE TABLE cb_librate LIKE librate;
INSERT INTO cb_librate SELECT * FROM librate;

-- ============================================
-- 3. Copy optional tables (if they exist)
-- ============================================

-- Reviews table
CREATE TABLE IF NOT EXISTS cb_librecs LIKE librecs;
INSERT INTO cb_librecs SELECT * FROM librecs;

CREATE TABLE IF NOT EXISTS cb_libreviews LIKE libreviews;
INSERT INTO cb_libreviews SELECT * FROM libreviews;

-- Picture tables
CREATE TABLE IF NOT EXISTS cb_libapics LIKE libapics;
INSERT INTO cb_libapics SELECT * FROM libapics;

CREATE TABLE IF NOT EXISTS cb_libbpics LIKE libbpics;
INSERT INTO cb_libbpics SELECT * FROM libbpics;

-- ============================================
-- 4. Copy annotation tables
-- ============================================

CREATE TABLE IF NOT EXISTS cb_libbannotations LIKE libbannotations;
INSERT INTO cb_libbannotations SELECT * FROM libbannotations;

CREATE TABLE IF NOT EXISTS cb_libaannotations LIKE libaannotations;
INSERT INTO cb_libaannotations SELECT * FROM libaannotations;

-- ============================================
-- 5. Copy full-text search table (if exists)
-- ============================================

CREATE TABLE IF NOT EXISTS cb_libbook_fts LIKE libbook_fts;
INSERT INTO cb_libbook_fts SELECT * FROM libbook_fts;

-- ============================================
-- 6. Verification and Statistics
-- ============================================

SELECT '✅ Copy completed!' AS Status;

-- Check table row counts and sizes
SELECT 
    table_name,
    table_rows AS row_count,
    ROUND((data_length + index_length) / 1024 / 1024, 2) AS size_mb
FROM information_schema.tables
WHERE table_schema = 'flibusta' AND table_name LIKE 'cb_lib%'
ORDER BY table_name;

-- Show comparison of row counts between lib* and cb_lib*
SELECT 
    CONCAT('lib', SUBSTR(t1.table_name, 5)) AS lib_table,
    t1.table_name AS cb_table,
    t1.table_rows AS cb_rows,
    t2.table_rows AS lib_rows,
    (t1.table_rows - t2.table_rows) AS row_diff
FROM information_schema.tables t1
LEFT JOIN information_schema.tables t2 ON 
    CONCAT('lib', SUBSTR(t1.table_name, 5)) = t2.table_name AND
    t2.table_schema = 'flibusta'
WHERE t1.table_schema = 'flibusta' AND t1.table_name LIKE 'cb_lib%'
ORDER BY t1.table_name;

-- ============================================
-- 7. Index Verification (Indexes WERE COPIED!)
-- ============================================

-- Verify indexes were copied to cb_libbook
SELECT 
    'cb_libbook indexes:' AS info;

SELECT 
    t.table_name,
    s.index_name,
    s.seq_in_index AS position,
    s.column_name,
    CASE s.index_type
        WHEN 'FULLTEXT' THEN '🔍 FULLTEXT'
        WHEN 'BTREE' THEN '📊 BTREE'
        WHEN 'HASH' THEN '⚡ HASH'
        ELSE s.index_type
    END AS index_type
FROM information_schema.statistics s
JOIN information_schema.tables t ON s.table_schema = t.table_schema AND s.table_name = t.table_name
WHERE t.table_schema = 'flibusta' AND t.table_name IN ('cb_libbook', 'libbook')
ORDER BY t.table_name, s.index_name, s.seq_in_index;

-- Count indexes on both tables
SELECT
    'Index Count Comparison' AS metric;

SELECT
    (SELECT COUNT(DISTINCT index_name) FROM information_schema.statistics 
     WHERE table_schema = 'flibusta' AND table_name = 'libbook') AS libbook_index_count,
    (SELECT COUNT(DISTINCT index_name) FROM information_schema.statistics 
     WHERE table_schema = 'flibusta' AND table_name = 'cb_libbook') AS cb_libbook_index_count;

-- Final status
SELECT '✅ All indexes successfully copied!' AS final_status;
