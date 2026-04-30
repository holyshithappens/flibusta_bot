"""
Flibusta Service - Сервис для работы с сайтом Flibusta

Новая реализация с:
- Полной типизацией
- Интеграцией с StructuredLogger
- Обработкой ошибок
- Поддержкой fallback стратегий
"""
import os
import re
from typing import Optional, Tuple
from urllib.parse import unquote

import aiohttp
from bs4 import BeautifulSoup

from ..core.structured_logger import StructuredLogger
from ..core.logging_schema import EventType


class FlibustaService:
    """
    Сервис для взаимодействия с сайтом Flibusta
    
    Возможности:
    - Скачивание книг (с авторизацией и без)
    - Получение обложек книг
    - Получение фотографий авторов
    - Формирование URL для книг, авторов, серий, жанров
    - Управление сессиями
    """
    
    def __init__(
        self,
        base_url: str = "https://flibusta.is",
        logger: Optional[StructuredLogger] = None
    ):
        """
        Инициализация сервиса
        
        Args:
            base_url: Базовый URL сайта Flibusta
            logger: Логгер для структурированного логирования
        """
        self.base_url = base_url
        self.logger = logger or StructuredLogger()
        
        # Сессии
        self._session: Optional[aiohttp.ClientSession] = None
        self._auth_session: Optional[aiohttp.ClientSession] = None
        self._is_logged_in: bool = False
        
        # Учетные данные
        self._username = os.getenv("FLIBUSTA_USERNAME", "")
        self._password = os.getenv("FLIBUSTA_PASSWORD", "")
    
    # ===== ПУБЛИЧНЫЕ МЕТОДЫ ДЛЯ ПОЛУЧЕНИЯ URL =====
    
    def get_book_url(self, book_id: int) -> str:
        """Получить URL страницы книги"""
        return f"{self.base_url}/b/{book_id}" if book_id else ""
    
    def get_download_url(self, book_id: int, book_format: str) -> str:
        """Получить URL для скачивания книги"""
        return f"{self.base_url}/b/{book_id}/{book_format}" if book_id and book_format else ""
    
    def get_author_url(self, author_id: int) -> str:
        """Получить URL страницы автора"""
        return f"{self.base_url}/a/{author_id}" if author_id else ""
    
    def get_series_url(self, series_id: int) -> str:
        """Получить URL страницы серии"""
        return f"{self.base_url}/s/{series_id}" if series_id else ""
    
    def get_genre_url(self, genre_id: int) -> str:
        """Получить URL страницы жанра"""
        return f"{self.base_url}/g/{genre_id}" if genre_id else ""
    
    def get_cover_url(self, local_cover_url: str) -> Optional[str]:
        """Получить полный URL обложки книги"""
        return f"{self.base_url}/ib/{local_cover_url}" if local_cover_url else None
    
    def get_author_photo_url(self, local_photo_url: str) -> Optional[str]:
        """Получить полный URL фотографии автора"""
        return f"{self.base_url}/ia/{local_photo_url}" if local_photo_url else None
    
    # ===== УПРАВЛЕНИЕ СЕССИЯМИ =====
    
    async def _create_session(self) -> aiohttp.ClientSession:
        """Создать новую сессию"""
        timeout = aiohttp.ClientTimeout(total=60)
        return aiohttp.ClientSession(
            timeout=timeout,
            headers={
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            }
        )
    
    async def _get_session(self, auth: bool = False) -> aiohttp.ClientSession:
        """
        Получить сессию (с авторизацией или без)
        
        Args:
            auth: True - вернуть авторизованную сессию, False - обычную
            
        Returns:
            Сессия aiohttp
        """
        if not auth:
            if self._session is None:
                self._session = await self._create_session()
            return self._session
        else:
            if self._auth_session is None or not self._is_logged_in:
                await self.login()
            return self._auth_session
    
    async def login(self) -> bool:
        """
        Авторизация на сайте Flibusta
        
        Returns:
            True - успешная авторизация, False - ошибка
        """
        try:
            if not self._username or not self._password:
                self.logger.log_system(
                    EventType.SYSTEM_ERROR,
                    "Flibusta credentials not configured",
                    {"error": "Missing FLIBUSTA_USERNAME or FLIBUSTA_PASSWORD"}
                )
                return False
            
            # Создаем новую сессию для авторизации
            if self._auth_session is None:
                self._auth_session = await self._create_session()
            
            # Получаем страницу входа
            login_url = f"{self.base_url}/user/login"
            async with self._auth_session.get(login_url) as response:
                html = await response.text()
            
            # Извлекаем form_build_id
            form_build_id = None
            if 'form_build_id' in html:
                start = html.find('form_build_id') + len('form_build_id')
                start = html.find('value="', start) + len('value="')
                end = html.find('"', start)
                form_build_id = html[start:end]
            
            # Формируем данные для входа
            form_data = {
                'name': self._username,
                'pass': self._password,
                'form_id': 'user_login',
                'op': 'Вход в систему',
                'persistent_login': '1'
            }
            if form_build_id:
                form_data['form_build_id'] = form_build_id
            
            # Отправляем форму
            async with self._auth_session.post(login_url, data=form_data) as response:
                result_html = await response.text()
            
            # Проверяем успешность авторизации
            self._is_logged_in = ('Выйти' in result_html) or (self._username in result_html)
            
            if self._is_logged_in:
                self.logger.log_system(
                    EventType.SYSTEM_INFO,
                    "Flibusta login successful",
                    {"username": self._username}
                )
            else:
                self.logger.log_system(
                    EventType.SYSTEM_ERROR,
                    "Flibusta login failed",
                    {"username": self._username}
                )
            
            return self._is_logged_in
            
        except Exception as e:
            self.logger.log_error(
                "flibusta_login_error",
                str(e),
                {"username": self._username}
            )
            return False
    
    async def logout(self) -> None:
        """Выход из системы и закрытие сессий"""
        if self._auth_session:
            await self._auth_session.close()
            self._auth_session = None
        self._is_logged_in = False
        
        self.logger.log_system(
            EventType.SYSTEM_INFO,
            "Flibusta logout",
            {}
        )
    
    async def close(self) -> None:
        """Закрыть все сессии"""
        if self._session:
            await self._session.close()
            self._session = None
        
        if self._auth_session:
            await self._auth_session.close()
            self._auth_session = None
        
        self._is_logged_in = False
    
    # ===== ОСНОВНЫЕ ОПЕРАЦИИ =====
    
    async def download_book(
        self,
        book_id: int,
        book_format: str,
        auth: bool = False
    ) -> Tuple[Optional[bytes], Optional[str]]:
        """
        Скачать книгу
        
        Args:
            book_id: ID книги
            book_format: Формат (fb2, epub, mobi)
            auth: Использовать авторизованную сессию
            
        Returns:
            Кортеж (данные книги, имя файла) или (None, None) при ошибке
        """
        try:
            session = await self._get_session(auth=auth)
            download_url = self.get_download_url(book_id, book_format)
            
            if not download_url:
                return None, None
            
            # Скачиваем книгу
            async with session.get(download_url) as response:
                if response.status != 200:
                    self.logger.log_error(
                        "download_book_failed",
                        f"HTTP {response.status}",
                        {"book_id": book_id, "format": book_format, "auth": auth}
                    )
                    return None, None
                
                # Проверяем, что это не HTML страница с ошибкой
                content_type = response.headers.get('Content-Type', '')
                if 'html' in content_type:
                    html = await response.text()
                    if 'Страница не найдена' in html:
                        return None, None
                
                # Читаем данные
                book_data = await response.read()
                
                # Извлекаем имя файла
                filename = None
                cd = response.headers.get('Content-Disposition')
                if cd:
                    match = re.search(
                        r'filename[^;=\n]*=([\'"]?)([^\'"\n]+)\1',
                        cd,
                        re.IGNORECASE
                    )
                    if match:
                        filename = unquote(match.group(2))
                
                self.logger.log_system(
                    EventType.DOWNLOAD_SUCCESS,
                    "Book downloaded",
                    {
                        "book_id": book_id,
                        "format": book_format,
                        "size": len(book_data),
                        "auth": auth
                    }
                )
                
                return book_data, filename
                
        except Exception as e:
            self.logger.log_error(
                "download_book_error",
                str(e),
                {"book_id": book_id, "format": book_format, "auth": auth}
            )
            return None, None
    
    async def get_book_cover_url(self, book_id: int) -> Optional[str]:
        """
        Получить URL обложки книги
        
        Args:
            book_id: ID книги
            
        Returns:
            URL обложки или None
        """
        try:
            # Сначала пробуем без авторизации
            cover_url = await self._extract_cover_from_page(book_id, auth=False)
            if cover_url:
                return cover_url
            
            # Пробуем с авторизацией
            cover_url = await self._extract_cover_from_page(book_id, auth=True)
            return cover_url
            
        except Exception as e:
            self.logger.log_error(
                "get_cover_error",
                str(e),
                {"book_id": book_id}
            )
            return None
    
    async def _extract_cover_from_page(
        self,
        book_id: int,
        auth: bool = False
    ) -> Optional[str]:
        """
        Извлечь URL обложки со страницы книги
        
        Args:
            book_id: ID книги
            auth: Использовать авторизованную сессию
            
        Returns:
            URL обложки или None
        """
        try:
            session = await self._get_session(auth=auth)
            book_url = self.get_book_url(book_id)
            
            async with session.get(book_url) as response:
                if response.status != 200:
                    return None
                
                html = await response.text()
                soup = BeautifulSoup(html, 'html.parser')
                
                # Ищем обложку
                cover_img = soup.find('img', {'title': 'Cover image'})
                if not cover_img:
                    cover_img = soup.find('img', {'alt': 'Cover image'})
                
                if cover_img and cover_img.get('src'):
                    cover_url = cover_img['src']
                    if not cover_url.startswith('http'):
                        cover_url = f"{self.base_url}{cover_url}"
                    return cover_url
                
                return None
                
        except Exception as e:
            self.logger.log_error(
                "extract_cover_error",
                str(e),
                {"book_id": book_id, "auth": auth}
            )
            return None
    
    # ===== КОНТЕКСТНЫЙ МЕНЕДЖЕР =====
    
    async def __aenter__(self):
        """Поддержка async context manager"""
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Автоматическое закрытие сессий"""
        await self.close()


# Глобальный экземпляр для обратной совместимости
flibusta_service = FlibustaService()