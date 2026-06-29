import os
import sqlite3
from collections import namedtuple
from typing import Dict, List, Any, Coroutine

import mysql.connector
from contextlib import contextmanager

from .flibusta_client import FlibustaClient, flibusta_client
from .constants import FLIBUSTA_DB_SETTINGS_PATH, FLIBUSTA_DB_LOGS_PATH, MAX_BOOKS_SEARCH, \
    SETTING_SEARCH_AREA_B, SETTING_SEARCH_AREA_BA, SETTING_SEARCH_AREA_AA, MAX_SERIES_SEARCH, MAX_AUTHORS_SEARCH, \
    POPULARITY_WEIGHT_RATE, POPULARITY_WEIGHT_RECS, POPULARITY_WEIGHT_REVIEWS
from .tools import load_bot_news

# from logger import logger

Book = namedtuple('Book',
                   ['FileName', 'Title', 'LastName', 'FirstName', 'MiddleName', 'Genre', 'BookSize',
                    'SearchYear', 'LibRate', 'SeriesTitle', 'Relevance',
                    'SrcLang', 'TransLastName', 'TransFirstName', 'TransMiddleName', 'TransID'])
UserSettingsType = namedtuple('UserSettingsType',
                              ['User_ID', 'MaxBooks', 'Lang',
                               # 'DateSortOrder',
                               'BookFormat', 'LastNewsDate', 'IsBlocked', 'BookSize', 'SearchType', 'Rating', 'SearchArea',
                               'Locale', 'GenreFilter'])  # User's preferred UI language (empty = auto-detect); GenreFilter = comma-separated genre IDs

# SQL-запросы
# Базовые поля для SELECT
BASE_FIELDS = """
    b.BookID as FileName,
    upper(b.Lang) as SearchLang,
    b.Title,
    b.FileSize as BookSize,
    b.Year as SearchYear,
    case 
      when b.FileSize <= 800 * 1024 then 'less800'
      when b.FileSize > 800 * 1024 then 'more800'
    end as BookSizeCat,  
    an.LastName,
    an.FirstName, 
    an.MiddleName,
    an.AvtorId as AuthorID,
    gl.GenreDesc AS Genre,
    sn.SeqName as SeriesTitle, 
    sn.SeqId as SeriesID, 
    ROUND(COALESCE(r.LibRate, 0)) as LibRate,
    b.SrcLang,
    tn.LastName as TransLastName,
    tn.FirstName as TransFirstName,
    tn.MiddleName as TransMiddleName,
    tn.AvtorId as TransID
"""

# Базовые JOIN (БЕЗ FROM)
def get_base_joins(locale: str = 'ru') -> str:
    """Return base JOINs with locale-aware genre table"""
    genre_table = _get_genre_table(locale)
    return f"""
-- LEFT JOIN (select bookid, min(avtorid) as avtorid from cb_libavtor group by bookid) a ON a.BookID = b.BookID
LEFT JOIN cb_libavtor a ON a.BookID = b.BookID
LEFT JOIN cb_libavtorname an ON an.AvtorID = a.AvtorID
LEFT JOIN cb_libtranslator t ON t.BookID = b.BookID
LEFT JOIN cb_libavtorname tn ON tn.AvtorID = t.TranslatorId
LEFT JOIN (select bookid, min(genreid) as genreid from cb_libgenre group by bookid) g ON g.BookID = b.BookID
-- LEFT JOIN cb_libgenre g ON g.BookID = b.BookID
LEFT JOIN {genre_table} gl ON gl.GenreID = g.GenreID
-- LEFT JOIN (select bookid, min(SeqID) as SeqID from cb_libseq group by bookid) s ON s.BookID = b.BookID
LEFT JOIN cb_libseq s ON s.BookID = b.BookID
LEFT JOIN cb_libseqname sn on sn.SeqID = s.SeqID
LEFT JOIN (
    SELECT BookId, AVG(CAST(Rate AS SIGNED)) as LibRate
    FROM cb_librate 
    GROUP BY BookId
) r ON r.BookId = b.BookId
"""

# Основной полнотекстовый поиск
SQL_QUERY_BOOKS = lambda locale, is_empty=False, genre_filter=None: f"""
select * from (
SELECT 
    {BASE_FIELDS},
    {'1' if is_empty else 'MATCH(fts.FT) AGAINST(%s IN BOOLEAN MODE)'} as Relevance
FROM cb_libbook_fts fts
JOIN cb_libbook b ON b.BookID = fts.BookID
{get_base_joins(locale)}
WHERE b.Deleted = '0'
  {'' if is_empty else 'AND MATCH(fts.FT) AGAINST(%s IN BOOLEAN MODE)'}
  {"AND g.GenreID IN (" + genre_filter + ")" if genre_filter and genre_filter.strip() and all(c.isdigit() or c == ',' for c in genre_filter) else ""}
) as subq 
"""

# Поиск по аннотациям книг
SQL_QUERY_ABOOKS = lambda locale, is_empty=False, genre_filter=None: f"""
select * from (
SELECT 
    {BASE_FIELDS},
    {'1' if is_empty else 'MATCH(ba.Body) AGAINST(%s IN BOOLEAN MODE)'} as Relevance
FROM cb_libbannotations ba
JOIN cb_libbook b ON b.BookID = ba.BookID
{get_base_joins(locale)}
WHERE b.Deleted = '0'
  {'' if is_empty else 'AND MATCH(ba.Body) AGAINST(%s IN BOOLEAN MODE)'}
  {"AND g.GenreID IN (" + genre_filter + ")" if genre_filter and genre_filter.strip() and all(c.isdigit() or c == ',' for c in genre_filter) else ""}
) as subq2
"""

# Поиск по аннотациям авторов
SQL_QUERY_AAUTHORS = lambda locale, is_empty=False, genre_filter=None: f"""
select * from (
SELECT 
    {BASE_FIELDS},
    {'1' if is_empty else 'MATCH(aa.Body) AGAINST(%s IN BOOLEAN MODE)'} as Relevance
FROM cb_libaannotations aa
JOIN cb_libavtor ab ON ab.AvtorId = aa.AvtorId
JOIN cb_libbook b ON b.BookID = ab.BookID
{get_base_joins(locale)}
WHERE b.Deleted = '0'
  AND MATCH(aa.Body) AGAINST(%s IN BOOLEAN MODE)
  {"AND g.GenreID IN (" + genre_filter + ")" if genre_filter and genre_filter.strip() and all(c.isdigit() or c == ',' for c in genre_filter) else ""}
) as subq2
"""

SELECT_SQL_QUERY = {
    SETTING_SEARCH_AREA_B: SQL_QUERY_BOOKS,
    SETTING_SEARCH_AREA_BA: SQL_QUERY_ABOOKS,
    SETTING_SEARCH_AREA_AA: SQL_QUERY_AAUTHORS
}

def _get_genre_table(locale: str) -> str:
    """Return correct genre table based on user's locale"""
    return 'cb_libgenrelist' if locale == 'ru' else 'cb_libgenrelist_en'

STR_WITHOUT_GENRES = lambda locale: '-- Без жанров --' if locale == 'ru' else '-- Without genres --'

SQL_QUERY_PARENT_GENRES_COUNT = lambda locale: f"""
	select coalesce(gl.GenreMeta,'{STR_WITHOUT_GENRES(locale)}'), count(b.BookId)
      from cb_libbook b
        left outer join cb_libgenre g on g.BookId = b.BookId
        left outer join {_get_genre_table(locale)} gl on gl.GenreId = g.GenreId
    where b.Deleted = '0'
      -- AND (#s = '' OR b.Lang = #s)
    group by coalesce(gl.GenreMeta, '{STR_WITHOUT_GENRES(locale)}')
    order by 1
"""

SQL_QUERY_CHILDREN_GENRES_COUNT = lambda locale: f"""
	select gl.GenreDesc, count(g.BookId), 
	  gl.GenreId
      from cb_libbook b
	    left outer join cb_libgenre g on g.BookId = b.BookId 
        left outer join {_get_genre_table(locale)} gl on gl.GenreId = g.GenreId 
    Where 
      b.Deleted = '0'
      and gl.GenreMeta = %s
    group by gl.GenreDesc, gl.GenreId
    order by 1	
"""

SQL_QUERY_LANGS = """
    SELECT Lang, COUNT(Lang) AS count
    FROM cb_libbook b
    where b.Deleted = '0'
    GROUP BY Lang
    ORDER BY count DESC
"""

SQL_QUERY_USER_SETTINGS_GET = """
    SELECT * FROM UserSettings WHERE user_id = ?
"""

SQL_QUERY_USER_SETTINGS_INS_DEFAULT = """
    INSERT INTO UserSettings (user_id) VALUES (?)
"""

SQL_QUERY_USER_SETTINGS_UPD = """
    UPDATE UserSettings SET ? = ? WHERE USER_ID = ?
"""

class Database:
    def __init__(self, db_path):
        self.db_path = db_path
        self._conn = None  # Защищённая переменная для хранения соединения
        # Создаем директорию для БД если не существует
        os.makedirs(os.path.dirname(db_path), exist_ok=True)

    def __enter__(self):
        self.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()

    def connect(self):
        """Устанавливает соединение с базой данных и инициализирует её если нужно"""
        if self._conn is None:
            self._conn = sqlite3.connect(self.db_path)
            # Инициализируем БД при первом подключении
            self._initialize_database()
        return self._conn

    def _initialize_database(self):
        """Базовый метод инициализации (переопределяется в дочерних классах)"""
        pass

    def close(self):
        """
        Закрывает соединение с базой данных, если оно установлено.
        """
        if self._conn is not None:
            self._conn.close()
            self._conn = None

# Класс для работы с БД настроек бота
class DatabaseLogs(Database):
    def __init__(self, db_path = FLIBUSTA_DB_LOGS_PATH):
        super().__init__(db_path)

    # def _initialize_database(self):
    #     """Инициализирует БД логов при первом подключении"""
    #     with self.connect() as conn:
    #         cursor = conn.cursor()
    #
    #         # Создаем таблицу если не существует
    #         cursor.execute("""
    #             CREATE TABLE IF NOT EXISTS UserLog (
    #                 Timestamp VARCHAR(27) NOT NULL,
    #                 UserID INTEGER NOT NULL,
    #                 UserName VARCHAR(50),
    #                 Action VARCHAR(50) COLLATE NOCASE,
    #                 Detail VARCHAR(255) COLLATE NOCASE,
    #                 PRIMARY KEY(Timestamp, UserID)
    #             );
    #         """)
    #
    #         # Создаем индекс если не существует
    #         cursor.execute("""
    #             CREATE INDEX IF NOT EXISTS IXUserLog_UserID_Timestamp
    #             ON UserLog (UserID, Timestamp);
    #         """)
    #
    #         # НОВАЯ ТАБЛИЦА ДЛЯ ДОНАТОВ
    #         cursor.execute("""
    #             CREATE TABLE IF NOT EXISTS UserPayment (
    #                 PaymentID VARCHAR(100) PRIMARY KEY,
    #                 UserID INTEGER NOT NULL,
    #                 UserName VARCHAR(100),
    #                 Amount DECIMAL(15,2) NOT NULL,
    #                 Currency VARCHAR(10) NOT NULL,
    #                 PaymentMethod VARCHAR(50),
    #                 PaymentDate DATETIME NOT NULL,
    #                 PaymentStatus VARCHAR(20) NOT NULL,
    #                 ProviderChargeID VARCHAR(100),
    #                 TelegramPaymentChargeID VARCHAR(100),
    #                 InvoicePayload TEXT,
    #                 ProviderPaymentChargeID VARCHAR(100),
    #                 OrderInfo TEXT,
    #                 ShippingAddress TEXT,
    #                 CreatedAt DATETIME DEFAULT CURRENT_TIMESTAMP,
    #                 UpdatedAt DATETIME DEFAULT CURRENT_TIMESTAMP,
    #
    #                 -- Для возможного возврата
    #                 Refundable BOOLEAN DEFAULT TRUE,
    #                 RefundedAmount DECIMAL(15,2) DEFAULT 0,
    #                 RefundedAt DATETIME,
    #                 RefundReason TEXT,
    #                 RefundTransactionID VARCHAR(100),
    #
    #                 -- Дополнительная информация
    #                 UserLanguage VARCHAR(10),
    #                 UserTimezone VARCHAR(50),
    #                 IPAddress VARCHAR(45),
    #                 UserAgent TEXT
    #             );
    #         """)
    #
    #         # Создаем индексы для быстрого поиска
    #         cursor.execute("""
    #             CREATE INDEX IF NOT EXISTS IXUserPayments_UserID
    #             ON UserPayment (UserID);
    #         """)
    #
    #         conn.commit()

    def log_payment(self, payment_data: dict):
        """
        Логирует информацию о платеже

        Args:
            payment_data: словарь с данными платежа
        """
        with self.connect() as conn:
            cursor = conn.cursor()

            cursor.execute("""
                INSERT OR REPLACE INTO UserPayment (
                    PaymentID, UserID, UserName, Amount, Currency, PaymentMethod,
                    PaymentDate, PaymentStatus, ProviderChargeID, TelegramPaymentChargeID,
                    InvoicePayload, ProviderPaymentChargeID, OrderInfo, ShippingAddress,
                    Refundable, UserLanguage, UserTimezone, IPAddress, UserAgent
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                payment_data.get('payment_id'),
                payment_data.get('user_id'),
                payment_data.get('user_name'),
                payment_data.get('amount'),
                payment_data.get('currency'),
                payment_data.get('payment_method'),
                payment_data.get('payment_date'),
                payment_data.get('payment_status', 'completed'),
                payment_data.get('provider_charge_id'),
                payment_data.get('telegram_payment_charge_id'),
                payment_data.get('invoice_payload'),
                payment_data.get('provider_payment_charge_id'),
                payment_data.get('order_info'),
                payment_data.get('shipping_address'),
                payment_data.get('refundable', True),
                payment_data.get('user_language'),
                payment_data.get('user_timezone'),
                payment_data.get('ip_address'),
                payment_data.get('user_agent')
            ))

            conn.commit()

    def get_payment_stats(self, days: int = 30) -> dict:
        """Получает статистику по платежам"""
        with self.connect() as conn:
            cursor = conn.cursor()

            # Общая статистика
            cursor.execute("""
                SELECT 
                    COUNT(*) as total_payments,
                    SUM(Amount) as total_amount,
                    AVG(Amount) as avg_amount,
                    COUNT(DISTINCT UserID) as unique_donors
                FROM UserPayment 
                WHERE PaymentStatus = 'completed'
                AND PaymentDate >= date('now', ?)
            """, (f'-{days} days',))

            stats = cursor.fetchone()

            return {
                'total_payments': stats[0] or 0,
                'total_amount': float(stats[1] or 0),
                'avg_amount': float(stats[2] or 0),
                'unique_donors': stats[3] or 0
                # 'daily_stats': daily_stats
            }

    def write_user_log(self, timestamp, user_id, user_name, action, detail = ''):
        with self.connect() as conn:
            cursor = conn.cursor()

            cursor.execute(f"""
                INSERT INTO UserLog (Timestamp, UserID, UserName, Action, Detail) 
                VALUES (?, ?, ?, ?, ?)
            """, (timestamp, user_id, user_name, action, detail))

            conn.commit()


    def get_user_stats_period(self, days):
        """Возвращает статистику пользователей за указанный период в днях"""
        with self.connect() as conn:
            cursor = conn.cursor()

            # Новые пользователи за период
            cursor.execute("""
                SELECT COUNT(*) AS NewUsers
                FROM (
                    SELECT UserID, MIN(Timestamp) AS FirstSeen
                    FROM UserLog
                    GROUP BY UserID
                    HAVING date(FirstSeen) >= date('now', ?)
                )
            """, (f'-{days} days',))
            new_users = cursor.fetchone()[0]

            # Активные пользователи за период
            cursor.execute("""
                SELECT COUNT(DISTINCT UserID) AS ActiveUsers
                FROM UserLog
                WHERE date(Timestamp) >= date('now', ?)
            """, (f'-{days} days',))
            active_users = cursor.fetchone()[0]

            # Количество поисков и скачиваний за период
            cursor.execute("""
                SELECT 
                    SUM(CASE WHEN Action LIKE 'searched%' THEN 1 ELSE 0 END) AS TotalSearches,
                    SUM(CASE WHEN Action = 'send file' THEN 1 ELSE 0 END) AS TotalDownloads
                FROM UserLog
                WHERE date(Timestamp) >= date('now', ?)
            """, (f'-{days} days',))
            searches, downloads = cursor.fetchone()

            return {
                'new_users': new_users,
                'active_users': active_users,
                'searches': searches or 0,
                'downloads': downloads or 0
            }


    def get_user_stats_total(self):
        """Возвращает общую статистику пользователей за всё время"""
        with self.connect() as conn:
            cursor = conn.cursor()

            # Общее количество пользователей
            cursor.execute("SELECT COUNT(DISTINCT UserID) AS TotalUniqueUsers FROM UserLog")
            total_users = cursor.fetchone()[0]

            # Активные пользователи всего (кто был активен хотя бы раз)
            cursor.execute("SELECT COUNT(DISTINCT UserID) AS ActiveUsersTotal FROM UserLog")
            active_users_total = cursor.fetchone()[0]

            # Количество поисков и скачиваний всего
            cursor.execute("""
                SELECT 
                    SUM(CASE WHEN Action LIKE 'searched%' THEN 1 ELSE 0 END) AS TotalSearches,
                    SUM(CASE WHEN Action = 'send file' THEN 1 ELSE 0 END) AS TotalDownloads
                FROM UserLog
            """)
            searches_total, downloads_total = cursor.fetchone()

            return {
                'total_users': total_users,
                'active_users_total': active_users_total,
                'searches_total': searches_total or 0,
                'downloads_total': downloads_total or 0
            }


    def get_user_stats_summary(self):
        """Возвращает общую статистику пользователей"""
        stats_week = self.get_user_stats_period(7)
        stats_month = self.get_user_stats_period(30)
        stats_total = self.get_user_stats_total()

        return {
            'total_users': stats_total['total_users'],
            'new_users_week': stats_week['new_users'],
            'active_users_week': stats_week['active_users'],
            'searches_week': stats_week['searches'],
            'downloads_week': stats_week['downloads'],
            'new_users_month': stats_month['new_users'],
            'active_users_month': stats_month['active_users'],
            'searches_month': stats_month['searches'],
            'downloads_month': stats_month['downloads'],
            'active_users_total': stats_total['active_users_total'],
            'searches_total': stats_total['searches_total'],
            'downloads_total': stats_total['downloads_total']
        }


    def get_users_list(self, limit=50, offset=0):
        """Возвращает список пользователей с основной информацией"""
        with self.connect() as conn:
            cursor = conn.cursor()

            cursor.execute("""
                SELECT
                    UserID,
                    MIN(UserName) AS UserName,
                    MAX(datetime(Timestamp)) AS LastSeen,
                    MIN(datetime(Timestamp)) AS FirstSeen,
                    SUM(CASE WHEN Action LIKE 'searched for%' THEN 1 ELSE 0 END) AS TotalSearches,
                    SUM(CASE WHEN Action = 'send file' THEN 1 ELSE 0 END) AS TotalDownloads
                FROM UserLog
                GROUP BY UserID
                ORDER BY LastSeen DESC
                LIMIT ? OFFSET ?
            """, (limit, offset))

            users = []
            for row in cursor.fetchall():
                users.append({
                    'user_id': row[0],
                    'username': row[1] or 'Без имени',
                    'last_seen': row[2],
                    'first_seen': row[3],
                    'total_searches': row[4] or 0,
                    'total_downloads': row[5] or 0
                })

            return users

    def get_user_activity(self, user_id, limit=50):
        """Возвращает историю действий пользователя"""
        with self.connect() as conn:
            cursor = conn.cursor()

            cursor.execute("""
                SELECT datetime(Timestamp), Action, Detail
                FROM UserLog
                WHERE UserID = ?
                ORDER BY Timestamp DESC
                LIMIT ?
            """, (user_id, limit))

            activities = []
            for row in cursor.fetchall():
                activities.append({
                    'timestamp': row[0],
                    'action': row[1],
                    'detail': row[2] or ''
                })

            return activities

    def get_recent_searches(self, limit=20):
        """Возвращает последние поисковые запросы"""
        with self.connect() as conn:
            cursor = conn.cursor()

            cursor.execute("""
                SELECT Detail AS SearchQuery, datetime(Timestamp), UserName
                FROM UserLog
                WHERE Action LIKE 'searched for%'
                ORDER BY Timestamp DESC
                LIMIT ?
            """, (limit,))

            return cursor.fetchall()

    def get_recent_downloads(self, limit=20):
        """Возвращает последние скачивания"""
        with self.connect() as conn:
            cursor = conn.cursor()

            cursor.execute("""
                SELECT Detail AS filename, datetime(Timestamp), UserName
                FROM UserLog
                WHERE Action = 'send file'
                ORDER BY Timestamp DESC
                LIMIT ?
            """, (limit,))

            return cursor.fetchall()

    def get_top_downloads(self, limit=20):
        """Возвращает топ скачанных книг"""
        with self.connect() as conn:
            cursor = conn.cursor()

            cursor.execute("""
                SELECT Detail AS FileName, COUNT(*) AS DownloadCount
                FROM UserLog
                WHERE Action = 'send file'
                GROUP BY Detail
                ORDER BY DownloadCount DESC
                LIMIT ?
            """, (limit,))

            return cursor.fetchall()

    def get_daily_user_stats(self, days=7):
        """Возвращает статистику пользователей по дням"""
        with self.connect() as conn:
            cursor = conn.cursor()

            # Статистика новых пользователей по дням
            cursor.execute("""
                SELECT 
                    date(FirstSeen) as day,
                    COUNT(*) as new_users
                FROM (
                    SELECT UserID, MIN(Timestamp) AS FirstSeen
                    FROM UserLog
                    GROUP BY UserID
                    HAVING date(FirstSeen) >= date('now', ?)
                )
                GROUP BY date(FirstSeen)
                ORDER BY day DESC
            """, (f'-{days} days',))

            new_users_by_day = {}
            for row in cursor.fetchall():
                new_users_by_day[row[0]] = row[1]

            # Статистика активных пользователей по дням
            cursor.execute("""
                SELECT 
                    date(Timestamp) as day,
                    COUNT(DISTINCT UserID) as active_users
                FROM UserLog
                WHERE date(Timestamp) >= date('now', ?)
                GROUP BY date(Timestamp)
                ORDER BY day DESC
            """, (f'-{days} days',))

            active_users_by_day = {}
            for row in cursor.fetchall():
                active_users_by_day[row[0]] = row[1]

            # Статистика поисков и скачиваний по дням
            cursor.execute("""
                SELECT 
                    date(Timestamp) as day,
                    SUM(CASE WHEN Action LIKE 'searched for%' THEN 1 ELSE 0 END) as searches,
                    SUM(CASE WHEN Action = 'send file' THEN 1 ELSE 0 END) as downloads
                FROM UserLog
                WHERE date(Timestamp) >= date('now', ?)
                GROUP BY date(Timestamp)
                ORDER BY day DESC
            """, (f'-{days} days',))

            searches_by_day = {}
            downloads_by_day = {}
            for row in cursor.fetchall():
                searches_by_day[row[0]] = row[1] or 0
                downloads_by_day[row[0]] = row[2] or 0

            # Формируем полный список дней
            import datetime
            dates = []
            for i in range(days):
                date = (datetime.datetime.now() - datetime.timedelta(days=i)).strftime('%Y-%m-%d')
                dates.append(date)

            # Заполняем данные для всех дней (даже если их нет в БД)
            result = {
                'dates': dates,
                'new_users': [new_users_by_day.get(date, 0) for date in dates],
                'active_users': [active_users_by_day.get(date, 0) for date in dates],
                'searches': [searches_by_day.get(date, 0) for date in dates],
                'downloads': [downloads_by_day.get(date, 0) for date in dates]
            }

            return result

    def get_top_searches(self, limit=20):
        """Возвращает топ поисковых запросов"""
        with self.connect() as conn:
            cursor = conn.cursor()

            cursor.execute("""
                SELECT 
                    Detail AS SearchQuery, 
                    COUNT(*) AS SearchCount,
                    COUNT(DISTINCT UserID) AS UniqueUsers
                FROM UserLog
                WHERE Action LIKE 'searched for%' AND Detail NOT LIKE '%count:0'
                GROUP BY Detail
                ORDER BY SearchCount DESC
                LIMIT ?
            """, (limit,))

            top_searches = []
            for row in cursor.fetchall():
                top_searches.append({
                    'query': row[0],
                    'count': row[1],
                    'unique_users': row[2]
                })

            return top_searches

    def get_user_by_id(self, user_id):
        """Возвращает информацию о конкретном пользователе по ID"""
        with self.connect() as conn:
            cursor = conn.cursor()

            cursor.execute("""
                SELECT
                    UserID,
                    MIN(UserName) AS UserName,
                    MAX(datetime(Timestamp)) AS LastSeen,
                    MIN(datetime(Timestamp)) AS FirstSeen,
                    SUM(CASE WHEN Action LIKE 'searched for%' THEN 1 ELSE 0 END) AS TotalSearches,
                    SUM(CASE WHEN Action = 'send file' THEN 1 ELSE 0 END) AS TotalDownloads
                FROM UserLog
                WHERE UserID = ?
                GROUP BY UserID
            """, (user_id,))

            row = cursor.fetchone()
            if row:
                return {
                    'user_id': row[0],
                    'username': row[1] or 'Без имени',
                    'last_seen': row[2],
                    'first_seen': row[3],
                    'total_searches': row[4] or 0,
                    'total_downloads': row[5] or 0
                }
            return None


# Класс для работы с БД пользовательских настроек бота
class DatabaseSettings(Database):

    def __init__(self, db_path = FLIBUSTA_DB_SETTINGS_PATH):
        super().__init__(db_path)
        # self._ensure_locale_column()

    # def _ensure_locale_column(self):
    #     """Ensures the Locale column exists in UserSettings table (migration for existing DBs)."""
    #     try:
    #         with self.connect() as conn:
    #             cursor = conn.cursor()
    #             # Check if Locale column exists
    #             cursor.execute("PRAGMA table_info(UserSettings)")
    #             columns = [col[1] for col in cursor.fetchall()]
    #
    #             if 'Locale' not in columns:
    #                 # Add Locale column with empty string default
    #                 cursor.execute("ALTER TABLE UserSettings ADD COLUMN Locale VARCHAR(5) DEFAULT ''")
    #                 conn.commit()
    #     except Exception as e:
    #         # Log but don't fail - column might already exist or table might be empty
    #         print(f"Note: Could not add Locale column (may already exist): {e}")

    # def _initialize_database(self):
    #     """Инициализирует БД настроек при первом подключении"""
    #     with self.connect() as conn:
    #         cursor = conn.cursor()
    #
    #         # Создаем таблицу если не существует
    #         cursor.execute("""
    #             CREATE TABLE IF NOT EXISTS UserSettings (
    #                 User_ID INTEGER NOT NULL UNIQUE,
    #                 MaxBooks INTEGER NOT NULL DEFAULT 20,
    #                 Lang VARCHAR(2) DEFAULT '',
    #                 DateSortOrder VARCHAR(10) DEFAULT 'DESC',
    #                 BookFormat VARCHAR(5) DEFAULT 'fb2',
    #                 LastNewsDate VARCHAR(10) DEFAULT '2000-01-01',
    #                 IsBlocked BOOLEAN DEFAULT FALSE,
    #                 BookSize TEXT DEFAULT '',
    #                 SearchType TEXT DEFAULT 'books',
    #                 Rating TEXT DEFAULT '',
    #                 SearchArea TEXT DEFAULT 'b',
    #                 Locale VARCHAR(5) DEFAULT '',
    #                 PRIMARY KEY(User_ID)
    #             );
    #         """)
    #
    #         # Создаем индекс если не существует
    #         cursor.execute("""
    #             CREATE UNIQUE INDEX IF NOT EXISTS IXUserSettings_User_ID
    #             ON UserSettings (User_ID);
    #         """)
    #
    #         conn.commit()

    def get_user_settings(self,user_id):
        """
        Получает настройки пользователя из базы данных.
        """
        fields = UserSettingsType._fields
        processed_fields = [field for field in fields]
        select_fields = ', '.join(processed_fields)

        with self.connect() as conn:
            cursor = conn.cursor()
            cursor.execute(f"SELECT {select_fields} FROM UserSettings WHERE user_id = ?", (user_id,))
            settings = cursor.fetchone()
            # Если настроек нет, добавляем значения по умолчанию
            if not settings:
                cursor.execute("INSERT INTO UserSettings (user_id) VALUES (?)", (user_id,))
                conn.commit()
                cursor.execute(f"SELECT {select_fields} FROM UserSettings WHERE user_id = ?", (user_id,))
                settings = cursor.fetchone()
        return UserSettingsType(*settings)

    def get_all_user_ids(self) -> list[int]:
        """Returns all user_id values from UserSettings."""
        with self.connect() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT User_ID FROM UserSettings")
            return [row[0] for row in cursor.fetchall()]

    def update_user_settings(self, user_id, **kwargs):
        """
        Обновляет настройки пользователя в базе данных.
        """
        with self.connect() as conn:
            cursor = conn.cursor()

            # Формируем SQL-запрос для обновления настроек
            set_clause = ", ".join([f"{key} = ?" for key in kwargs])
            values = list(kwargs.values()) + [user_id]

            cursor.execute(f"""
                UPDATE UserSettings
                SET {set_clause}
                WHERE user_id = ?
            """, values)

            conn.commit()

    def update_last_news_date(self, user_id: int, date: str) -> None:
        """
        Updates the LastNewsDate for a specific user.

        Args:
            user_id: The ID of the user.
            date: The date string (YYYY-MM-DD).
        """
        self.update_user_settings(user_id, LastNewsDate=date)

    # def get_user_stats(self):
    #     """Возвращает статистику пользователей"""
    #     with self.connect() as conn:
    #         cursor = conn.cursor()
    #
    #         # Общая статистика
    #         cursor.execute("""
    #             SELECT
    #                 COUNT(*) as total_users,
    #                 SUM(CASE WHEN IsBlocked THEN 1 ELSE 0 END) as blocked_users,
    #                 SUM(CASE WHEN LastNewsDate > '2000-01-01' THEN 1 ELSE 0 END) as active_users
    #             FROM UserSettings
    #         """)
    #         stats = cursor.fetchone()
    #
    #         return {
    #             'total_users': stats[0],
    #             'blocked_users': stats[1],
    #             'active_users': stats[2]
    #         }



# Класс для работы с БД библиотеки
class DatabaseBooks():
    _class_cached_langs = None
    _class_cached_parent_genres = {}
    _class_cached_genres = {}  # Словарь для кеширования жанров по родительским категориям
    _class_stats = {}  # Статистика по библиотеке

    def __init__(self, db_config):
        self.db_config = db_config
        self._connection = None

    @contextmanager
    def connect(self):
        """Устанавливает соединение с MariaDB"""
        conn = mysql.connector.connect(**self.db_config)
        try:
            yield conn
        finally:
            conn.close()


    @property
    def lib_last_update(self):
        return self.get_library_stats().get('last_update')

    def get_max_book_id(self) -> int | None:
        """Get current maximum book ID from database (bypasses cache)."""
        try:
            with self.connect() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT MAX(bookid) FROM cb_libbook WHERE Deleted = '0'
                """)
                result = cursor.fetchone()
                return result[0] if result and result[0] is not None else None
        except Exception as e:
            # logger.log_system_action("Failed to get max book ID", str(e))
            return None

    def get_library_stats(self):
        """Возвращает статистику библиотеки"""
        try:
            if not DatabaseBooks._class_stats:
                with self.connect() as conn:
                    cursor = conn.cursor()

                    # Статистика книг
                    cursor.execute("""
                        SELECT
                            MAX(date(time)) as max_update_date,
                            COUNT(*) as books_cnt,
                            MAX(bookid) as max_filename
                        FROM cb_libbook b
                        where b.Deleted = '0'
                    """)
                    books_stats = cursor.fetchone()

                    # Количество авторов
                    # cursor.execute("SELECT COUNT(*) FROM cb_libavtorname")
                    cursor.execute("SELECT COUNT(DISTINCT AvtorID) FROM cb_libavtor")
                    authors_cnt = cursor.fetchone()[0]

                    # Количество переводчиков
                    cursor.execute("SELECT COUNT(DISTINCT TranslatorID) FROM cb_libtranslator")
                    translators_cnt = cursor.fetchone()[0]

                    # Количество жанров
                    cursor.execute("SELECT COUNT(*) FROM cb_libgenrelist")
                    genres_cnt = cursor.fetchone()[0]

                    # Количество серий
                    cursor.execute("SELECT COUNT(*) FROM cb_libseqname")
                    series_cnt = cursor.fetchone()[0]

                    # Количество языков
                    cursor.execute("SELECT COUNT(DISTINCT Lang) FROM cb_libbook WHERE Deleted = '0'")
                    langs_cnt = cursor.fetchone()[0]

                    DatabaseBooks._class_stats = {
                        'last_update': books_stats[0],
                        'books_count': books_stats[1],
                        'max_filename': books_stats[2],
                        'authors_count': authors_cnt,
                        'translators_count': translators_cnt,
                        'genres_count': genres_cnt,
                        'series_count': series_cnt,
                        'languages_count': langs_cnt
                    }

            return DatabaseBooks._class_stats

        except Exception as e:
            print(f"Error getting library stats: {e}")
            return {
                'last_update': None,
                'books_count': 0,
                'max_filename': 'N/A',
                'authors_count': 0,
                'translators_count': 0,
                'genres_count': 0,
                'series_count': 0,
                'languages_count': 0
            }


    def get_parent_genres_count(self, locale: str = 'ru'):
        """Получает родительские жанры с кешированием"""
        cache_key = locale
        if cache_key not in DatabaseBooks._class_cached_parent_genres:
            with self.connect() as conn:
                cursor = conn.cursor(buffered=True)
                cursor.execute(SQL_QUERY_PARENT_GENRES_COUNT(locale))
                DatabaseBooks._class_cached_parent_genres[cache_key] = cursor.fetchall()
        return DatabaseBooks._class_cached_parent_genres[cache_key]


    # def get_parent_genres_count(self, locale: str = 'ru'):
    #     """Получает родительские жанры с учётом локали"""
    #     query = SQL_QUERY_PARENT_GENRES_COUNT(locale)
    #     with self.connect() as conn:
    #         cursor = conn.cursor(buffered=True)
    #         cursor.execute(query)
    #         return cursor.fetchall()


    def get_genres_with_counts(self, parent_genre, locale: str = 'ru'):
        # cache_key = (parent_genre, locale)
        # print(f"[DEBUG] parent_genre={parent_genre}, locale={locale}")
        if locale not in DatabaseBooks._class_cached_genres or not DatabaseBooks._class_cached_genres[locale]:
            self.load_all_child_genres_cache(locale)
            # print(f"[DEBUG] _class_cached_genres={DatabaseBooks._class_cached_genres[cache_key]}")
        # if cache_key not in DatabaseBooks._class_cached_genres:
        #     with self.connect() as conn:
        #         cursor = conn.cursor(buffered=True)
        #         cursor.execute(SQL_QUERY_CHILDREN_GENRES_COUNT(locale), (parent_genre,))
        #         DatabaseBooks._class_cached_genres[cache_key] = cursor.fetchall()
        return DatabaseBooks._class_cached_genres[locale][parent_genre]

    def load_all_child_genres_cache(self, locale: str = 'ru'):
        """Preloads child genres for all parent genres into cache for the given locale."""
        # If we already have any cached data for this locale, assume it's already loaded
        if locale in DatabaseBooks._class_cached_genres and DatabaseBooks._class_cached_genres[locale]:
            return
        else:
            DatabaseBooks._class_cached_genres[locale] = {}
        # Localized string for null genre
        null_genre_str = STR_WITHOUT_GENRES(locale)
        sql = f"""
            SELECT 
                COALESCE(gl.GenreMeta, %s) AS parent,
                gl.GenreDesc AS child_desc,
                COUNT(g.BookId) AS count,
                gl.GenreId AS genre_id
            FROM cb_libbook b
            LEFT JOIN cb_libgenre g ON g.BookId = b.BookId
            LEFT JOIN {_get_genre_table(locale)} gl ON gl.GenreId = g.GenreId
            WHERE b.Deleted = '0'
            GROUP BY COALESCE(gl.GenreMeta, %s), gl.GenreDesc, gl.GenreId
            ORDER BY parent, gl.GenreDesc
        """
        params = (null_genre_str, null_genre_str)
        with self.connect() as conn:
            cursor = conn.cursor(buffered=True)
            cursor.execute(sql, params)
            rows = cursor.fetchall()
        # Group by parent
        grouped = {}
        for parent, child_desc, count, genre_id in rows:
            if parent not in grouped:
                grouped[parent] = []
            grouped[parent].append((child_desc, count, genre_id))
        # Update class cache
        for parent_genre, child_list in grouped.items():
            DatabaseBooks._class_cached_genres[locale][parent_genre] = child_list


    def get_langs(self):
        """Получает языки с кешированием"""
        if DatabaseBooks._class_cached_langs is None:
            with self.connect() as conn:
                cursor = conn.cursor(buffered=True)
                cursor.execute(SQL_QUERY_LANGS)
                DatabaseBooks._class_cached_langs = cursor.fetchall()
        return DatabaseBooks._class_cached_langs


    def search_books(self, query, lang, size_limit, rating_filter=None, search_area=SETTING_SEARCH_AREA_B, series_id=0,
                     author_id=0, person_type='author',
                     locale: str = 'ru', genre_filter=None):
        """Ищем книги по запросу пользователя"""
        is_empty = not query
        sql_where = self.build_sql_where_ft(lang, size_limit, rating_filter, series_id, author_id, person_type)
        # Строим запросы для поиска книг и подсчёта количества найденных книг
        sql_query = self.build_sql_query_books(sql_where, 'desc', search_area, locale, is_empty, genre_filter)

        params = []
        # Пара одинаковых параметров в виде полного запроса для FullText поиска
        if not is_empty:
            params.extend([query] * 2)

        # #DEBUG
        # print(f"[DEBUG] search_books, sql_query = {sql_query}")
        # print(f"[DEBUG] params = {params}")

        # выполняем запросы поиска книг и подсчёта количества найденных книг
        with self.connect() as conn:
            cursor = conn.cursor(buffered=True)
            cursor.execute(sql_query, params)
            books = [Book(*row) for row in cursor.fetchall()]

        return books


    async def get_book_info(self, book_id, locale: str = 'ru'):
        """Получает основную информацию о книге"""
        genre_table = _get_genre_table(locale)
        with self.connect() as conn:
            cursor = conn.cursor(buffered=True)
            cursor.execute(f"""
                SELECT b.Title, b.Year, b.SrcLang, sn.SeqName,
                       GROUP_CONCAT(DISTINCT CONCAT(gl.GenreID, ',', gl.GenreDesc) SEPARATOR ',') as Genres,
                       GROUP_CONCAT(DISTINCT CONCAT(an.AvtorID, ',', an.LastName, ' ', an.FirstName, ' ', an.MiddleName) SEPARATOR ',') as Authors,
                       GROUP_CONCAT(DISTINCT CONCAT(tn.AvtorID, ',', tn.LastName, ' ', tn.FirstName, ' ', tn.MiddleName) SEPARATOR ',') as Translators,
                       bp.File, b.FileSize, b.Pages, b.Lang, r.LibRate, b.BookId,
                       sn.SeqID
                FROM cb_libbook b
                LEFT JOIN cb_libavtor a ON a.BookID = b.BookID
                LEFT JOIN cb_libavtorname an ON a.AvtorID = an.AvtorID
                LEFT JOIN cb_libtranslator t ON t.BookID = b.BookID
                LEFT JOIN cb_libavtorname tn ON t.TranslatorID = tn.AvtorID
                LEFT JOIN cb_libseq s ON s.BookID = b.BookID
                LEFT JOIN cb_libseqname sn ON s.SeqID = sn.SeqID
                LEFT JOIN cb_libgenre g ON g.BookID = b.BookID
                LEFT JOIN {genre_table} gl ON g.GenreID = gl.GenreID
                LEFT JOIN cb_libbpics bp ON b.BookID = bp.BookID
                left outer join ( 
                    select 
                        r.BookId, 
                        avg(cast(r.Rate as signed)) as Librate
                    from cb_librate r 
                    group by r.BookId 
                    ) r on r.BookId = b.BookId
                WHERE b.BookID = %s
                GROUP BY b.Title, b.Year, b.SrcLang, sn.SeqName, bp.File, b.FileSize, b.Pages, b.Lang
            """, (book_id,))
            result = cursor.fetchone()
            cover_url = FlibustaClient.get_cover_url_direct(result[7]) if result[7] else None
            # print(f"DEBUG: cover_url = {cover_url}")
            # Получение ссылки на обложку со страницы книги, если нет в БД
            if cover_url is None:
                cover_url = await flibusta_client.get_book_cover_url(book_id)
                # print(f"DEBUG: cover_url = {cover_url}")

            return {
                'title': result[0],      # b.Title
                'year': result[1],       # b.Year
                'src_lang': result[2],   # b.SrcLang
                'series': result[3],     # sn.SeqName
                'genres': result[4],     # Genres
                'authors': result[5],    # Authors
                'translators': result[6],# Translators
                'cover_url': cover_url,  # bp.File (processed above)
                'size': result[8],       # b.FileSize
                'pages': result[9],      # b.Pages
                'lang': result[10],      # b.Lang
                'rate': result[11],      # r.LibRate
                'bookid': result[12],    # b.BookId
                'seqid': result[13],     # sn.SeqID
            } if result else None

    async def get_book_details(self, book_id):
        """Получает детальную информацию о книге с обложкой и аннотацией"""
        with self.connect() as conn:
            cursor = conn.cursor(buffered=True)

            # Получаем аннотацию
            cursor.execute("""
                SELECT b.title, ba.Body FROM cb_libbannotations ba 
                INNER JOIN cb_libbook b ON ba.BookId = b.BookId
                WHERE ba.BookID = %s
                """, (book_id,))
            annotation_result = cursor.fetchone()

            return {
                'title': annotation_result[0],
                'annotation': annotation_result[1]
            } if annotation_result else None

    @classmethod
    def build_sql_query_series(cls, sql_query_nested, sql_where) -> str:
        """Сбор sql запроса для поиска серий"""
        return f"""
        SELECT 
            SeriesTitle, 
            SeriesID,
            COUNT(DISTINCT FileName) as book_count
        FROM ({sql_query_nested} 
          ORDER BY relevance DESC) as subquery
        {sql_where}
          and SeriesTitle IS NOT NULL
        GROUP BY SeriesTitle, SeriesID 
        ORDER BY book_count DESC, SeriesTitle
        LIMIT {MAX_SERIES_SEARCH}
        """

    def search_series(self, query, lang, size_limit, rating_filter=None, search_area=SETTING_SEARCH_AREA_B, series_id=0, author_id=0, locale: str = 'ru', genre_filter=None):
        """Ищет серии по запросу"""
        sql_where = self.build_sql_where_ft(lang, size_limit, rating_filter)

        params = []
        # Пара одинаковых параметров в виде полного запроса для FullText поиска
        params.extend([query] * 2)

        # запрос для поиска серий
        sql_query_nested = SELECT_SQL_QUERY.get(search_area)(locale, False, genre_filter)
        sql_query = self.build_sql_query_series(sql_query_nested, sql_where)

        # #DEBUG
        # print(f"DEBUG: sql_query = {sql_query}")
        # print(f"DEBUG: params = {params}")

        with self.connect() as conn:
            cursor = conn.cursor(buffered=True)
            cursor.execute(sql_query, params)
            series = cursor.fetchall()

        return series


    async def get_authors_id(self, book_id: int) -> list[ int | None | Any] | None:
        """Получает ID авторов книги"""
        with self.connect() as conn:
            cursor = conn.cursor(buffered=True)

            # Получаем id всех авторов книги
            cursor.execute("""
                SELECT DISTINCT a.AvtorID 
                FROM cb_libavtor a 
                WHERE a.BookID = %s
            """, (book_id,))
            author_result = cursor.fetchall()

            if not author_result:
                return None
            else:
                return [author_id[0] for author_id in author_result]


    async def get_translators_id(self, book_id: int) -> list[int | None | Any] | None:
        """Получает ID переводчиков книги"""
        with self.connect() as conn:
            cursor = conn.cursor(buffered=True)

            cursor.execute("""
                SELECT DISTINCT t.TranslatorID 
                FROM cb_libtranslator t 
                WHERE t.BookID = %s
            """, (book_id,))
            translator_result = cursor.fetchall()

            if not translator_result:
                return None
            else:
                return [translator_id[0] for translator_id in translator_result]


    async def get_author_info(self, author_id: int) -> dict[str, str | None | Any] | None:
        """Получает информацию об авторе книги"""
        with self.connect() as conn:
            cursor = conn.cursor(buffered=True)

            # Получаем первого автора книги
            cursor.execute("""
                SELECT an.AvtorID, an.LastName, an.FirstName, an.MiddleName 
                -- FROM cb_libavtor a 
                -- JOIN cb_libavtorname an ON a.AvtorID = an.AvtorID 
                FROM cb_libavtorname an
                WHERE an.AvtorID = %s
                LIMIT 1
            """, (author_id,))
            author_result = cursor.fetchone()

            if not author_result:
                return None

            # Получаем фото автора
            cursor.execute("SELECT File FROM cb_libapics WHERE AvtorID = %s", (author_id,))
            photo_result = cursor.fetchone()
            photo_url = FlibustaClient.get_author_photo_url(photo_result[0]) if photo_result else None

            # Получаем аннотацию автора
            cursor.execute("SELECT title, Body FROM cb_libaannotations WHERE AvtorID = %s", (author_id,))
            annotation_result = cursor.fetchone()

            return {
                'name': f"{author_result[1]} {author_result[2]} {author_result[3]}",
                'photo_url': photo_url,
                'title': annotation_result[0],
                'biography': annotation_result[1],
                'author_id': author_result[0]
            } if annotation_result else None


    async def get_book_reviews(self, book_id):
        """Получает отзывы о книге"""
        with self.connect() as conn:
            cursor = conn.cursor(buffered=True)
            cursor.execute("""
                SELECT Name, Time, Text 
                FROM cb_libreviews 
                WHERE BookID = %s 
                ORDER BY Time DESC
            """, (book_id,))
            return cursor.fetchall()

    @classmethod
    def build_sql_query_authors(cls,sql_query_nested, sql_where) -> str:
        """Собирает SQL запрос поиска авторов и переводчиков"""
        return f"""
        SELECT
            CONCAT(COALESCE(LastName, ''), ' ', COALESCE(FirstName, ''), ' ', COALESCE(MiddleName, '')) as AuthorName,
            COUNT(DISTINCT FileName) as book_count,
            AuthorID,
            PersonType
        FROM (
            -- Authors
            SELECT
                LastName,
                FirstName,
                MiddleName,
                FileName,
                AuthorID,
                'author' as PersonType,
                SearchLang,
                BookSizeCat,
                LibRate
            FROM ({sql_query_nested}) as subquery
            WHERE (LastName <> '' OR FirstName <> '' OR MiddleName <> '')
            
            UNION ALL
            
            -- Translators
            SELECT
                TransLastName as LastName,
                TransFirstName as FirstName,
                TransMiddleName as MiddleName,
                FileName,
                TransID as AuthorID,
                'translator' as PersonType,
                SearchLang,
                BookSizeCat,
                LibRate
            FROM ({sql_query_nested}) as subquery
            WHERE (TransLastName <> '' OR TransFirstName <> '' OR TransMiddleName <> '')
        ) combined
        {sql_where}
        GROUP BY AuthorName, AuthorID, PersonType
        ORDER BY book_count DESC, AuthorName
        LIMIT {MAX_AUTHORS_SEARCH}
        """

    def search_authors(self, query, lang, size_limit, rating_filter=None, search_area=SETTING_SEARCH_AREA_B, series_id=0, author_id=0, locale: str = 'ru', genre_filter=None):
        """Ищет авторов по запросу"""
        sql_where = self.build_sql_where_ft(lang, size_limit, rating_filter)

        params = []
        # Пара одинаковых параметров в виде полного запроса для FullText поиска
        params.extend([query] * 4)

        # Модифицируем запрос для поиска авторов
        sql_query_nested = SELECT_SQL_QUERY.get(search_area)(locale, False, genre_filter)
        sql_query = self.build_sql_query_authors(sql_query_nested, sql_where)

        # print(f"[DEBUG] search_authors, sql_query={sql_query}")

        with self.connect() as conn:
            cursor = conn.cursor(buffered=True)
            cursor.execute(sql_query, params)
            authors = cursor.fetchall()

        return authors

    def search_pop_books(self, lang, size_limit, rating_filter=None, days_back: int = 0, locale: str = 'ru',
                         genre_filter=None):
        """Поиск популярных книг за период"""
        # assert lang.isalpha() and len(lang) <= 3, "Invalid lang"

        # sql_where = self.build_sql_where_ft(lang, size_limit, rating_filter)
        # Build filter conditions - using actual table columns, not aliases
        conditions = ["b.Deleted = '0'"]

        if lang:
            conditions.append(f"b.Lang = '{lang.lower()}'")

        # Size filter uses actual FileSize column, not BookSizeCat alias
        if size_limit:
            if size_limit == 'less800':
                conditions.append("b.FileSize <= 819200")  # 800 * 1024
            elif size_limit == 'more800':
                conditions.append("b.FileSize > 819200")

        # Rating filter uses actual LibRate from joined table, not alias
        if rating_filter and rating_filter != '':
            conditions.append(f"ROUND(COALESCE(r.LibRate, 0)) IN ({rating_filter})")

        # Genre filter — uses g.GenreID from cb_libgenre table (joined via get_base_joins)
        if genre_filter and genre_filter.strip():
            if all(c.isdigit() or c == ',' for c in genre_filter):
                conditions.append(f"g.GenreID IN ({genre_filter})")

        sql_where = " AND ".join(conditions)

        if days_back == 0:
            # Поиск новинок
            sql_query_nested = DatabaseBooks.build_sql_query_nov(sql_where, locale)
        else:
            # Поиск популярных
            filter_recent = 1 if days_back < 999 else 0
            current_date = self.lib_last_update
            sql_query_nested = DatabaseBooks.build_sql_query_pop(filter_recent, current_date, sql_where, days_back, locale)

        select_fields = ', '.join(Book._fields)

        sql_query = f"""
        SELECT {select_fields} FROM (
        -- SELECT /BASE_FIELDS/
            -- , b.relevance
            -- , ROW_NUMBER() OVER (PARTITION BY b.BookId ORDER BY b.BookId) AS rn 
        -- FROM ( /sql_query_nested/ ) b
        -- /BASE_JOINS/ 
        {sql_query_nested} ) subq
        -- /sql_where/ 
        -- and rn = 1
        where rn = 1
        ORDER BY relevance DESC
        LIMIT {MAX_BOOKS_SEARCH};
        """

        # print(f"DEBUG: {sql_query}")

        with self.connect() as conn:
            cursor = conn.cursor(buffered=True)
            cursor.execute(sql_query)
            books = [Book(*row) for row in cursor.fetchall()]

        return books

    # def search_pop_series(self, lang, size_limit, rating_filter=None, days_back:int=0):
    #     """Поиск популярных книг по сериям за период"""
    #     # assert lang.isalpha() and len(lang) <= 3, "Invalid lang"
    #
    #     sql_where = self.build_sql_where_ft(lang, size_limit, rating_filter)
    #     if days_back == 0:
    #         # Поиск новинок
    #         sql_query_nested = DatabaseBooks.build_sql_query_nov(self)
    #     else:
    #         # Поиск популярных
    #         filter_recent = 1 if days_back < 999 else 0
    #         current_date = self.lib_last_update
    #         sql_query_nested = DatabaseBooks.build_sql_query_pop(self, filter_recent, current_date, days_back)
    #
    #     sql_query_nested2 = f"""
    #     SELECT {BASE_FIELDS}
    #         , b.relevance
    #     FROM ( {sql_query_nested} ) b
    #     {BASE_JOINS}
    #     """
    #
    #     sql_query = self.build_sql_query_series(sql_query_nested2, sql_where)
    #
    #     with self.connect() as conn:
    #         cursor = conn.cursor(buffered=True)
    #         cursor.execute(sql_query)
    #         series = cursor.fetchall()
    #
    #     return series

    # def search_pop_authors(self, lang, size_limit, rating_filter=None, days_back:int=0):
    #     """Поиск популярных книг по авторам за период"""
    #     # assert lang.isalpha() and len(lang) <= 3, "Invalid lang"
    #
    #     sql_where = self.build_sql_where_ft(lang, size_limit, rating_filter)
    #     if days_back == 0:
    #         # Поиск новинок
    #         sql_query_nested = DatabaseBooks.build_sql_query_nov(self)
    #     else:
    #         # Поиск популярных
    #         filter_recent = 1 if days_back < 999 else 0
    #         current_date = self.lib_last_update
    #         sql_query_nested = DatabaseBooks.build_sql_query_pop(self, filter_recent, current_date, days_back)
    #
    #     sql_query_nested2 = f"""
    #     SELECT {BASE_FIELDS}
    #         , b.relevance
    #     FROM ( {sql_query_nested} ) b
    #     {BASE_JOINS}
    #     """
    #
    #     sql_query = self.build_sql_query_authors(sql_query_nested2, sql_where)
    #
    #     with self.connect() as conn:
    #         cursor = conn.cursor(buffered=True)
    #         cursor.execute(sql_query)
    #         authors = cursor.fetchall()
    #
    #     return authors

    @staticmethod
    def build_sql_query_pop(filter_recent: int, current_date: str, sql_where: str, days_back: int, locale: str = 'ru'):
        """Build SQL query for popular books with weighted scoring.

        Popularity formula:
        - All-time (filter_recent=0): (rate_count * W_RATE) + (recs_count * W_RECS) + (reviews_count * W_REVIEWS)
        - Recent (filter_recent=1): (recs_count * W_RECS) + (reviews_count * W_REVIEWS)

        Weights are defined in constants.py for easy customization.

        Args:
            filter_recent: 0 for all-time popularity, 1 for recent period
            current_date: Reference date for period calculation (ISO date string)
            days_back: Number of days to look back for recent mode

        Returns:
            SQL query string with weighted relevance scoring
        """
        # assert filter_recent in (0, 1), "filter_recent must be 0 or 1"
        # assert 1 <= days_back <= 999, "days_back out of range"

        # Weighted expressions using configurable constants
        weighted_all_time = f"""
            COALESCE(ra.cnt, 0) * {POPULARITY_WEIGHT_RATE} +
            COALESCE(re.cnt, 0) * {POPULARITY_WEIGHT_RECS} +
            COALESCE(rv.cnt, 0) * {POPULARITY_WEIGHT_REVIEWS}
        """

        weighted_recent = f"""
            COALESCE(re.cnt, 0) * {POPULARITY_WEIGHT_RECS} +
            COALESCE(rv.cnt, 0) * {POPULARITY_WEIGHT_REVIEWS}
        """

        return f"""
    SELECT 
        -- b.BookID,
        -- b.Lang,
        -- b.Title,
        -- b.FileSize,
        -- b.Year,
        {BASE_FIELDS},
        CASE {filter_recent}
            WHEN 0 THEN {weighted_all_time}
            WHEN 1 THEN {weighted_recent}
        END AS relevance,
        CASE {1 - filter_recent}
            WHEN 0 THEN {weighted_all_time}
            WHEN 1 THEN {weighted_recent}
        END AS relevance_oppos,
        ROW_NUMBER() OVER (PARTITION BY b.BookId ORDER BY b.BookId) AS rn
    FROM cb_libbook b
    {get_base_joins(locale)}
    LEFT JOIN (
        SELECT bookid, COUNT(DISTINCT id) AS cnt
        FROM cb_librate
        GROUP BY bookid
    ) ra ON ra.BookId = b.BookId
    LEFT JOIN (
        SELECT bid AS bookid, COUNT(DISTINCT id) AS cnt
        FROM cb_librecs
        WHERE '{current_date}' - INTERVAL {days_back} DAY <= timestamp
           OR {filter_recent} = 0
        GROUP BY bid
    ) re ON re.BookId = b.BookId
    LEFT JOIN (
        SELECT bookid, COUNT(DISTINCT time) AS cnt
        FROM cb_libreviews
        WHERE '{current_date}' - INTERVAL {days_back} DAY <= time
           OR {filter_recent} = 0
        GROUP BY bookid
    ) rv ON rv.BookId = b.BookId
    -- WHERE b.Deleted = '0'
    WHERE {sql_where}
      AND (CASE {filter_recent}
            WHEN 0 THEN {weighted_all_time}
            WHEN 1 THEN {weighted_recent}
          END) > 0
    ORDER BY 
        CASE {filter_recent}
            WHEN 0 THEN {weighted_all_time}
            WHEN 1 THEN {weighted_recent}
        END DESC,
        CASE {1 - filter_recent}
            WHEN 0 THEN {weighted_all_time}
            WHEN 1 THEN {weighted_recent}
        END DESC
    LIMIT {MAX_BOOKS_SEARCH * 3} 
        """


    @staticmethod
    def build_sql_query_nov(sql_where, locale: str = 'ru'):
        """Поиск новинок"""

        return f"""
    SELECT 
        -- b.BookID,
        -- b.Lang,
        -- b.Title,
        -- b.FileSize,
        -- b.Year,
        {BASE_FIELDS},
        b.BookID AS relevance,
        0 AS relevance_oppos,
        ROW_NUMBER() OVER (PARTITION BY b.BookId ORDER BY b.BookId) AS rn
    FROM cb_libbook b
    {get_base_joins(locale)}
    WHERE {sql_where}
    ORDER BY b.BookID desc 
    LIMIT {MAX_BOOKS_SEARCH * 3} 
        """


    @staticmethod
    def build_sql_where_ft(lang, size_limit, rating_filter=None, series_id=0, author_id=0, person_type='author',
                           genre_filter=None):
        """Создает SQL-условие WHERE на основе списка слов и их операторов."""
        conditions = []

        # Добавляем условие по языку, если задан в настройках пользователя
        if lang:
            conditions.append(f"SearchLang = '{lang.upper()}'")

        # Добавляем ограничение по размеру книг, если задан в настройках пользователя
        if size_limit:
            conditions.append(f"BookSizeCat = '{size_limit}'")

        # ДОБАВЛЯЕМ ФИЛЬТРАЦИЮ ПО РЕЙТИНГУ
        if rating_filter and rating_filter != '':
            rating_condition = f"LibRate IN ({rating_filter})"
            conditions.append(rating_condition)

        # Добавляем условие по серии в поиске книг по сериям
        if series_id != 0:
            conditions.append(f"SeriesID = {series_id}")

        # Добавляем условие по автору в поиске книг по авторам
        if author_id != 0:
            conditions.append(f"AuthorID = {author_id}" if person_type=='author' else f"TransID = {author_id}")

        # Note: Genre filter is NOT added here because this WHERE clause is used outside the subquery
        # where table aliases are not available. Genre filter is handled separately in build_sql_query_books.

        # в соновном sql вконце уже есть where, поэтому заменяем его на and
        sql_where = "WHERE " + " AND ".join(conditions) if conditions else "WHERE 1=1"
        return sql_where #, params


    @staticmethod
    def build_sql_query_books(sql_where, sort_order='desc', search_area=SETTING_SEARCH_AREA_B, locale: str = 'ru', is_empty=False, genre_filter=None):
        fields = Book._fields

        # Всегда используем sum для Relevance
        processed_fields = []
        for field in fields:
            # processed_fields.append(f"max({field})")
            processed_fields.append(f"{field}")

        select_fields = ', '.join(processed_fields)

        sql_query_nested = SELECT_SQL_QUERY.get(search_area)(locale, is_empty, genre_filter)
        from_clause = f"FROM ( {sql_query_nested} {sql_where} ) as subquery"

        sql_query = f"""
            select {select_fields} from (
            SELECT {select_fields},
              ROW_NUMBER() OVER (PARTITION BY FileName ORDER BY FileName) AS rn 
            {from_clause}
            -- GROUP BY {fields[0]}
            ORDER BY Relevance DESC, FileName {sort_order}
            -- LIMIT {MAX_BOOKS_SEARCH}
            LIMIT 10000
            ) as ranked
            where rn = 1
            ORDER BY Relevance DESC, FileName {sort_order}
            LIMIT {MAX_BOOKS_SEARCH}
        """

        return sql_query

    def invalidate_db_cache(self):
        """
        Hourly check to detect database updates and invalidate cache if needed.
        Called from cleanup_old_sessions task.
        """
        # from logger import logger
        try:
            # Get current max book ID from DB
            current_max = self.get_max_book_id()
            if current_max is None:
                return  # Cannot determine, skip

            # Get cached max from _class_stats
            cached_max = DatabaseBooks._class_stats.get('max_filename') if DatabaseBooks._class_stats else None

            if current_max != cached_max:
                # Database updated - clear all class-level caches
                DatabaseBooks._class_cached_langs = None
                DatabaseBooks._class_cached_parent_genres = None
                DatabaseBooks._class_cached_genres = {}
                DatabaseBooks._class_stats = {}

                # logger.log_system_action("Cache invalidated due to database update",
                #                          f"old_max={cached_max}, new_max={current_max}, difference={current_max - cached_max if isinstance(cached_max, int) else None}")
        except Exception as e:
            # logger.log_system_action("Cache invalidation check failed", str(e))
            pass
    
    
DB_BOOKS = DatabaseBooks({
    'host': os.getenv('DB_HOST'),
    'port': int(os.getenv('DB_PORT', 3306)),
    'database': os.getenv('DB_NAME'),
    'user': os.getenv('DB_USER'),
    'password': os.getenv('DB_PASSWORD'),
    'charset': os.getenv('DB_CHARSET', 'utf8mb4')
})

DB_LOGS = DatabaseLogs()