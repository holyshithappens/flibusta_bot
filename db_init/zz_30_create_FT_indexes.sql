-- -- ПОЛНЕТОКСТОВЫЙ ИНДЕКС ДЛЯ ПОИСКА ПО АННОТАЦИИ КНИГ
CREATE FULLTEXT INDEX IF NOT EXISTS idx_annotations_body_ft ON libbannotations (Body);
SELECT 'Fulltext index idx_annotations_body_ft created' AS OperationStatus;

-- -- ПОЛНЕТОКСТОВЫЙ ИНДЕКС ДЛЯ ПОИСКА ПО АННОТАЦИИ АВТОРОВ
CREATE FULLTEXT INDEX IF NOT EXISTS idx_author_bio_ft ON libaannotations (Body);
SELECT 'Fulltext index idx_author_bio_ft created' AS OperationStatus;

SELECT 'All fulltext indexes creation completed' AS OperationStatus;
