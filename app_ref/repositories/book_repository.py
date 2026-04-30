"""
Book Repository - Репозиторий для работы с книгами MariaDB
"""
from typing import List, Optional, Dict, Any, Tuple
import mysql.connector
from datetime import datetime, timedelta

from ..core.custom_types import (
    BookInfo, BookDetails, AuthorInfo,
    SeriesResult, AuthorResult
)
from ..core.cache import SimpleCache


class BookRepository:
    """
    Репозиторий для работы с книгами в MariaDB
    
    Отвечает за:
    - Поиск книг с фильтрами
    - Получение деталей книги/автора
    - Популярные книги и новинки
    - Статистику библиотеки
    - Кеширование результатов
    """
    
    def __init__(self, db_config: Dict[str, Any]):
        """
        Инициализация репозитория
        
        Args:
            db_config: Конфигурация подключения к MariaDB
        """
        self.db_config = db_config
        self.cache = SimpleCache(default_ttl=300)  # 5 минут кеша
        
        # Базовые поля для запросов
        self.base_fields = """
            b.BookID as FileName,
            UPPER(b.Lang) as SearchLang,
            b.Title,
            b.FileSize as BookSize,
            b.Year as SearchYear,
            CASE 
                WHEN b.FileSize <= 800 * 1024 THEN 'less800'
                WHEN b.FileSize > 800 * 1024 THEN 'more800'
            END as BookSizeCat,
            an.LastName,
            an.FirstName, 
            an.MiddleName,
            an.AvtorId as AuthorID,
            gl.GenreDesc AS Genre,
            sn.SeqName as SeriesTitle, 
            sn.SeqId as SeriesID, 
            ROUND(COALESCE(r.LibRate, 0)) as LibRate
        """
        
        # Базовые JOIN'ы
        self.base_joins = """
            LEFT JOIN cb_libavtor a ON a.BookID = b.BookID
            LEFT JOIN cb_libavtorname an ON an.AvtorID = a.AvtorID
            LEFT JOIN (
                SELECT bookid, MIN(genreid) as genreid
                FROM cb_libgenre
                GROUP BY bookid
            ) g ON g.BookID = b.BookID
            LEFT JOIN cb_libgenrelist gl ON gl.GenreID = g.GenreID
            LEFT JOIN cb_libseq s ON s.BookID = b.BookID
            LEFT JOIN cb_libseqname sn ON sn.SeqID = s.SeqID
            LEFT JOIN (
                SELECT BookId, AVG(CAST(Rate AS SIGNED)) as LibRate
                FROM cb_librate
                GROUP BY BookId
            ) r ON r.BookId = b.BookId
        """
    
    def _get_connection(self):
        """Получение подключения к БД"""
        return mysql.connector.connect(**self.db_config)
    
    async def search(
        self,
        query: str,
        lang: str = "",
        size_limit: str = "",
        rating_filter: Optional[str] = None,
        search_area: str = "b",
        series_id: int = 0,
        author_id: int = 0
    ) -> List[BookInfo]:
        """
        Поиск книг с применением фильтров
        
        Args:
            query: Поисковый запрос
            lang: Язык книг (ru/en/etc)
            size_limit: Ограничение размера (less800/more800)
            rating_filter: Фильтр по рейтингу (например "45")
            search_area: Область поиска (b/ba/aa)
            series_id: ID серии для фильтрации
            author_id: ID автора для фильтрации
        
        Returns:
            Список BookInfo
        """
        # НЕ КЭШИРУЕМ ПОИСКОВЫЕ ЗАПРОСЫ, ЭТО БЕССМЫСЛЕННО
        # cache_key = f"search:{query}:{lang}:{size_limit}:{rating_filter}:{search_area}:{series_id}:{author_id}"
        #
        # # Проверяем кеш
        # cached = self.cache.get(cache_key)
        # if cached:
        #     return cached
        
        # Строим SQL запрос
        sql = self._build_search_query(
            search_area, lang, size_limit, rating_filter, series_id, author_id
        )
        
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(sql, (query, query))
                rows = cursor.fetchall()
            
            # Преобразуем в BookInfo
            books = [BookInfo(*row) for row in rows]
            
            # # Сохраняем в кеш
            # self.cache.set(cache_key, books)
            
            return books
            
        except Exception as e:
            print(f"Error in search: {e}")
            return []
    
    async def get_book_info(self, book_id: int) -> Optional[BookDetails]:
        """
        Получение детальной информации о книге
        
        Args:
            book_id: ID книги
        
        Returns:
            BookDetails или None
        """
        cache_key = f"book_info:{book_id}"
        
        # Проверяем кеш
        cached = self.cache.get(cache_key)
        if cached:
            return cached
        
        sql = """
            SELECT 
                b.BookID,
                b.Title,
                b.Year,
                sn.SeqName as SeriesTitle,
                s.SeqId as SeriesID,
                GROUP_CONCAT(CONCAT(gl.GenreID, ',', gl.GenreDesc) SEPARATOR ',') as Genres,
                GROUP_CONCAT(CONCAT(an.AvtorID, ',', an.LastName, ' ', an.FirstName, ' ', an.MiddleName) SEPARATOR ',') as Authors,
                NULL as CoverURL,  -- Будет заполнено отдельно
                b.FileSize as Size,
                NULL as Pages,  -- Нет в исходной БД
                b.Lang as Lang,
                ROUND(COALESCE(r.LibRate, 0)) as Rate
            FROM cb_libbook b
            LEFT JOIN cb_libavtor a ON a.BookID = b.BookID
            LEFT JOIN cb_libavtorname an ON an.AvtorID = a.AvtorID
            LEFT JOIN (
                SELECT bookid, MIN(genreid) as genreid
                FROM cb_libgenre
                GROUP BY bookid
            ) g ON g.BookID = b.BookID
            LEFT JOIN cb_libgenrelist gl ON gl.GenreID = g.GenreID
            LEFT JOIN cb_libseq s ON s.BookID = b.BookID
            LEFT JOIN cb_libseqname sn ON sn.SeqID = s.SeqID
            LEFT JOIN (
                SELECT BookId, AVG(CAST(Rate AS SIGNED)) as LibRate
                FROM cb_librate
                GROUP BY BookId
            ) r ON r.BookId = b.BookId
            WHERE b.BookID = %s
            GROUP BY b.BookID, b.Title, b.Year, sn.SeqName, s.SeqId, b.FileSize, b.Lang
        """
        
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(sql, (book_id,))
                row = cursor.fetchone()
            
            if not row:
                return None
            
            book_info = BookDetails(*row)
            
            # Сохраняем в кеш
            self.cache.set(cache_key, book_info)
            
            return book_info
            
        except Exception as e:
            print(f"Error getting book info: {e}")
            return None
    
    async def get_author_info(self, author_id: int) -> Optional[AuthorInfo]:
        """
        Получение информации об авторе
        
        Args:
            author_id: ID автора
        
        Returns:
            AuthorInfo или None
        """
        cache_key = f"author_info:{author_id}"
        
        # Проверяем кеш
        cached = self.cache.get(cache_key)
        if cached:
            return cached
        
        sql = """
            SELECT 
                an.AvtorID,
                CONCAT(an.LastName, ' ', an.FirstName, ' ', an.MiddleName) as Name,
                NULL as PhotoURL,  -- Будет заполнено отдельно
                aa.Title,
                aa.Body as Biography
            FROM cb_libavtorname an
            LEFT JOIN cb_libaannotations aa ON aa.AvtorId = an.AvtorID
            WHERE an.AvtorID = %s
        """
        
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(sql, (author_id,))
                row = cursor.fetchone()
            
            if not row:
                return None
            
            author_info = AuthorInfo(*row)
            
            # Сохраняем в кеш
            self.cache.set(cache_key, author_info)
            
            return author_info
            
        except Exception as e:
            print(f"Error getting author info: {e}")
            return None
    
    async def get_book_details(self, book_id: int) -> Optional[Dict[str, Any]]:
        """
        Получение детальной информации о книге (аннотация)
        
        Args:
            book_id: ID книги
        
        Returns:
            Словарь с информацией о книге или None
        """
        cache_key = f"book_details:{book_id}"
        
        # Проверяем кеш
        cached = self.cache.get(cache_key)
        if cached:
            return cached
        
        sql = """
            SELECT
                b.BookID,
                b.Title,
                ba.Body as annotation
            FROM cb_libbook b
            LEFT JOIN cb_libbannotations ba ON ba.BookID = b.BookID
            WHERE b.BookID = %s
        """
        
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor(dictionary=True)
                cursor.execute(sql, (book_id,))
                row = cursor.fetchone()
            
            if not row:
                return None
            
            # Сохраняем в кеш
            self.cache.set(cache_key, row)
            
            return row
            
        except Exception as e:
            print(f"Error getting book details: {e}")
            return None
    
    async def get_book_reviews(self, book_id: int) -> List[Dict[str, Any]]:
        """
        Получение отзывов о книге
        
        Args:
            book_id: ID книги
        
        Returns:
            Список отзывов
        """
        cache_key = f"book_reviews:{book_id}"
        
        # Проверяем кеш
        cached = self.cache.get(cache_key)
        if cached:
            return cached
        
        sql = """
            SELECT
                name,
                time,
                review
            FROM cb_libreviews
            WHERE BookID = %s
            ORDER BY time DESC
            LIMIT 50
        """
        
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor(dictionary=True)
                cursor.execute(sql, (book_id,))
                rows = cursor.fetchall()
            
            # Сохраняем в кеш
            self.cache.set(cache_key, rows, ttl=1800)  # 30 минут для отзывов
            
            return rows
            
        except Exception as e:
            print(f"Error getting book reviews: {e}")
            return []
    
    async def get_popular(
        self,
        lang: str = "",
        size_limit: str = "",
        rating_filter: Optional[str] = None,
        days_back: int = 7
    ) -> List[BookInfo]:
        """
        Получение популярных книг и новинок
        
        Args:
            lang: Язык книг
            size_limit: Ограничение размера
            rating_filter: Фильтр по рейтингу
            days_back: Количество дней назад (0 = новинки)
        
        Returns:
            Список BookInfo
        """
        cache_key = f"popular:{lang}:{size_limit}:{rating_filter}:{days_back}"
        
        # Проверяем кеш
        cached = self.cache.get(cache_key)
        if cached:
            return cached
        
        # Базовый запрос
        sql = f"""
            SELECT 
                {self.base_fields},
                0 as Relevance
            FROM cb_libbook b
            {self.base_joins}
            WHERE b.Deleted = '0'
        """
        
        # Добавляем условия
        conditions = []
        
        if lang:
            conditions.append(f"UPPER(b.Lang) = '{lang.upper()}'")
        
        if size_limit:
            if size_limit == 'less800':
                conditions.append("b.FileSize <= 800 * 1024")
            elif size_limit == 'more800':
                conditions.append("b.FileSize > 800 * 1024")
        
        if rating_filter:
            conditions.append(f"ROUND(COALESCE(r.LibRate, 0)) IN ({rating_filter})")
        
        # Для новинок (days_back=0) сортируем по ID
        # Для популярных - по рейтингу и количеству рекомендаций
        if days_back == 0:
            # Новинки
            sql += " AND " + " AND ".join(conditions) if conditions else ""
            sql += " ORDER BY b.BookID DESC LIMIT 200"
        else:
            # Популярные (упрощенная логика)
            sql += " AND " + " AND ".join(conditions) if conditions else ""
            sql += " ORDER BY LibRate DESC, b.BookID DESC LIMIT 200"
        
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(sql)
                rows = cursor.fetchall()
            
            books = [BookInfo(*row) for row in rows]
            
            # Сохраняем в кеш
            self.cache.set(cache_key, books, ttl=3600)  # 1 час для популярных
            
            return books
            
        except Exception as e:
            print(f"Error getting popular books: {e}")
            return []
    
    def get_library_stats(self) -> Dict[str, Any]:
        """
        Получение статистики библиотеки (как в старой архитектуре)
        
        Returns:
            Словарь со статистикой
        """
        cache_key = "library_stats"
        
        # Проверяем кеш
        cached = self.cache.get(cache_key)
        if cached:
            return cached
        
        stats = {}
        
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                
                # Статистика книг (как в старой архитектуре)
                cursor.execute("""
                    SELECT
                        MAX(date(time)) as max_update_date,
                        COUNT(*) as books_cnt,
                        MAX(bookid) as max_filename
                    FROM cb_libbook b
                    WHERE b.Deleted = '0'
                """)
                books_stats = cursor.fetchone()
                
                # Количество авторов
                cursor.execute("SELECT COUNT(*) FROM cb_libavtorname")
                authors_cnt = cursor.fetchone()[0]
                
                # Количество жанров
                cursor.execute("SELECT COUNT(*) FROM cb_libgenrelist")
                genres_cnt = cursor.fetchone()[0]
                
                # Количество серий
                cursor.execute("SELECT COUNT(*) FROM cb_libseqname")
                series_cnt = cursor.fetchone()[0]
                
                # Количество языков
                cursor.execute("SELECT COUNT(DISTINCT Lang) FROM cb_libbook WHERE Deleted = '0'")
                langs_cnt = cursor.fetchone()[0]
                
                stats = {
                    'last_update': books_stats[0],
                    'books_count': books_stats[1],
                    'max_filename': books_stats[2],
                    'authors_count': authors_cnt,
                    'genres_count': genres_cnt,
                    'series_count': series_cnt,
                    'languages_count': langs_cnt
                }
            
            # Сохраняем в кеш (на 1 час)
            self.cache.set(cache_key, stats, ttl=3600)
            
            return stats
                
        except Exception as e:
            print(f"Error getting library stats: {e}")
            return {}
            
    async def get_parent_genres_with_counts(self) -> List[Tuple[str, int]]:
        """
        Получает родительские жанры с количеством книг в каждом
        
        Returns:
            Список кортежей (название_жанра, количество_книг)
        """
        cache_key = "parent_genres"
        
        # Проверяем кеш
        cached = self.cache.get(cache_key)
        if cached:
            return cached
        
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                query = """
                    SELECT
                        COALESCE(gl.GenreMeta, 'Неотсортированное') as genre_name,
                        COUNT(b.BookId) as book_count
                    FROM cb_libbook b
                    LEFT OUTER JOIN cb_libgenre g ON g.BookId = b.BookId
                    LEFT OUTER JOIN cb_libgenrelist gl ON gl.GenreId = g.GenreId
                    WHERE b.Deleted = '0'
                    GROUP BY COALESCE(gl.GenreMeta, 'Неотсортированное')
                    ORDER BY genre_name
                """
                cursor.execute(query)
                results = cursor.fetchall()
                genres = [(genre_name, count) for genre_name, count in results]
                
                # Сохраняем в кеш (на 1 час, т.к. жанры меняются редко)
                self.cache.set(cache_key, genres, ttl=3600)
                
                return genres
        except Exception as e:
            print(f"Error getting parent genres: {e}")
            return []

    async def get_child_genres_with_counts(self, parent_genre: str) -> List[Tuple[str, int, int]]:
        """
        Получает дочерние жанры для указанного родительского жанра
        
        Args:
            parent_genre: Название родительского жанра
            
        Returns:
            Список кортежей (название_жанра, количество_книг, genre_id)
        """
        cache_key = f"child_genres:{parent_genre}"
        
        # Проверяем кеш
        cached = self.cache.get(cache_key)
        if cached:
            return cached
        
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                query = """
                    SELECT
                        gl.GenreDesc as genre_name,
                        COUNT(g.BookId) as book_count,
                        gl.GenreId as genre_id
                    FROM cb_libbook b
                    LEFT OUTER JOIN cb_libgenre g ON g.BookId = b.BookId
                    LEFT OUTER JOIN cb_libgenrelist gl ON gl.GenreId = g.GenreId
                    WHERE b.Deleted = '0'
                      AND gl.GenreMeta = %s
                    GROUP BY gl.GenreDesc, gl.GenreId
                    ORDER BY genre_name
                """
                cursor.execute(query, (parent_genre,))
                results = cursor.fetchall()
                genres = [(genre_name, count, genre_id) for genre_name, count, genre_id in results]
                
                # Сохраняем в кеш (на 1 час)
                self.cache.set(cache_key, genres, ttl=3600)
                
                return genres
        except Exception as e:
            print(f"Error getting child genres for '{parent_genre}': {e}")
            return []
    
    def _build_search_query(
        self,
        search_area: str,
        lang: str,
        size_limit: str,
        rating_filter: Optional[str],
        series_id: int,
        author_id: int
    ) -> str:
        """
        Строит SQL запрос для поиска
        
        Args:
            search_area: Область поиска
            lang: Язык
            size_limit: Ограничение размера
            rating_filter: Фильтр рейтинга
            series_id: ID серии
            author_id: ID автора
        
        Returns:
            SQL запрос
        """
        # Определяем таблицу и поле для полнотекстового поиска
        if search_area == 'b':
            search_table = "cb_libbook_fts fts"
            search_join = "JOIN cb_libbook b ON b.BookID = fts.BookID"
            match_field = "fts.FT"
        elif search_area == 'ba':
            search_table = "cb_libbannotations ba"
            search_join = "JOIN cb_libbook b ON b.BookID = ba.BookID"
            match_field = "ba.Body"
        elif search_area == 'aa':
            search_table = "cb_libaannotations aa"
            search_join = """
                JOIN cb_libavtor ab ON ab.AvtorId = aa.AvtorId
                JOIN cb_libbook b ON b.BookID = ab.BookID
            """
            match_field = "aa.Body"
        else:
            search_table = "cb_libbook_fts fts"
            search_join = "JOIN cb_libbook b ON b.BookID = fts.BookID"
            match_field = "fts.FT"
        
        # Базовый запрос
        sql = f"""
            SELECT * FROM (
                SELECT 
                    {self.base_fields},
                    MATCH({match_field}) AGAINST(%s IN BOOLEAN MODE) as Relevance,
                    ROW_NUMBER() OVER (PARTITION BY FileName ORDER BY FileName) AS rn
                FROM {search_table}
                {search_join}
                {self.base_joins}
                WHERE b.Deleted = '0'
                  AND MATCH({match_field}) AGAINST(%s IN BOOLEAN MODE)
            ) as ranked
        """
        
        # Добавляем условия фильтрации
        conditions = ["rn = 1"]
        
        if lang:
            conditions.append(f"SearchLang = '{lang.upper()}'")
        
        if size_limit:
            conditions.append(f"BookSizeCat = '{size_limit}'")
        
        if rating_filter:
            conditions.append(f"ROUND(COALESCE(r.LibRate, 0)) IN ({rating_filter})")
        
        if series_id != 0:
            conditions.append(f"SeriesID = {series_id}")
        
        if author_id != 0:
            conditions.append(f"AuthorID = {author_id}")
        
        sql += f" WHERE {' AND '.join(conditions)}"
        
        # Сортировка и лимит
        sql += " ORDER BY Relevance DESC, FileName DESC LIMIT 2000"
        
        return sql
    
    async def get_available_languages(self) -> List[Tuple[str, str]]:
        """
        Получение списка доступных языков книг
        
        Returns:
            Список кортежей (код_языка, количество_книг)
        """
        cache_key = "available_languages"
        
        # Проверяем кеш
        cached = self.cache.get(cache_key)
        if cached:
            return cached
        
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                query = """
                    SELECT Lang, COUNT(Lang) AS count
                    FROM cb_libbook
                    WHERE Deleted = '0'
                      AND Lang IS NOT NULL
                      AND Lang != ''
                    GROUP BY Lang
                    ORDER BY count DESC
                """
                cursor.execute(query)
                results = cursor.fetchall()
                
                # Сохраняем в кеш (на 1 час, т.к. языки меняются редко)
                self.cache.set(cache_key, results, ttl=3600)
                
                return results
        except Exception as e:
            print(f"Error getting available languages: {e}")
            return []
    
    def cleanup_cache(self) -> int:
        """
        Очистка просроченных записей из кеша
        
        Returns:
            Количество удаленных записей
        """
        return self.cache.cleanup_expired()