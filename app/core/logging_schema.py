"""
Схема структурированного логирования
"""

from dataclasses import dataclass, asdict
from datetime import datetime
from typing import Optional, Dict, Any
from enum import Enum
import json

class EventCategory(Enum):
    """Категории событий"""
    USER_ACTION = "user_action"
    SYSTEM = "system"
    ERROR = "error"
    PAYMENT = "payment"

class EventType(Enum):
    """Типы событий"""
    # Пользовательские действия
    BOT_START = "bot.start"
    SEARCH_BOOKS = "search.books"
    SEARCH_SERIES = "search.series"
    SEARCH_AUTHORS = "search.authors"
    SEARCH_POPULAR = "search.popular"
    BOOK_INFO_VIEW = "book.info.view"
    BOOK_DOWNLOAD = "book.download"
    AUTHOR_INFO_VIEW = "author.info.view"
    SETTINGS_CHANGE = "settings.change"
    GENRES_VIEW = "genres.view"
    BOOK_DETAILS_VIEW = "book.details.view"
    BOOK_REVIEWS_VIEW = "book.reviews.view"
    # Новые типы для главных команд
    HELP_VIEW = "help.view"
    ABOUT_VIEW = "about.view"
    NEWS_VIEW = "news.view"
    DONATE_VIEW = "donate.view"

    # Системные события
    SYSTEM_STARTUP = "system.startup"
    SYSTEM_SHUTDOWN = "system.shutdown"
    DATABASE_ERROR = "system.db.error"
    API_ERROR = "system.api.error"

    # Ошибки
    ERROR_BOOK_DOWNLOAD = "error.book.download"
    ERROR_SEARCH = "error.search"
    ERROR_TELEGRAM = "error.telegram"

    # Платежи
    PAYMENT_RECEIVED = "payment.received"
    PAYMENT_REFUND = "payment.refund"


@dataclass
class LogEvent:
    """Структурированное событие лога"""

    # Временная метка
    timestamp: datetime

    # Категория и тип события
    category: EventCategory
    event_type: EventType

    # Пользователь (None для системных событий)
    user_id: Optional[int]
    username: Optional[str]

    # Контекст
    chat_type: str  # 'private' или 'group'
    chat_id: Optional[int]

    # Данные события (JSON)
    data: Dict[str, Any]

    # Метрики
    duration_ms: Optional[int] = None

    # Ошибки
    error_message: Optional[str] = None
    error_type: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Преобразование в словарь"""
        result = asdict(self)
        result['timestamp'] = self.timestamp.isoformat()
        result['category'] = self.category.value
        result['event_type'] = self.event_type.value
        return result

    def to_json(self) -> str:
        """Преобразование в JSON"""
        return json.dumps(self.to_dict(), ensure_ascii=False)


# ===== СПЕЦИАЛИЗИРОВАННЫЕ СОБЫТИЯ =====

@dataclass
class SearchEvent:
    """Данные события поиска"""
    query: str
    search_type: str  # 'books', 'series', 'authors'
    search_area: str  # 'b', 'ba', 'aa'
    results_count: int
    filters: Dict[str, Any]  # lang, rating, size, etc.


@dataclass
class DownloadEvent:
    """Данные события скачивания"""
    book_id: int
    book_title: str
    format: str
    file_size: int
    success: bool
    via_tmpfiles: bool = False


@dataclass
class SettingsChangeEvent:
    """Данные изменения настроек"""
    setting_name: str
    old_value: Any
    new_value: Any


@dataclass
class ErrorEvent:
    """Данные события ошибки"""
    error_type: str
    error_message: str
    context: Dict[str, Any]
    traceback: Optional[str] = None

