-- ============================================
-- Database Statistics Report
-- ============================================
-- This script provides comprehensive statistics about all tables and indexes
-- in the flibusta database for monitoring and control purposes
--

-- Database overview
SELECT '=== FLIBUSTA DATABASE STATISTICS REPORT ===' AS ReportTitle;
SELECT NOW() AS ReportGeneratedAt;

-- Table statistics with detailed information
SELECT
    'TABLE STATISTICS' AS Section,
    t.TABLE_NAME AS TableName,
    t.TABLE_ROWS AS RowCount,
    ROUND((t.DATA_LENGTH) / 1024 / 1024, 2) AS DataSizeMB,
    ROUND((t.INDEX_LENGTH) / 1024 / 1024, 2) AS IndexSizeMB,
    ROUND((t.DATA_LENGTH + t.INDEX_LENGTH) / 1024 / 1024, 2) AS TotalSizeMB,
    t.TABLE_COLLATION AS Collation,
    t.CREATE_TIME AS Created,
    t.UPDATE_TIME AS LastUpdated
FROM information_schema.TABLES t
WHERE t.TABLE_SCHEMA = 'flibusta'
ORDER BY t.TABLE_NAME;

-- Index statistics for each table
SELECT
    'INDEX STATISTICS' AS Section,
    s.TABLE_NAME AS TableName,
    s.INDEX_NAME AS IndexName,
    s.NON_UNIQUE AS IsNonUnique,
    s.INDEX_TYPE AS IndexType,
    GROUP_CONCAT(s.COLUMN_NAME ORDER BY s.SEQ_IN_INDEX) AS Columns,
    s.INDEX_COMMENT AS Comment
FROM information_schema.STATISTICS s
WHERE s.TABLE_SCHEMA = 'flibusta'
GROUP BY s.TABLE_NAME, s.INDEX_NAME, s.NON_UNIQUE, s.INDEX_TYPE, s.INDEX_COMMENT
ORDER BY s.TABLE_NAME, s.INDEX_NAME;

-- Summary statistics
SELECT
    'SUMMARY STATISTICS' AS Section,
    COUNT(DISTINCT TABLE_NAME) AS TotalTables,
    SUM(TABLE_ROWS) AS TotalRows,
    ROUND(SUM(DATA_LENGTH) / 1024 / 1024, 2) AS TotalDataSizeMB,
    ROUND(SUM(INDEX_LENGTH) / 1024 / 1024, 2) AS TotalIndexSizeMB,
    ROUND((SUM(DATA_LENGTH) + SUM(INDEX_LENGTH)) / 1024 / 1024, 2) AS TotalDatabaseSizeMB
FROM information_schema.TABLES
WHERE TABLE_SCHEMA = 'flibusta';

-- Fulltext index specific statistics
SELECT
    'FULLTEXT INDEX STATISTICS' AS Section,
    TABLE_NAME AS TableName,
    INDEX_NAME AS FulltextIndexName,
    INDEX_TYPE AS IndexType
FROM information_schema.STATISTICS
WHERE TABLE_SCHEMA = 'flibusta'
AND INDEX_TYPE = 'FULLTEXT'
GROUP BY TABLE_NAME, INDEX_NAME, INDEX_TYPE;

-- Database engine statistics
SELECT
    'ENGINE STATISTICS' AS Section,
    ENGINE AS StorageEngine,
    COUNT(*) AS TableCount,
    SUM(TABLE_ROWS) AS TotalRows,
    ROUND(SUM(DATA_LENGTH + INDEX_LENGTH) / 1024 / 1024, 2) AS TotalSizeMB
FROM information_schema.TABLES
WHERE TABLE_SCHEMA = 'flibusta'
GROUP BY ENGINE;

SELECT '=== END OF STATISTICS REPORT ===' AS ReportEnd;