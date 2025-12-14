"""
Базовый класс для работы с MariaDB (Flibusta)
Только чтение данных
"""

from typing import Any, Optional
from contextlib import contextmanager
import mysql.connector
from mysql.connector import Error
import os


class BaseMariaDBRepository:
    """
    Базовый класс для работы с MariaDB (библиотека Flibusta)

    Особенности:
    - Только SELECT запросы (read-only)
    - Кеширование на уровне класса
    - Оптимизирован для больших объёмов данных
    """

    _connection_pool: Optional[Any] = None

    def __init__(self, db_config: Optional[dict[str, Any]] = None):
        """
        Инициализация репозитория

        Args:
            db_config: Конфигурация подключения к MariaDB
                      Если None, используются переменные окружения
        """
        if db_config is None:
            self.db_config = {
                'host': os.getenv('DB_HOST', 'localhost'),
                'port': int(os.getenv('DB_PORT', '3306')),
                'database': os.getenv('DB_NAME', 'flibusta'),
                'user': os.getenv('DB_USER', 'flibusta'),
                'password': os.getenv('DB_PASSWORD', ''),
                'charset': 'utf8mb3',
                'collation': 'utf8mb3_unicode_ci',
            }
        else:
            self.db_config = db_config

    @contextmanager
    def get_connection(self):
        """
        Контекстный менеджер для получения подключения к MariaDB

        Yields:
            mysql.connector.connection.MySQLConnection
        """
        conn = None
        try:
            conn = mysql.connector.connect(**self.db_config)
            yield conn
        except Error as e:
            print(f"MariaDB connection error: {e}")
            raise
        finally:
            if conn and conn.is_connected():
                conn.close()

    def execute_query(
            self,
            query: str,
            params: Optional[tuple[Any, ...]] = None,
            fetch_one: bool = False
    ) -> list[tuple[Any, ...]] | tuple[Any, ...] | None:
        """
        Выполняет SELECT запрос

        Args:
            query: SQL запрос
            params: Параметры для запроса
            fetch_one: Если True, возвращает только одну строку

        Returns:
            Список кортежей или один кортеж (если fetch_one=True)
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()
            try:
                if params:
                    cursor.execute(query, params)
                else:
                    cursor.execute(query)

                if fetch_one:
                    result = cursor.fetchone()
                else:
                    result = cursor.fetchall()

                return result
            finally:
                cursor.close()

    def execute_query_dict(
            self,
            query: str,
            params: Optional[tuple[Any, ...]] = None
    ) -> list[dict[str, Any]]:
        """
        Выполняет SELECT запрос и возвращает результаты как список словарей

        Args:
            query: SQL запрос
            params: Параметры для запроса

        Returns:
            Список словарей с результатами
        """
        with self.get_connection() as conn:
            cursor = conn.cursor(dictionary=True)
            try:
                if params:
                    cursor.execute(query, params)
                else:
                    cursor.execute(query)

                results = cursor.fetchall()
                return results if results else []
            finally:
                cursor.close()
