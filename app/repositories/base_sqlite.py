"""
Базовый класс для работы с SQLite
Чтение и запись данных
"""

from typing import Any, Optional
from contextlib import contextmanager
import sqlite3
import os
import threading


class BaseSQLiteRepository:
    """
    Базовый класс для работы с SQLite

    Особенности:
    - Чтение и запись данных
    - Thread-safe операции
    - Автоматическое создание БД если не существует
    """

    # Thread-local storage для подключений
    _local = threading.local()

    def __init__(self, db_path: str):
        """
        Инициализация репозитория

        Args:
            db_path: Путь к файлу SQLite БД
        """
        self.db_path = db_path

        # Создаём директорию если не существует
        db_dir = os.path.dirname(db_path)
        if db_dir and not os.path.exists(db_dir):
            os.makedirs(db_dir, exist_ok=True)

        # Инициализируем схему при первом запуске
        self._init_schema()

    def _init_schema(self) -> None:
        """
        Инициализация схемы БД
        Переопределяется в наследниках
        """
        pass

    @contextmanager
    def get_connection(self):
        """
        Контекстный менеджер для получения подключения к SQLite

        Features:
        - Row factory для доступа по именам колонок
        - Автоматический commit при успехе
        - Rollback при ошибке

        Yields:
            sqlite3.Connection
        """
        conn = None
        try:
            conn = sqlite3.connect(self.db_path, check_same_thread=False)
            conn.row_factory = sqlite3.Row  # Доступ к колонкам по имени
            yield conn
            conn.commit()
        except Exception as e:
            if conn:
                conn.rollback()
            print(f"SQLite error: {e}")
            raise
        finally:
            if conn:
                conn.close()

    def execute_query(
            self,
            query: str,
            params: Optional[tuple[Any, ...] | dict[str, Any]] = None,
            fetch_one: bool = False
    ) -> list[sqlite3.Row] | sqlite3.Row | None:
        """
        Выполняет SELECT запрос

        Args:
            query: SQL запрос
            params: Параметры для запроса (tuple или dict)
            fetch_one: Если True, возвращает только одну строку

        Returns:
            Список Row объектов или один Row (если fetch_one=True)
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()

            if params:
                cursor.execute(query, params)
            else:
                cursor.execute(query)

            if fetch_one:
                result = cursor.fetchone()
            else:
                result = cursor.fetchall()

            cursor.close()
            return result

    def execute_update(
            self,
            query: str,
            params: Optional[tuple[Any, ...] | dict[str, Any]] = None
    ) -> int:
        """
        Выполняет INSERT/UPDATE/DELETE запрос

        Args:
            query: SQL запрос
            params: Параметры для запроса

        Returns:
            Количество затронутых строк
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()

            if params:
                cursor.execute(query, params)
            else:
                cursor.execute(query)

            affected = cursor.rowcount
            cursor.close()
            return affected

    def execute_many(
            self,
            query: str,
            params_list: list[tuple[Any, ...] | dict[str, Any]]
    ) -> int:
        """
        Выполняет множественные INSERT/UPDATE

        Args:
            query: SQL запрос
            params_list: Список параметров

        Returns:
            Количество затронутых строк
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.executemany(query, params_list)
            affected = cursor.rowcount
            cursor.close()
            return affected

    def get_last_insert_id(self) -> int:
        """
        Возвращает ID последней вставленной записи

        Returns:
            ID последней записи
        """
        result = self.execute_query("SELECT last_insert_rowid()", fetch_one=True)
        return result[0] if result else 0
