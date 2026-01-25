-- Для libreviews
--DROP INDEX IF EXISTS idx_libreviews_bookid_time_desc ON libreviews;
CREATE INDEX IF NOT EXISTS idx_libreviews_bookid_time_desc ON libreviews (BookId ASC, Time DESC); -- есть дубликаты
SELECT 'Index idx_libreviews_bookid_time_desc created' AS OperationStatus;

-- Для libapics
--DROP INDEX IF EXISTS idx_libapics_avtorid ON libapics;
CREATE INDEX IF NOT EXISTS idx_libapics_avtorid ON libapics (AvtorId ASC); -- есть дубликаты
SELECT 'Index idx_libapics_avtorid created' AS OperationStatus;

-- Для libaannotations
--DROP INDEX IF EXISTS idx_libaannotations_avtorid ON libaannotations;
CREATE INDEX IF NOT EXISTS idx_libaannotations_avtorid ON libaannotations (AvtorId ASC); -- есть дубликаты
SELECT 'Index idx_libaannotations_avtorid created' AS OperationStatus;

-- Для libbannotations
--DROP INDEX IF EXISTS idx_libbannotations_bookid ON libbannotations;
CREATE INDEX IF NOT EXISTS idx_libbannotations_bookid ON libbannotations (BookId ASC); -- есть дубликаты
SELECT 'Index idx_libbannotations_bookid created' AS OperationStatus;

-- Для libbpics
--DROP INDEX IF EXISTS idx_libbpics_bookid ON libbpics;
CREATE INDEX IF NOT EXISTS idx_libbpics_bookid ON libbpics (BookId ASC); -- есть дубликаты
SELECT 'Index idx_libbpics_bookid created' AS OperationStatus;

SELECT 'All indexes creation completed' AS OperationStatus;