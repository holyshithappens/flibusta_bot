-- -- ПОЛНЕТОКСТОВЫЙ ИНДЕКС ДЛЯ ПОИСКА ПО АННОТАЦИИ КНИГ
CREATE FULLTEXT INDEX idx_annotations_body_ft ON libbannotations (Body);

-- -- ПОЛНЕТОКСТОВЫЙ ИНДЕКС ДЛЯ ПОИСКА ПО АННОТАЦИИ АВТОРОВ
CREATE FULLTEXT INDEX idx_author_bio_ft ON libaannotations (Body);
