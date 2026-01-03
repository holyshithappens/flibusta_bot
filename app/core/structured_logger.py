"""
Структурированный логгер для бота
"""

import logging
from typing import Optional, Dict, Any, TYPE_CHECKING
from datetime import datetime

from .logging_schema import LogEvent, EventCategory, EventType, SearchEvent, DownloadEvent, SettingsChangeEvent

if TYPE_CHECKING:
    from .repositories.logs_repository import LogsRepository

class StructuredLogger:
    """
    Структурированный логгер

    Записывает события в:
    - Файл (JSON формат)
    - База данных (StructuredLog таблица)
    """

    _instance: Optional['StructuredLogger'] = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        if not hasattr(self, '_initialized'):
            self.file_logger = logging.getLogger('structured_logger')
            self.file_logger.setLevel(logging.INFO)

            # Будем инициализировать DB logger при первом использовании
            self._db_logger = None
            self._initialized = True

    def set_db_logger(self, db_logger: 'LogsRepository') -> None:
        """Установить database logger (LogsRepository)"""
        self._db_logger = db_logger

    def log_event(self, event: LogEvent) -> None:
        """Логирует структурированное событие"""
        # 1. Файловое логирование (JSON)
        self.file_logger.info(event.to_json())

        # 2. Базовое логирование в БД
        if self._db_logger:
            try:
                self._db_logger.write_structured_log(event)
            except Exception as e:
                self.file_logger.error(f"Failed to write to DB: {e}")

    # ===== УДОБНЫЕ МЕТОДЫ ДЛЯ ЧАСТЫХ СОБЫТИЙ =====

    def log_search(
            self,
            user_id: int,
            username: str,
            query: str,
            search_type: str,
            search_area: str,
            results_count: int,
            duration_ms: int,
            chat_type: str = "private",
            chat_id: Optional[int] = None,
            **filters
    ) -> None:
        """Логирует поиск"""
        # Определяем event_type по search_type
        event_type_map = {
            'books': EventType.SEARCH_BOOKS,
            'series': EventType.SEARCH_SERIES,
            'authors': EventType.SEARCH_AUTHORS
        }
        event_type = event_type_map.get(search_type, EventType.SEARCH_BOOKS)

        search_data = SearchEvent(
            query=query,
            search_type=search_type,
            search_area=search_area,
            results_count=results_count,
            filters=filters
        )

        # print(f"DEBUG: search_data={search_data}")

        event = LogEvent(
            timestamp=datetime.now(),
            category=EventCategory.USER_ACTION,
            event_type=event_type,
            user_id=user_id,
            username=username,
            chat_type=chat_type,
            chat_id=chat_id or user_id,
            data=search_data.__dict__,
            duration_ms=duration_ms
        )

        self.log_event(event)

    def log_download(
            self,
            user_id: int,
            username: str,
            book_id: int,
            book_title: str,
            format: str,
            file_size: int,
            success: bool,
            via_tmpfiles: bool = False,
            chat_type: str = "private",
            chat_id: Optional[int] = None
    ) -> None:
        """Логирует скачивание книги"""
        # print(f"DEBUG: book_id={book_id}, type={type(book_id)}")
        # print(f"DEBUG: book_title={book_title}, type={type(book_title)}")
        # print(f"DEBUG: book_format={format}, type={type(format)}")
        # print(f"DEBUG: file_size={file_size}, type={type(file_size)}")

        download_data = DownloadEvent(
            book_id=book_id,
            book_title=book_title,
            format=format,
            file_size=file_size,
            success=success,
            via_tmpfiles=via_tmpfiles
        )

        event = LogEvent(
            timestamp=datetime.now(),
            category=EventCategory.USER_ACTION,
            event_type=EventType.BOOK_DOWNLOAD,
            user_id=user_id,
            username=username,
            chat_type=chat_type,
            chat_id=chat_id or user_id,
            data=download_data.__dict__
        )

        self.log_event(event)

    def log_settings_change(
            self,
            user_id: int,
            username: str,
            setting_name: str,
            old_value: Any,
            new_value: Any,
            chat_type: str = "private",
            chat_id: Optional[int] = None
    ) -> None:
        """Логирует изменение настроек"""
        settings_data = SettingsChangeEvent(
            setting_name=setting_name,
            old_value=str(old_value),
            new_value=str(new_value)
        )

        event = LogEvent(
            timestamp=datetime.now(),
            category=EventCategory.USER_ACTION,
            event_type=EventType.SETTINGS_CHANGE,
            user_id=user_id,
            username=username,
            chat_type=chat_type,
            chat_id=chat_id or user_id,
            data=settings_data.__dict__
        )

        self.log_event(event)

    def log_user_action(
        self,
        event_type: EventType,
        user_id: int,
        username: str,
        data: Optional[Dict[str, Any]] = None,
        chat_type: str = "private",
        chat_id: Optional[int] = None,
        duration_ms: Optional[int] = None
    ) -> None:
        """Логирует произвольное действие пользователя"""
        event = LogEvent(
            timestamp=datetime.now(),
            category=EventCategory.USER_ACTION,
            event_type=event_type,
            user_id=user_id,
            username=username,
            chat_type=chat_type,
            chat_id=chat_id or user_id,
            data=data or {},
            duration_ms=duration_ms or 0
        )

        self.log_event(event)

    def log_author_info_view(
        self,
        user_id: int,
        username: str,
        author_id: int,
        author_name: Optional[str] = None,
        chat_type: str = "private",
        chat_id: Optional[int] = None
    ) -> None:
        """Логирует просмотр информации об авторе"""
        event = LogEvent(
            timestamp=datetime.now(),
            category=EventCategory.USER_ACTION,
            event_type=EventType.AUTHOR_INFO_VIEW,
            user_id=user_id,
            username=username,
            chat_type=chat_type,
            chat_id=chat_id or user_id,
            data={"author_id": author_id,
                  "author_name": author_name}
        )

        self.log_event(event)

    def log_book_reviews_view(
        self,
        user_id: int,
        username: str,
        book_id: int,
        chat_type: str = "private",
        chat_id: Optional[int] = None
    ) -> None:
        """Логирует просмотр отзывов о книге"""
        event = LogEvent(
            timestamp=datetime.now(),
            category=EventCategory.USER_ACTION,
            event_type=EventType.BOOK_REVIEWS_VIEW,
            user_id=user_id,
            username=username,
            chat_type=chat_type,
            chat_id=chat_id or user_id,
            data={"book_id": book_id}
        )

        self.log_event(event)

    def log_book_details_view(
        self,
        user_id: int,
        username: str,
        book_id: int,
        book_title: Optional[str] = None,
        chat_type: str = "private",
        chat_id: Optional[int] = None
    ) -> None:
        """Логирует просмотр детальной информации о книге"""
        event = LogEvent(
            timestamp=datetime.now(),
            category=EventCategory.USER_ACTION,
            event_type=EventType.BOOK_DETAILS_VIEW,
            user_id=user_id,
            username=username,
            chat_type=chat_type,
            chat_id=chat_id or user_id,
            data={"book_id": book_id,
                  "book_title": book_title}
        )

        self.log_event(event)

    def log_error(
            self,
            error_type: str,
            error_message: str,
            context: Optional[Dict[str, Any]] = None,
            user_id: Optional[int] = None,
            username: Optional[str] = None
    ) -> None:
        """Логирует ошибку"""
        event = LogEvent(
            timestamp=datetime.now(),
            category=EventCategory.ERROR,
            event_type=EventType.ERROR_TELEGRAM,
            user_id=user_id,
            username=username,
            chat_type="system",
            chat_id=None,
            data=context or {},
            error_type=error_type,
            error_message=error_message
        )

        self.log_event(event)

    def log_system(
            self,
            event_type: EventType,
            message: str,
            data: Optional[Dict[str, Any]] = None
    ) -> None:
        """Логирует системное событие"""
        event = LogEvent(
            timestamp=datetime.now(),
            category=EventCategory.SYSTEM,
            event_type=event_type,
            user_id=None,
            username=None,
            chat_type="system",
            chat_id=None,
            data=data or {'message': message}
        )

        self.log_event(event)


# Глобальный экземпляр
structured_logger = StructuredLogger()
