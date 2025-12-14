-- -- ПОЛНОТЕКСТОВЫЙ ПОИСК -- --
DROP TABLE IF EXISTS libbook_fts;
CREATE TABLE libbook_fts (
    BookId INT(10) UNSIGNED NOT NULL,
    FT LONGTEXT,
    PRIMARY KEY (BookId),
    FULLTEXT idx_fts_search (FT)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb3 COLLATE=utf8mb3_unicode_ci;

-- truncate table libbook_fts;
INSERT INTO libbook_fts (BookID, FT)
SELECT
    b.BookID,
    CONCAT_WS(' ',
        b.Title,
        -- b.Lang,
        case when b.Year between 1600 and 2100 then b.`Year`
             else ''
        end,
        GROUP_CONCAT(DISTINCT CONCAT_WS(' ', an.LastName, an.FirstName, an.MiddleName)),
        GROUP_CONCAT(DISTINCT sn.SeqName),
        GROUP_CONCAT(DISTINCT gl.GenreDesc)
    ) as FT
FROM libbook b
LEFT JOIN libavtor a ON a.BookID = b.BookID
LEFT JOIN libavtorname an ON a.AvtorID = an.AvtorID
LEFT JOIN libseq s ON s.BookID = b.BookID
LEFT JOIN libseqname sn ON s.SeqID = sn.SeqID
LEFT JOIN libgenre g ON g.BookID = b.BookID
LEFT JOIN libgenrelist gl ON g.GenreID = gl.GenreID
WHERE b.Deleted = '0'
GROUP BY b.BookID -- , b.Title, b.Lang, b.Year
ON DUPLICATE KEY UPDATE FT = VALUES(FT);

