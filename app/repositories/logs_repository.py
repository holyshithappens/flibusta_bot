"""
Репозиторий для работы с логами (SQLite)
"""

from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta
from app.repositories.base_sqlite import BaseSQLiteRepository
from logging_schema import LogEvent
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

