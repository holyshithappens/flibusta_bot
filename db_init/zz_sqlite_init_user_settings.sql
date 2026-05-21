-- UserSettings definition

CREATE TABLE IF NOT EXISTS UserSettings (
                    User_ID INTEGER NOT NULL UNIQUE,
                    MaxBooks INTEGER NOT NULL DEFAULT 20,
                    Lang VARCHAR(2) DEFAULT '',
                    DateSortOrder VARCHAR(10) DEFAULT 'DESC',
                    BookFormat VARCHAR(5) DEFAULT 'fb2',
                    LastNewsDate VARCHAR(10) DEFAULT ('2000-01-01'),
                    IsBlocked BOOLEAN DEFAULT (FALSE),
                    BookSize TEXT DEFAULT '',
                    SearchType TEXT DEFAULT 'books',
                    Rating TEXT DEFAULT '',
                    SearchArea TEXT DEFAULT 'b',
                    Locale VARCHAR(5) DEFAULT '',
                    PRIMARY KEY(User_ID)
                );

CREATE UNIQUE INDEX IF NOT EXISTS IXUserSettings_User_ID
                ON UserSettings (User_ID);