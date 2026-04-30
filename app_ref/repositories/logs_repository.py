"""
Репозиторий для работы с логами (SQLite)
"""

from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta
from .base_sqlite import BaseSQLiteRepository
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
            -- id INTEGER PRIMARY KEY AUTOINCREMENT, -- НЕ НУЖЕН
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

    # ==================== АНАЛИТИКА И ОТЧЕТЫ ====================

    def get_user_stats_summary(self) -> Dict[str, Any]:
        """
        Получение общей статистики пользователей

        Returns:
            Словарь со статистикой
        """
        query = """
        SELECT
            COUNT(DISTINCT user_id) as total_users,
            COUNT(*) as total_events,
            COUNT(DISTINCT CASE WHEN category = 'user_action' THEN user_id END) as active_users,
            COUNT(DISTINCT CASE WHEN category = 'error' THEN user_id END) as users_with_errors
        FROM StructuredLog
        """
        
        result = self.execute_query(query, fetch_one=True)
        if not result:
            return {}
        
        return {
            'total_users': result['total_users'],
            'total_events': result['total_events'],
            'active_users': result['active_users'],
            'users_with_errors': result['users_with_errors']
        }

    def get_daily_user_stats(self, days: int = 30) -> List[Dict[str, Any]]:
        """
        Статистика пользователей по дням

        Args:
            days: Количество дней назад

        Returns:
            Список словарей с дневной статистикой
        """
        query = """
        SELECT
            DATE(timestamp) as date,
            COUNT(DISTINCT user_id) as unique_users,
            COUNT(*) as total_events,
            COUNT(DISTINCT CASE WHEN category = 'error' THEN user_id END) as users_with_errors
        FROM StructuredLog
        WHERE timestamp >= date('now', ?)
        GROUP BY DATE(timestamp)
        ORDER BY date DESC
        """
        
        results = self.execute_query(query, (f'-{days} days',))
        return [
            {
                'date': row['date'],
                'unique_users': row['unique_users'],
                'total_events': row['total_events'],
                'users_with_errors': row['users_with_errors']
            }
            for row in results
        ]

    def get_top_searches(self, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Топ поисковых запросов

        Args:
            limit: Количество записей

        Returns:
            Список словарей с запросами
        """
        query = """
        SELECT
            json_extract(data_json, '$.query') as query,
            COUNT(*) as search_count,
            COUNT(DISTINCT user_id) as unique_users,
            AVG(json_extract(data_json, '$.results_count')) as avg_results
        FROM StructuredLog
        WHERE event_type IN ('search.books', 'search.series', 'search.authors')
          AND json_extract(data_json, '$.query') IS NOT NULL
        GROUP BY json_extract(data_json, '$.query')
        ORDER BY search_count DESC
        LIMIT ?
        """
        
        results = self.execute_query(query, (limit,))
        return [
            {
                'query': row['query'],
                'search_count': row['search_count'],
                'unique_users': row['unique_users'],
                'avg_results': round(row['avg_results'], 2) if row['avg_results'] else 0
            }
            for row in results
        ]

    def get_top_downloads(self, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Топ скачиваний

        Args:
            limit: Количество записей

        Returns:
            Список словарей с книгами
        """
        query = """
        SELECT
            json_extract(data_json, '$.book_title') as book_title,
            json_extract(data_json, '$.book_id') as book_id,
            COUNT(*) as download_count,
            COUNT(DISTINCT user_id) as unique_users,
            AVG(CASE WHEN json_extract(data_json, '$.success') = 1 THEN 1 ELSE 0 END) as success_rate
        FROM StructuredLog
        WHERE event_type = 'book.download'
          AND json_extract(data_json, '$.book_title') IS NOT NULL
        GROUP BY json_extract(data_json, '$.book_id'), json_extract(data_json, '$.book_title')
        ORDER BY download_count DESC
        LIMIT ?
        """
        
        results = self.execute_query(query, (limit,))
        return [
            {
                'book_title': row['book_title'],
                'book_id': row['book_id'],
                'download_count': row['download_count'],
                'unique_users': row['unique_users'],
                'success_rate': round(row['success_rate'] * 100, 1)
            }
            for row in results
        ]

    def get_payment_stats(self, days: int = 30) -> Dict[str, Any]:
        """
        Статистика платежей

        Args:
            days: Количество дней назад

        Returns:
            Словарь со статистикой платежей
        """
        query = """
        SELECT
            COUNT(*) as total_payments,
            COUNT(DISTINCT user_id) as unique_payers,
            SUM(CAST(json_extract(data_json, '$.amount') AS REAL)) as total_amount,
            AVG(CAST(json_extract(data_json, '$.amount') AS REAL)) as avg_amount
        FROM StructuredLog
        WHERE event_type = 'payment.received'
          AND timestamp >= date('now', ?)
        """
        
        result = self.execute_query(query, (f'-{days} days',), fetch_one=True)
        if not result:
            return {}
        
        return {
            'total_payments': result['total_payments'],
            'unique_payers': result['unique_payers'],
            'total_amount': round(result['total_amount'] or 0, 2),
            'avg_amount': round(result['avg_amount'] or 0, 2)
        }

    def get_recent_errors(self, limit: int = 20) -> List[Dict[str, Any]]:
        """
        Последние ошибки

        Args:
            limit: Количество записей

        Returns:
            Список словарей с ошибками
        """
        query = """
        SELECT
            timestamp,
            user_id,
            username,
            event_type,
            error_message,
            error_type,
            data_json
        FROM StructuredLog
        WHERE category = 'error'
        ORDER BY timestamp DESC
        LIMIT ?
        """
        
        results = self.execute_query(query, (limit,))
        return [
            {
                'timestamp': row['timestamp'],
                'user_id': row['user_id'],
                'username': row['username'],
                'event_type': row['event_type'],
                'error_message': row['error_message'],
                'error_type': row['error_type'],
                'data': json.loads(row['data_json']) if row['data_json'] else {}
            }
            for row in results
        ]

    def get_user_activity(
        self,
        user_id: int,
        days: int = 7
    ) -> List[Dict[str, Any]]:
        """
        Активность конкретного пользователя

        Args:
            user_id: ID пользователя
            days: Количество дней назад

        Returns:
            Список событий пользователя
        """
        query = """
        SELECT
            timestamp,
            category,
            event_type,
            data_json,
            duration_ms,
            error_message
        FROM StructuredLog
        WHERE user_id = ?
          AND timestamp >= date('now', ?)
        ORDER BY timestamp DESC
        """
        
        results = self.execute_query(query, (user_id, f'-{days} days'))
        return [
            {
                'timestamp': row['timestamp'],
                'category': row['category'],
                'event_type': row['event_type'],
                'data': json.loads(row['data_json']) if row['data_json'] else {},
                'duration_ms': row['duration_ms'],
                'error_message': row['error_message']
            }
            for row in results
        ]

    def cleanup_old_logs(self, days: int = 60) -> int:
        """
        Удаление старых логов

        Args:
            days: Хранить логи за N дней

        Returns:
            Количество удаленных записей
        """
        query = """
        DELETE FROM StructuredLog
        WHERE timestamp < date('now', ?)
        """
        
        return self.execute_update(query, (f'-{days} days',))

