"""
Book Service - Сервис для работы с книгами
"""
from typing import Optional, Tuple, List, Dict, Any
import asyncio
import aiohttp

from ..core.custom_types import BookDetails, AuthorInfo
from ..repositories.book_repository import BookRepository
from .flibusta_service import FlibustaService
from ..utils.formatter import format_size


class BookService:
    """
    Сервис для работы с книгами
    
    Отвечает за:
    - Получение деталей книги
    - Получение информации об авторе
    - Скачивание книг
    - Получение отзывов
    """
    
    def __init__(
        self,
        book_repo: BookRepository,
        flibusta_service: Optional[FlibustaService] = None,
        logger=None  # Optional logger for compatibility
    ):
        """
        Инициализация сервиса
        
        Args:
            book_repo: Репозиторий для работы с книгами
            flibusta_service: Сервис для скачивания книг (опционально)
            logger: Логгер (опционально)
        """
        self.book_repo = book_repo
        self.flibusta_service = flibusta_service or FlibustaService(logger=logger)
        self.logger = logger
    
    async def get_book_details(self, book_id: int) -> Optional[BookDetails]:
        """
        Получение детальной информации о книге
        
        Args:
            book_id: ID книги
        
        Returns:
            BookDetails или None
        """
        return await self.book_repo.get_book_info(book_id)
    
    async def get_author_details(self, author_id: int) -> Optional[AuthorInfo]:
        """
        Получение детальной информации об авторе
        
        Args:
            author_id: ID автора
        
        Returns:
            AuthorInfo или None
        """
        return await self.book_repo.get_author_info(author_id)
    
    async def download_book(
        self,
        book_id: int,
        format: str,
        try_auth: bool = True
    ) -> Optional[Tuple[bytes, str]]:
        """
        Скачивание книги (двухэтапная попытка)
        
        Args:
            book_id: ID книги
            format: Формат (fb2/epub/mobi)
            try_auth: Пробовать с авторизацией если без неё не получилось
        
        Returns:
            Кортеж (book_data, filename) или None
        """
        try:
            # Первая попытка — без авторизации
            book_data, filename = await self.flibusta_service.download_book(
                book_id, format, auth=False
            )
             
            # Если не удалось и try_auth=True — вторая попытка с авторизацией
            if not book_data and try_auth:
                book_data, filename = await self.flibusta_service.download_book(
                    book_id, format, auth=True
                )
            
            if book_data:
                # Логируем успешное скачивание
                if self.logger:
                    self.logger.log_download(
                        user_id=0,  # Пока неизвестен, будет установлен в обработчике
                        username="system",
                        book_id=book_id,
                        book_title="",  # Будет получено из БД
                        format=format,
                        file_size=len(book_data),
                        success=True,
                        via_tmpfiles=False,
                        chat_type="private",
                        chat_id=0
                    )
                
                return book_data, filename
            else:
                # Логируем неудачное скачивание
                if self.logger:
                    self.logger.log_error(
                        error_type="download_failed",
                        error_message="Book not found or unavailable",
                        context={"book_id": book_id, "format": format}
                    )
                
                return None
                
        except Exception as e:
            if self.logger:
                self.logger.log_error(
                    error_type="download_exception",
                    error_message=str(e),
                    context={"book_id": book_id, "format": format}
                )
            return None
    
    async def get_book_cover(self, book_id: int) -> Optional[str]:
        """
        Получение URL обложки книги
        
        Args:
            book_id: ID книги
        
        Returns:
            URL обложки или None
        """
        # Получаем детали книги
        book_info = await self.get_book_details(book_id)
        
        if not book_info:
            return None
        
        # Формируем URL обложки (логика из старого кода)
        # В реальной реализации может быть получение из внешнего источника
        return None
    
    async def get_book_reviews(self, book_id: int) -> str:
        """
        Получение отзывов о книге
        
        Args:
            book_id: ID книги
        
        Returns:
            Отформатированный текст с отзывами
        """
        # В реальной реализации нужно получать из БД
        # Пока заглушка
        return "Отзывы пока недоступны"
    
    async def get_author_photo(self, author_id: int) -> Optional[str]:
        """
        Получение URL фото автора
        
        Args:
            author_id: ID автора
        
        Returns:
            URL фото или None
        """
        # Получаем детали автора
        author_info = await self.get_author_details(author_id)
        
        if not author_info:
            return None
        
        # Формируем URL фото (логика из старого кода)
        # В реальной реализации может быть получение из внешнего источника
        return None
    
    def format_book_info(self, book: BookDetails) -> str:
        """
        Форматирует информацию о книге в текст
        
        Args:
            book: Детали книги
        
        Returns:
            Отформатированный текст
        """
        lines = []
        
        # Название
        lines.append(f"📖 <b>{book.title}</b>")
        
        # Авторы
        if book.authors:
            lines.append(f"👤 {book.authors}")
        
        # Год
        if book.year:
            lines.append(f"📅 Год: {book.year}")
        
        # Серия
        if book.series:
            series_text = book.series
            if book.seqid:
                series_text += f" (кн. {book.seqid})"
            lines.append(f"📚 Серия: {series_text}")
        
        # Жанры
        if book.genres:
            lines.append(f"🎭 Жанры: {book.genres}")
        
        # Размер
        if book.size:
            lines.append(f"💾 Размер: {self._format_size(book.size)}")
        
        # Язык
        if book.lang:
            lines.append(f"🌐 Язык: {book.lang}")
        
        # Рейтинг
        if book.rate:
            lines.append(f"⭐ Рейтинг: {book.rate}")
        
        return "\n".join(lines)
    
    def format_author_info(self, author: AuthorInfo) -> str:
        """
        Форматирует информацию об авторе в текст
        
        Args:
            author: Информация об авторе
        
        Returns:
            Отформатированный текст
        """
        lines = []
        
        # Имя
        name = f"{author.last_name} {author.first_name or ''} {author.middle_name or ''}".strip()
        lines.append(f"👤 <b>{name}</b>")
        
        # Заголовок
        if author.title:
            lines.append(f"🏷️ {author.title}")
        
        # Биография
        if author.biography:
            # Обрезаем длинную биографию
            bio = author.biography
            if len(bio) > 500:
                bio = bio[:500] + "..."
            lines.append(f"\n{bio}")
        
        return "\n".join(lines)
    
    def _format_size(self, size_bytes: int) -> str:
        """
        Форматирует размер файла
        
        Args:
            size_bytes: Размер в байтах
        
        Returns:
            Отформатированная строка
        """
        return format_size(size_bytes)
    
    async def download_book_with_fallback(
        self,
        book_id: int,
        format: str,
        timeout: int = 30
    ) -> Tuple[Optional[bytes], Optional[str], bool]:
        """
        Скачивание книги с обработкой таймаута и загрузкой в облако
        
        Args:
            book_id: ID книги
            format: Формат (fb2/epub/mobi)
            timeout: Таймаут в секундах
        
        Returns:
            Кортеж (book_data, filename, via_tmpfiles)
            - book_data: Данные книги или None
            - filename: Имя файла или None
            - via_tmpfiles: True если использовался облачный сервис
        """
        try:
            # Пытаемся скачать книгу
            result = await asyncio.wait_for(
                self.download_book(book_id, format, try_auth=True),
                timeout=timeout
            )
            
            if result:
                book_data, filename = result
                return book_data, filename, False
            else:
                return None, None, False
                
        except asyncio.TimeoutError:
            # Таймаут - пытаемся скачать еще раз для загрузки в облако
            try:
                result = await self.download_book(book_id, format, try_auth=True)
                if result:
                    book_data, filename = result
                    
                    # Загружаем в облако
                    cloud_url = await self.upload_to_tmpfiles(book_data, filename or f"{book_id}.{format}")
                    
                    if cloud_url:
                        # Логируем успешную загрузку в облако
                        if self.logger:
                            self.logger.log_download(
                                user_id=0,
                                username="system",
                                book_id=book_id,
                                book_title="",
                                format=format,
                                file_size=len(book_data),
                                success=True,
                                via_tmpfiles=True,
                                chat_type="private",
                                chat_id=0,
                                cloud_url=cloud_url
                            )
                        
                        return book_data, filename, True
                
                return None, None, False
                
            except Exception as e:
                if self.logger:
                    self.logger.log_error(
                        error_type="cloud_upload_failed",
                        error_message=str(e),
                        context={"book_id": book_id, "format": format}
                    )
                return None, None, False
        
        except Exception as e:
            if self.logger:
                self.logger.log_error(
                    error_type="download_with_fallback_failed",
                    error_message=str(e),
                    context={"book_id": book_id, "format": format}
                )
            return None, None, False
    
    async def get_book_title(self, book_id: int) -> str:
        """
        Получение названия книги безопасно (кеш → БД → fallback)
        
        Args:
            book_id: ID книги
        
        Returns:
            Название книги или "Book #{book_id}"
        """
        try:
            # Пытаемся получить из репозитория
            book_details = await self.get_book_details(book_id)
            if book_details and book_details.title:
                return book_details.title
        except Exception as e:
            if self.logger:
                self.logger.log_error(
                    error_type="get_book_title_failed",
                    error_message=str(e),
                    context={"book_id": book_id}
                )
        
        # Fallback
        return f"Book #{book_id}"
    
    def get_book_url(self, book_id: int) -> str:
        """
        Получение URL страницы книги
        
        Args:
            book_id: ID книги
        
        Returns:
            URL страницы книги
        """
        return self.flibusta_service.get_book_url(book_id)
     
    def get_download_url(self, book_id: int, format: str) -> str:
        """
        Получение URL для скачивания книги
        
        Args:
            book_id: ID книги
            format: Формат книги
        
        Returns:
            URL для скачивания
        """
        return self.flibusta_service.get_download_url(book_id, format)
    
    async def upload_to_tmpfiles(self, file, file_name: str) -> Optional[str]:
        """
        Загружает файл на tmpfiles.org и возвращает URL для скачивания
        
        Args:
            file: Файл для загрузки
            file_name: Имя файла
        
        Returns:
            URL для скачивания или None
        """
        try:
            async with aiohttp.ClientSession() as session:
                form_data = aiohttp.FormData()
                form_data.add_field("file", file, filename=file_name)
                params = {"duration": "15m"}

                async with session.post("https://tmpfiles.org/api/v1/upload", data=form_data, params=params) as response:
                    if response.status == 200:
                        result = await response.json()
                        return result["data"]["url"]
                    return None
        except Exception as e:
            if self.logger:
                self.logger.log_error(
                    error_type="cloud_upload_failed",
                    error_message=str(e),
                    context={"file_name": file_name}
                )
            return None
      
    async def get_available_languages(self) -> List[Tuple[str, str]]:
        """
        Получение списка доступных языков книг
        
        Returns:
            Список кортежей (код_языка, количество_книг)
        """
        return await self.book_repo.get_available_languages()
    
    def get_library_stats(self) -> Dict[str, Any]:
        """
        Получение статистики библиотеки
        
        Returns:
            Словарь со статистикой
        """
        return self.book_repo.get_library_stats()
    
    async def get_parent_genres_with_counts(self) -> List[Tuple[str, int]]:
        """
        Получение родительских жанров с количеством книг
        
        Returns:
            Список кортежей (название_жанра, количество_книг)
        """
        return await self.book_repo.get_parent_genres_with_counts()
    
    async def get_child_genres_with_counts(self, parent_genre: str) -> List[Tuple[str, int, int]]:
        """
        Получение дочерних жанров для указанного родительского жанра
        
        Args:
            parent_genre: Название родительского жанра
        
        Returns:
            Список кортежей (название_жанра, количество_книг, genre_id)
        """
        return await self.book_repo.get_child_genres_with_counts(parent_genre)
    
    async def close(self):
        """Закрытие ресурсов"""
        await self.flibusta_service.close()