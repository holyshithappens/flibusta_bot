"""
Search Service - Сервис поиска книг
"""
from typing import List, Optional
from dataclasses import dataclass

from ..core.custom_types import (
    BookInfo, SeriesResult, AuthorResult, UserSettings
)
from ..repositories.book_repository import BookRepository


@dataclass
class SearchParams:
    """Параметры поиска"""
    query: str
    settings: UserSettings
    series_id: Optional[int] = None
    author_id: Optional[int] = None


class SearchService:
    """
    Сервис для выполнения поиска книг
    
    Отвечает за:
    - Поиск книг с фильтрами
    - Группировку по сериям
    - Группировку по авторам
    - Популярные книги и новинки
    - Пагинацию результатов
    """
    
    def __init__(self, book_repo: BookRepository, logger=None):
        """
        Инициализация сервиса
        
        Args:
            book_repo: Репозиторий для работы с книгами
            logger: Логгер (опционально)
        """
        self.book_repo = book_repo
        self.logger = logger
    
    async def search_books(self, params: SearchParams) -> dict:
        """
        Поиск книг с применением фильтров
        
        Args:
            params: Параметры поиска
        
        Returns:
            Словарь с результатами:
            {
                'books': List[BookInfo],
                'total_count': int,
                'pages': List[List[BookInfo]]
            }
        """
        books = await self.book_repo.search(
            query=params.query,
            lang=params.settings.lang,
            size_limit=params.settings.book_size,
            rating_filter=params.settings.rating,
            search_area=params.settings.search_area,
            series_id=params.series_id or 0,
            author_id=params.author_id or 0
        )
        
        pages = self._paginate(books, params.settings.max_books)
        
        return {
            'books': books,
            'total_count': len(books),
            'pages': pages
        }
    
    async def search_series(self, params: SearchParams) -> List[SeriesResult]:
        """
        Поиск с группировкой по сериям
        
        Args:
            params: Параметры поиска
        
        Returns:
            Список SeriesResult
        """
        # Получаем все книги
        books = await self.book_repo.search(
            query=params.query,
            lang=params.settings.lang,
            size_limit=params.settings.book_size,
            rating_filter=params.settings.rating,
            search_area=params.settings.search_area,
            series_id=params.series_id or 0,
            author_id=params.author_id or 0
        )
        
        # Группируем по сериям
        series_dict = {}
        for book in books:
            if book.series_title and book.series_id:
                key = (book.series_title, book.series_id)
                if key not in series_dict:
                    series_dict[key] = 0
                series_dict[key] += 1
        
        # Преобразуем в SeriesResult
        results = [
            SeriesResult(
                series_title=title,
                series_id=series_id,
                book_count=count
            )
            for (title, series_id), count in series_dict.items()
        ]
        
        # Сортируем по количеству книг
        results.sort(key=lambda x: x.book_count, reverse=True)
        
        return results
    
    async def search_authors(self, params: SearchParams) -> List[AuthorResult]:
        """
        Поиск с группировкой по авторам
        
        Args:
            params: Параметры поиска
        
        Returns:
            Список AuthorResult
        """
        # Получаем все книги
        books = await self.book_repo.search(
            query=params.query,
            lang=params.settings.lang,
            size_limit=params.settings.book_size,
            rating_filter=params.settings.rating,
            search_area=params.settings.search_area,
            series_id=params.series_id or 0,
            author_id=params.author_id or 0
        )
        
        # Группируем по авторам
        authors_dict = {}
        for book in books:
            if book.author_id and (book.last_name or book.first_name):
                # Формируем имя автора
                name_parts = []
                if book.last_name:
                    name_parts.append(book.last_name)
                if book.first_name:
                    name_parts.append(book.first_name)
                if book.middle_name:
                    name_parts.append(book.middle_name)
                
                author_name = ' '.join(name_parts)
                key = (author_name, book.author_id)
                
                if key not in authors_dict:
                    authors_dict[key] = 0
                authors_dict[key] += 1
        
        # Преобразуем в AuthorResult
        results = [
            AuthorResult(
                author_name=name,
                author_id=author_id,
                book_count=count
            )
            for (name, author_id), count in authors_dict.items()
        ]
        
        # Сортируем по количеству книг
        results.sort(key=lambda x: x.book_count, reverse=True)
        
        return results
    
    async def get_popular_books(
        self, 
        settings: UserSettings, 
        days_back: int = 7
    ) -> dict:
        """
        Получение популярных книг
        
        Args:
            settings: Настройки пользователя
            days_back: Количество дней назад
        
        Returns:
            Словарь с результатами (как search_books)
        """
        books = await self.book_repo.get_popular(
            lang=settings.lang,
            size_limit=settings.book_size,
            rating_filter=settings.rating,
            days_back=days_back
        )
        
        pages = self._paginate(books, settings.max_books)
        
        return {
            'books': books,
            'total_count': len(books),
            'pages': pages
        }
    
    async def get_new_books(self, settings: UserSettings) -> dict:
        """
        Получение новинок
        
        Args:
            settings: Настройки пользователя
        
        Returns:
            Словарь с результатами
        """
        return await self.get_popular_books(settings, days_back=0)
    
    def _paginate(self, items: List, page_size: int) -> List[List]:
        """
        Разбивает список на страницы
        
        Args:
            items: Список элементов
            page_size: Размер страницы
        
        Returns:
            Список страниц
        """
        if not items:
            return []
        
        return [
            items[i:i + page_size]
            for i in range(0, len(items), page_size)
        ]
    
    def format_results_header(
        self, 
        total_count: int, 
        page: int, 
        total_pages: int,
        query: str = ""
    ) -> str:
        """
        Форматирует заголовок с результатами
        
        Args:
            total_count: Общее количество
            page: Текущая страница
            total_pages: Всего страниц
            query: Поисковый запрос
        
        Returns:
            Отформатированный текст
        """
        header = f"📚 Найдено книг: {total_count}"
        
        if query:
            header += f"\n🔍 Запрос: {query}"
        
        if total_pages > 1:
            header += f"\n📄 Страница {page + 1} из {total_pages}"
        
        return header