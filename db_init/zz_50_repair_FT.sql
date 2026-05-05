-- Перестроить FULLTEXT индексы
REPAIR TABLE libbook_fts QUICK;
SELECT 'libbook_fts table repaired' AS OperationStatus;
OPTIMIZE TABLE libbook_fts;
SELECT 'libbook_fts table optimized' AS OperationStatus;

REPAIR TABLE libaannotations QUICK;
SELECT 'libaannotations table repaired' AS OperationStatus;
OPTIMIZE TABLE libaannotations;
SELECT 'libaannotations table optimized' AS OperationStatus;

REPAIR TABLE libbannotations QUICK;
SELECT 'libbannotations table repaired' AS OperationStatus;
OPTIMIZE TABLE libbannotations;
SELECT 'libbannotations table optimized' AS OperationStatus;

SELECT 'All FULLTEXT tables repair and optimization completed' AS OperationStatus;
