"""
Репозиторий для работы с логами (SQLite)
"""

from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta
from ..repositories.base_sqlite import BaseSQLiteRepository
from ..core.logging_schema import LogEvent
import json


class LogsRepository(BaseSQLiteRepository):
    """
    Репозиторий для структурированных логов

    БД: FlibustaLogs.sqlite
    Таблицы: StructuredLog
    """

    def __init__(self, db_path: str = "data/FlibustaLogs.sqlite"):
        """Инициализация репозитория логов"""
        super().__init__(db_path)

    def _init_schema(self) -> None:
        """Инициализация схемы БД при первом запуске"""
        schema_sql = """
        CREATE TABLE IF NOT EXISTS StructuredLog (
            timestamp TEXT NOT NULL,
            category TEXT NOT NULL,
            event_type TEXT NOT NULL,

            user_id INTEGER,
            username TEXT,

            chat_type TEXT NOT NULL,
            chat_id INTEGER,

            data_json TEXT,

            duration_ms INTEGER,

            error_message TEXT,
            error_type TEXT
        );

        CREATE INDEX IF NOT EXISTS idx_timestamp ON StructuredLog(timestamp);
        CREATE INDEX IF NOT EXISTS idx_category ON StructuredLog(category);
        CREATE INDEX IF NOT EXISTS idx_event_type ON StructuredLog(event_type);
        CREATE INDEX IF NOT EXISTS idx_user_id ON StructuredLog(user_id);
        CREATE INDEX IF NOT EXISTS idx_category_timestamp ON StructuredLog(category, timestamp);

        -- PaymentLog table for payment events
        CREATE TABLE IF NOT EXISTS PaymentLog (
            payment_id TEXT PRIMARY KEY,
            user_id INTEGER NOT NULL,
            username TEXT,
            amount INTEGER NOT NULL,
            currency TEXT NOT NULL,
            payment_method TEXT,
            payment_date TEXT NOT NULL,
            payment_status TEXT NOT NULL DEFAULT 'completed',
            telegram_payment_charge_id TEXT,
            data_json TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        );

        CREATE INDEX IF NOT EXISTS idx_paymentlog_user_id ON PaymentLog(user_id);
        CREATE INDEX IF NOT EXISTS idx_paymentlog_payment_date ON PaymentLog(payment_date);
        CREATE INDEX IF NOT EXISTS idx_paymentlog_status ON PaymentLog(payment_status);
        """

        with self.get_connection() as conn:
            conn.executescript(schema_sql)

    # ==================== ЗАПИСЬ ЛОГОВ ====================

    def write_structured_log(self, event: LogEvent) -> int:
        """
        Записывает структурированное событие

        Args:
            event: LogEvent объект

        Returns:
            ID созданной записи
        """
        query = """
        INSERT INTO StructuredLog (
            timestamp, category, event_type,
            user_id, username,
            chat_type, chat_id,
            data_json,
            duration_ms,
            error_message, error_type
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """

        params = (
            event.timestamp.isoformat(),
            event.category.value,
            event.event_type.value,
            event.user_id,
            event.username,
            event.chat_type,
            event.chat_id,
            json.dumps(event.data, ensure_ascii=False),
            event.duration_ms,
            event.error_message,
            event.error_type
        )

        self.execute_update(query, params)
        return self.get_last_insert_id()

    # ==================== ЗАПИСЬ ПЛАТЕЖЕЙ ====================

    def write_payment(self, event: LogEvent) -> int:
        """
        Записывает событие платежа в PaymentLog

        Args:
            event: LogEvent объект с category=PAYMENT

        Returns:
            ID созданнной записи
        """
        query = """
        INSERT OR REPLACE INTO PaymentLog (
            payment_id, user_id, username, amount, currency,
            payment_method, payment_date, payment_status,
            telegram_payment_charge_id, data_json
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """

        data = event.data
        params = (
            data.get('payment_id'),
            event.user_id,
            event.username,
            data.get('amount'),
            data.get('currency'),
            data.get('payment_method'),
            event.timestamp.isoformat(),
            'completed',
            data.get('telegram_payment_charge_id'),
            json.dumps(data, ensure_ascii=False)
        )

        self.execute_update(query, params)
        return self.get_last_insert_id()

    # ==================== ЧТЕНИЕ: СТАТИСТИКА ====================

    def get_user_stats_summary(self) -> Dict[str, int]:
        """Возвращает общую статистику пользователей"""
        stats_week = self._get_period_stats(7)
        stats_month = self._get_period_stats(30)
        stats_total = self._get_total_stats()

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

    def _get_period_stats(self, days: int) -> Dict[str, int]:
        """Возвращает статистику за указанный период в днях"""
        with self.get_connection() as conn:
            cursor = conn.cursor()

            # Новые пользователи за период
            cursor.execute("""
                SELECT COUNT(*) AS NewUsers
                FROM (
                    SELECT user_id, MIN(timestamp) AS FirstSeen
                    FROM StructuredLog
                    WHERE user_id IS NOT NULL
                    GROUP BY user_id
                    HAVING date(FirstSeen) >= date('now', ?)
                )
            """, (f'-{days} days',))
            new_users = cursor.fetchone()[0] or 0

            # Активные пользователи за период
            cursor.execute("""
                SELECT COUNT(DISTINCT user_id) AS ActiveUsers
                FROM StructuredLog
                WHERE date(timestamp) >= date('now', ?)
            """, (f'-{days} days',))
            active_users = cursor.fetchone()[0] or 0

            # Количество поисков и скачиваний за период
            cursor.execute("""
                SELECT 
                    SUM(CASE WHEN event_type LIKE 'search.%' THEN 1 ELSE 0 END) AS TotalSearches,
                    SUM(CASE WHEN event_type = 'book.download' THEN 1 ELSE 0 END) AS TotalDownloads
                FROM StructuredLog
                WHERE date(timestamp) >= date('now', ?)
            """, (f'-{days} days',))
            row = cursor.fetchone()
            searches = row[0] or 0
            downloads = row[1] or 0

            return {
                'new_users': new_users,
                'active_users': active_users,
                'searches': searches,
                'downloads': downloads
            }

    def _get_total_stats(self) -> Dict[str, int]:
        """Возвращает общую статистику за всё время"""
        with self.get_connection() as conn:
            cursor = conn.cursor()

            cursor.execute("""
                SELECT 
                    COUNT(DISTINCT user_id) AS TotalUsers,
                    SUM(CASE WHEN event_type LIKE 'search.%' THEN 1 ELSE 0 END) AS TotalSearches,
                    SUM(CASE WHEN event_type = 'book.download' THEN 1 ELSE 0 END) AS TotalDownloads
                FROM StructuredLog
            """)
            row = cursor.fetchone()

            return {
                'total_users': row[0] or 0,
                'active_users_total': row[0] or 0,
                'searches_total': row[1] or 0,
                'downloads_total': row[2] or 0
            }

    def get_daily_user_stats(self, days: int = 7) -> Dict[str, list]:
        """Возвращает статистику пользователей по дням"""
        with self.get_connection() as conn:
            cursor = conn.cursor()

            # Статистика новых пользователей по дням
            cursor.execute("""
                SELECT date(FirstSeen) as day, COUNT(*) as new_users
                FROM (
                    SELECT user_id, MIN(timestamp) AS FirstSeen
                    FROM StructuredLog
                    WHERE user_id IS NOT NULL
                    GROUP BY user_id
                    HAVING date(FirstSeen) >= date('now', ?)
                )
                GROUP BY date(FirstSeen)
                ORDER BY day DESC
            """, (f'-{days} days',))
            new_users_by_day = {row[0]: row[1] for row in cursor.fetchall()}

            # Статистика активных пользователей по дням
            cursor.execute("""
                SELECT date(timestamp) as day, COUNT(DISTINCT user_id) as active_users
                FROM StructuredLog
                WHERE date(timestamp) >= date('now', ?)
                GROUP BY date(timestamp)
                ORDER BY day DESC
            """, (f'-{days} days',))
            active_users_by_day = {row[0]: row[1] for row in cursor.fetchall()}

            # Статистика поисков и скачиваний по дням
            cursor.execute("""
                SELECT 
                    date(timestamp) as day,
                    SUM(CASE WHEN event_type LIKE 'search.%' THEN 1 ELSE 0 END) as searches,
                    SUM(CASE WHEN event_type = 'book.download' THEN 1 ELSE 0 END) as downloads
                FROM StructuredLog
                WHERE date(timestamp) >= date('now', ?)
                GROUP BY date(timestamp)
                ORDER BY day DESC
            """, (f'-{days} days',))
            searches_by_day = {}
            downloads_by_day = {}
            for row in cursor.fetchall():
                searches_by_day[row[0]] = row[1] or 0
                downloads_by_day[row[0]] = row[2] or 0

            # Формируем полный список дней
            dates = []
            for i in range(days):
                date = (datetime.now() - timedelta(days=i)).strftime('%Y-%m-%d')
                dates.append(date)

            return {
                'dates': dates,
                'new_users': [new_users_by_day.get(date, 0) for date in dates],
                'active_users': [active_users_by_day.get(date, 0) for date in dates],
                'searches': [searches_by_day.get(date, 0) for date in dates],
                'downloads': [downloads_by_day.get(date, 0) for date in dates]
            }

    def get_payment_stats(self, days: int = 30) -> Dict[str, Any]:
        """Получает статистику по платежам из PaymentLog"""
        with self.get_connection() as conn:
            cursor = conn.cursor()

            cursor.execute("""
                SELECT 
                    COUNT(*) as total_payments,
                    SUM(amount) as total_amount,
                    AVG(amount) as avg_amount,
                    COUNT(DISTINCT user_id) as unique_donors
                FROM PaymentLog 
                WHERE payment_status = 'completed'
                AND payment_date >= date('now', ?)
            """, (f'-{days} days',))

            stats = cursor.fetchone()

            return {
                'total_payments': stats[0] or 0,
                'total_amount': float(stats[1] or 0),
                'avg_amount': float(stats[2] or 0),
                'unique_donors': stats[3] or 0
            }

    # ==================== ЧТЕНИЕ: ПОСЛЕДНИЕ ДЕЙСТВИЯ ====================

    def get_payments_list(self, limit: int = 20, offset: int = 0) -> list:
        """Возвращает список платежей с пагинацией"""
        with self.get_connection() as conn:
            cursor = conn.cursor()

            cursor.execute("""
                SELECT
                    payment_id,
                    user_id,
                    username,
                    amount,
                    currency,
                    payment_method,
                    payment_date,
                    payment_status,
                    telegram_payment_charge_id
                FROM PaymentLog
                ORDER BY payment_date DESC
                LIMIT ? OFFSET ?
            """, (limit, offset))

            payments = []
            for row in cursor.fetchall():
                payments.append({
                    'payment_id': row[0],
                    'user_id': row[1],
                    'username': row[2],
                    'amount': row[3],
                    'currency': row[4],
                    'payment_method': row[5],
                    'payment_date': row[6],
                    'payment_status': row[7],
                    'telegram_payment_charge_id': row[8]
                })

            return payments

    def get_payments_count(self) -> int:
        """Возвращает общее количество платежей"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM PaymentLog")
            return cursor.fetchone()[0] or 0

    def get_recent_searches(self, limit: int = 20) -> list:
        """Возвращает последние поисковые запросы"""
        with self.get_connection() as conn:
            cursor = conn.cursor()

            cursor.execute("""
                SELECT 
                    json_extract(data_json, '$.query') AS SearchQuery,
                    datetime(timestamp),
                    username
                FROM StructuredLog
                WHERE event_type LIKE 'search.%'
                ORDER BY timestamp DESC
                LIMIT ?
            """, (limit,))

            return cursor.fetchall()

    def get_recent_downloads(self, limit: int = 20) -> list:
        """Возвращает последние скачивания"""
        with self.get_connection() as conn:
            cursor = conn.cursor()

            cursor.execute("""
                SELECT 
                    json_extract(data_json, '$.book_title') AS BookTitle,
                    datetime(timestamp),
                    username
                FROM StructuredLog
                WHERE event_type = 'book.download'
                ORDER BY timestamp DESC
                LIMIT ?
            """, (limit,))

            return cursor.fetchall()

    # ==================== ЧТЕНИЕ: ТОПЫ ====================

    def get_top_searches(self, limit: int = 20) -> List[Dict[str, Any]]:
        """Возвращает топ поисковых запросов"""
        with self.get_connection() as conn:
            cursor = conn.cursor()

            cursor.execute("""
                SELECT 
                    json_extract(data_json, '$.query') AS SearchQuery, 
                    COUNT(*) AS SearchCount,
                    COUNT(DISTINCT user_id) AS UniqueUsers
                FROM StructuredLog
                WHERE event_type LIKE 'search.%'
                GROUP BY json_extract(data_json, '$.query')
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

    def get_top_downloads(self, limit: int = 20) -> list:
        """Возвращает топ скачанных книг"""
        with self.get_connection() as conn:
            cursor = conn.cursor()

            cursor.execute("""
                SELECT 
                    json_extract(data_json, '$.book_title') AS BookTitle,
                    COUNT(*) AS DownloadCount
                FROM StructuredLog
                WHERE event_type = 'book.download'
                GROUP BY json_extract(data_json, '$.book_title')
                ORDER BY DownloadCount DESC
                LIMIT ?
            """, (limit,))

            return cursor.fetchall()

    # ==================== ЧТЕНИЕ: СПИСОК ПОЛЬЗОВАТЕЛЕЙ ====================

    def get_users_list(self, limit: int = 50, offset: int = 0) -> List[Dict[str, Any]]:
        """Возвращает список пользователей с основной информацией"""
        with self.get_connection() as conn:
            cursor = conn.cursor()

            cursor.execute("""
                SELECT
                    user_id,
                    MIN(username) AS UserName,
                    MAX(datetime(timestamp)) AS LastSeen,
                    MIN(datetime(timestamp)) AS FirstSeen,
                    SUM(CASE WHEN event_type LIKE 'search.%' THEN 1 ELSE 0 END) AS TotalSearches,
                    SUM(CASE WHEN event_type = 'book.download' THEN 1 ELSE 0 END) AS TotalDownloads
                FROM StructuredLog
                WHERE user_id IS NOT NULL
                GROUP BY user_id
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

    def get_user_by_id(self, user_id: int) -> Optional[Dict[str, Any]]:
        """Возвращает информацию о конкретном пользователе по ID"""
        with self.get_connection() as conn:
            cursor = conn.cursor()

            cursor.execute("""
                SELECT
                    user_id,
                    MIN(username) AS UserName,
                    MAX(datetime(timestamp)) AS LastSeen,
                    MIN(datetime(timestamp)) AS FirstSeen,
                    SUM(CASE WHEN event_type LIKE 'search.%' THEN 1 ELSE 0 END) AS TotalSearches,
                    SUM(CASE WHEN event_type = 'book.download' THEN 1 ELSE 0 END) AS TotalDownloads
                FROM StructuredLog
                WHERE user_id = ?
                GROUP BY user_id
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

    def get_user_activity(self, user_id: int, limit: int = 50) -> List[Dict[str, str]]:
        """Возвращает историю действий пользователя"""
        with self.get_connection() as conn:
            cursor = conn.cursor()

            cursor.execute("""
                SELECT datetime(timestamp), event_type, data_json
                FROM StructuredLog
                WHERE user_id = ?
                ORDER BY timestamp DESC
                LIMIT ?
            """, (user_id, limit))

            activities = []
            for row in cursor.fetchall():
                activities.append({
                    'timestamp': row[0],
                    'event_type': row[1],
                    'data_json': row[2] or ''
                })

            return activities

