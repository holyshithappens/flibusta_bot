"""
User Repository - Репозиторий для работы с настройками пользователей (SQLite)
"""
from typing import Optional, Dict, Any
import sqlite3
from datetime import datetime

from ..core.custom_types import UserSettings


class UserRepository:
    """
    Репозиторий для работы с настройками пользователей в SQLite
    
    Отвечает за:
    - Получение и обновление настроек пользователя
    - Блокировку/разблокировку пользователей
    - Управление датой последних новостей
    """
    
    def __init__(self, db_path: str):
        """
        Инициализация репозитория
        
        Args:
            db_path: Путь к SQLite базе данных
        """
        self.db_path = db_path
        self._init_db()
    
    def _init_db(self) -> None:
        """Инициализация таблицы UserSettings если её нет"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS UserSettings (
                    User_ID INTEGER PRIMARY KEY,
                    MaxBooks INTEGER DEFAULT 20,
                    Lang VARCHAR(2) DEFAULT '',
                    BookFormat VARCHAR(5) DEFAULT 'fb2',
                    SearchType TEXT DEFAULT 'books',
                    Rating TEXT DEFAULT '',
                    BookSize TEXT DEFAULT '',
                    SearchArea TEXT DEFAULT 'b',
                    IsBlocked BOOLEAN DEFAULT FALSE,
                    LastNewsDate VARCHAR(10) DEFAULT '2000-01-01'
                )
            """)
            conn.commit()
    
    def get_settings(self, user_id: int) -> UserSettings:
        """
        Получить настройки пользователя
        
        Args:
            user_id: ID пользователя
        
        Returns:
            UserSettings
        """
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            cursor.execute(
                "SELECT * FROM UserSettings WHERE User_ID = ?",
                (user_id,)
            )
            row = cursor.fetchone()
            
            if not row:
                # Создаем настройки по умолчанию
                self._create_default_settings(user_id)
                return self.get_settings(user_id)
            
            return UserSettings(
                user_id=row['User_ID'],
                max_books=row['MaxBooks'],
                lang=row['Lang'],
                book_format=row['BookFormat'],
                search_type=row['SearchType'],
                rating=row['Rating'],
                book_size=row['BookSize'],
                search_area=row['SearchArea'],
                is_blocked=bool(row['IsBlocked']),
                last_news_date=row['LastNewsDate']
            )
    
    def update_settings(self, user_id: int, **kwargs) -> None:
        """
        Обновить настройки пользователя
        
        Args:
            user_id: ID пользователя
            **kwargs: Параметры для обновления
        """
        allowed_fields = {
            'max_books', 'lang', 'book_format', 'search_type',
            'rating', 'book_size', 'search_area', 'is_blocked', 'last_news_date'
        }
        
        # Фильтруем только допустимые поля
        updates = {k: v for k, v in kwargs.items() if k in allowed_fields}
        
        if not updates:
            return
        
        # Строим SQL запрос
        set_clause = ", ".join([f"{k.replace('_', '')} = ?" for k in updates.keys()])
        values = list(updates.values())
        values.append(user_id)
        
        sql = f"UPDATE UserSettings SET {set_clause} WHERE User_ID = ?"
        
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(sql, values)
            conn.commit()
    
    def update_setting(self, user_id: int, setting: str, value: Any) -> None:
        """
        Обновить одну конкретную настройку
        
        Args:
            user_id: ID пользователя
            setting: Название настройки
            value: Значение
        """
        # Маппинг названий
        field_map = {
            'max_books': 'MaxBooks',
            'lang': 'Lang',
            'book_format': 'BookFormat',
            'search_type': 'SearchType',
            'rating': 'Rating',
            'book_size': 'BookSize',
            'search_area': 'SearchArea',
            'is_blocked': 'IsBlocked',
            'last_news_date': 'LastNewsDate'
        }
        
        db_field = field_map.get(setting)
        if not db_field:
            return
        
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                f"UPDATE UserSettings SET {db_field} = ? WHERE User_ID = ?",
                (value, user_id)
            )
            conn.commit()
    
    def is_blocked(self, user_id: int) -> bool:
        """
        Проверить, заблокирован ли пользователь
        
        Args:
            user_id: ID пользователя
        
        Returns:
            True если заблокирован
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT IsBlocked FROM UserSettings WHERE User_ID = ?",
                (user_id,)
            )
            row = cursor.fetchone()
            return bool(row and row[0])
    
    def block_user(self, user_id: int) -> None:
        """
        Заблокировать пользователя
        
        Args:
            user_id: ID пользователя
        """
        self.update_setting(user_id, 'is_blocked', True)
    
    def unblock_user(self, user_id: int) -> None:
        """
        Разблокировать пользователя
        
        Args:
            user_id: ID пользователя
        """
        self.update_setting(user_id, 'is_blocked', False)
    
    def get_all_users(self) -> list:
        """
        Получить список всех пользователей
        
        Returns:
            Список кортежей (user_id, is_blocked, last_news_date)
        """
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute("SELECT User_ID, IsBlocked, LastNewsDate FROM UserSettings")
            return [(row['User_ID'], bool(row['IsBlocked']), row['LastNewsDate']) for row in cursor.fetchall()]
    
    def get_blocked_users(self) -> list:
        """
        Получить список заблокированных пользователей
        
        Returns:
            Список ID заблокированных пользователей
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT User_ID FROM UserSettings WHERE IsBlocked = 1")
            return [row[0] for row in cursor.fetchall()]
    
    def update_last_news_date(self, user_id: int, date: str) -> None:
        """
        Обновить дату последних новостей
        
        Args:
            user_id: ID пользователя
            date: Дата в формате 'YYYY-MM-DD'
        """
        self.update_setting(user_id, 'last_news_date', date)
    
    def get_last_news_date(self, user_id: int) -> str:
        """
        Получить дату последних новостей
        
        Args:
            user_id: ID пользователя
        
        Returns:
            Дата в формате 'YYYY-MM-DD'
        """
        settings = self.get_settings(user_id)
        return settings.last_news_date
    
    def _create_default_settings(self, user_id: int) -> None:
        """
        Создать настройки по умолчанию для нового пользователя
        
        Args:
            user_id: ID пользователя
        """
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """
                INSERT INTO UserSettings 
                (User_ID, MaxBooks, Lang, BookFormat, SearchType, Rating, BookSize, SearchArea, IsBlocked, LastNewsDate)
                VALUES (?, 20, '', 'fb2', 'books', '', '', 'b', 0, '2000-01-01')
                """,
                (user_id,)
            )
            conn.commit()
    
    def delete_user(self, user_id: int) -> None:
        """
        Удалить пользователя (для тестирования)
        
        Args:
            user_id: ID пользователя
        """
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("DELETE FROM UserSettings WHERE User_ID = ?", (user_id,))
            conn.commit()
    
    def get_user_count(self) -> int:
        """
        Получить количество пользователей
        
        Returns:
            Количество пользователей
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM UserSettings")
            return cursor.fetchone()[0]