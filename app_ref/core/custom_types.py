"""
Определения типов для проекта Flibusta Bot
"""

from dataclasses import dataclass
from typing import Optional, List
from enum import Enum


# ===== ENUMS (перечисления) =====

class SearchType(Enum):
    """Тип группировки результатов поиска"""
    BOOKS = "books"
    SERIES = "series"
    AUTHORS = "authors"


class SearchArea(Enum):
    """Область поиска"""
    BASIC = "b"  # основной поиск (название, авторы, жанры, серии)
    BOOK_ANNOTATIONS = "ba"  # по аннотациям книг
    AUTHOR_ANNOTATIONS = "aa"  # по аннотациям авторов


class BookFormat(Enum):
    """Формат скачивания книги"""
    FB2 = "fb2"
    EPUB = "epub"
    MOBI = "mobi"


# ===== НАСТРОЙКИ ПОЛЬЗОВАТЕЛЯ =====

@dataclass
class UserSettings:
    """Настройки пользователя"""
    user_id: int
    max_books: int = 20
    lang: str = ""
    book_format: str = "fb2"  # Пока строка, потом поменяем на BookFormat
    search_type: str = "books"  # Пока строка, потом поменяем на SearchType
    rating: str = ""
    book_size: str = ""
    search_area: str = "b"  # Пока строка, потом поменяем на SearchArea
    is_blocked: bool = False
    last_news_date: str = "2000-01-01"


# ===== КНИГИ =====

@dataclass
class BookInfo:
    """Краткая информация о книге (результат поиска)"""
    file_name: str  # BookID
    search_lang: str
    title: str
    book_size: int
    search_year: int
    book_size_cat: str
    last_name: Optional[str]
    first_name: Optional[str]
    middle_name: Optional[str]
    author_id: Optional[int]
    genre: Optional[str]
    series_title: Optional[str]
    series_id: Optional[int]
    lib_rate: float
    relevance: float


@dataclass
class BookDetails:
    """Полная информация о книге"""
    bookid: int
    title: str
    year: Optional[int]
    series: Optional[str]
    seqid: Optional[int]
    genres: str  # comma-separated "id,name,id,name"
    authors: str  # comma-separated "id,lastname firstname,id,lastname firstname"
    cover_url: Optional[str]
    size: int
    pages: Optional[int]
    lang: str
    rate: Optional[float]


# ===== АВТОРЫ =====

@dataclass
class AuthorInfo:
    """Информация об авторе"""
    author_id: int
    last_name: str
    first_name: Optional[str]
    middle_name: Optional[str]
    photo_url: Optional[str]
    title: Optional[str]
    biography: Optional[str]


# ===== РЕЗУЛЬТАТЫ ПОИСКА =====

@dataclass
class SeriesResult:
    """Результат группировки по сериям"""
    series_title: str
    series_id: int
    book_count: int


@dataclass
class AuthorResult:
    """Результат группировки по авторам"""
    author_name: str
    book_count: int
    author_id: int