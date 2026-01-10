-- ============================================
-- Проверка результата
-- ============================================

SELECT
    table_name,
    table_rows,
    ROUND((data_length + index_length) / 1024 / 1024, 2) as size_mb
FROM information_schema.tables
WHERE table_schema = 'flibusta' -- AND table_name LIKE 'cb_lib%'
ORDER BY table_name;