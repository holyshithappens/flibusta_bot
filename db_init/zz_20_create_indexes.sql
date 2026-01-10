-- Для libreviews
CREATE INDEX idx_libreviews_bookid_time_desc ON libreviews (BookId ASC, Time DESC); -- есть дубликаты
SELECT 'Index idx_libreviews_bookid_time_desc created' AS OperationStatus;

-- Для libapics
CREATE INDEX idx_libapics_avtorid ON libapics (AvtorId ASC); -- есть дубликаты
SELECT 'Index idx_libapics_avtorid created' AS OperationStatus;

-- Для libaannotations
CREATE INDEX idx_libaannotations_avtorid ON libaannotations (AvtorId ASC); -- есть дубликаты
SELECT 'Index idx_libaannotations_avtorid created' AS OperationStatus;

-- Для libbannotations
CREATE INDEX idx_libbannotations_bookid ON libbannotations (BookId ASC); -- есть дубликаты
SELECT 'Index idx_libbannotations_bookid created' AS OperationStatus;

-- Для libbpics
CREATE INDEX idx_libbpics_bookid ON libbpics (BookId ASC); -- есть дубликаты
SELECT 'Index idx_libbpics_bookid created' AS OperationStatus;

SELECT 'All indexes creation completed' AS OperationStatus;