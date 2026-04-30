"""
Обработчики поиска (новая архитектура)
"""
import asyncio
from time import time
from typing import List, Optional

from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import CallbackContext
from telegram.constants import ParseMode
from telegram.error import Forbidden

from ..services.search_service import SearchService, SearchParams
from ..services.book_service import BookService
from ..services.user_service import UserService
from ..core.structured_logger import StructuredLogger
from ..core.logging_schema import EventType
from ..core.custom_types import (
    BookInfo, SeriesResult, AuthorResult, UserSettings,
    SearchType, SearchArea
)
from ..core import HEADING_POP


class SearchHandlers:
    """
    Обработчики для поиска и навигации
    
    Команды:
    - Текстовый поиск (книги, серии, авторы)
    - Пагинация результатов
    - Популярные книги и новинки
    - Навигация по сериям и авторам
    """
    
    def __init__(
        self,
        search_service: SearchService,
        book_service: BookService,
        user_service: UserService,
        logger: StructuredLogger
    ):
        self.search_service = search_service
        self.book_service = book_service
        self.user_service = user_service
        self.logger = logger
    
    async def handle_message(self, update: Update, context: CallbackContext) -> None:
        """Обработка текстовых сообщений (поиск)"""
        try:
            user = update.effective_user
            query_text = update.message.text.strip()
            
            # Проверка блокировки
            if self.user_service.is_user_blocked(user.id):
                return
            
            # Получаем настройки
            settings = self.user_service.get_user_settings(user.id)
            
            # Определяем тип поиска
            search_type = SearchType(settings.search_type)
            
            # Отправляем сообщение о обработке
            processing_msg = await update.message.reply_text(
                f"⏰ <i>Ищу {self._get_search_type_text(search_type)}, ожидайте...</i>",
                parse_mode=ParseMode.HTML,
                disable_notification=True
            )
            
            # Запускаем асинхронный поиск
            asyncio.create_task(
                self._async_search(context, query_text, processing_msg, user, settings, search_type)
            )
            
        except Forbidden as e:
            if "bot was blocked by the user" in str(e):
                self.logger.log_user_action(
                    EventType.USER_BLOCKED_BOT,
                    user.id,
                    user.username or "Unknown",
                    {}
                )
                return
            raise e
        except Exception as e:
            await update.message.reply_text("❌ Произошла ошибка при обработке запроса")
            self.logger.log_error(
                error_type="search_message_error",
                error_message=str(e),
                context={"query": query_text},
                user_id=user.id,
                username=user.username
            )
    
    async def _async_search(
        self,
        context: CallbackContext,
        query_text: str,
        processing_msg,
        user,
        settings: UserSettings,
        search_type: SearchType
    ) -> None:
        """Асинхронная задача поиска"""
        try:
            start_time = time()
            
            # Создаем параметры поиска
            params = SearchParams(
                query=query_text,
                settings=settings
            )
            
            # Выполняем поиск в зависимости от типа
            if search_type == SearchType.BOOKS:
                result = await self.search_service.search_books(params)
                await self._process_book_results(context, result, processing_msg, query_text, user, settings)
                
            elif search_type == SearchType.SERIES:
                series_list = await self.search_service.search_series(params)
                await self._process_series_results(context, series_list, processing_msg, query_text, user, settings)
                
            elif search_type == SearchType.AUTHORS:
                authors_list = await self.search_service.search_authors(params)
                await self._process_author_results(context, authors_list, processing_msg, query_text, user, settings)
            
            # Логируем поиск
            duration_ms = int((time() - start_time) * 1000)
            # Получаем реальное количество результатов
            result_count = 0
            if 'result' in locals():
                result_count = result.get('total_count', 0)
            elif 'series_list' in locals():
                result_count = len(series_list)
            elif 'authors_list' in locals():
                result_count = len(authors_list)
            
            self.logger.log_search(
                user_id=user.id,
                username=user.username or user.first_name or "Unknown",
                query=query_text,
                search_type=search_type.value,
                search_area=settings.search_area,
                results_count=result_count,
                duration_ms=duration_ms,
                chat_type="private",
                chat_id=user.id,
                lang=settings.lang,
                rating_filter=settings.rating,
                size_limit=settings.book_size
            )
            
        except Exception as e:
            await processing_msg.edit_text(f"❌ Ошибка при поиске: {str(e)}")
            self.logger.log_error(
                "async_search_error",
                str(e),
                {"query": query_text, "search_type": search_type.value},
                user.id,
                user.username
            )
    
    async def _process_book_results(
        self,
        context: CallbackContext,
        result: dict,
        processing_msg,
        query_text: str,
        user,
        settings: UserSettings
    ) -> None:
        """Обработка и отображение результатов поиска книг"""
        books = result.get('books', [])
        pages = result.get('pages', [])
        
        if not books:
            await processing_msg.edit_text(
                "😞 Не нашёл подходящих книг. Попробуйте другие критерии поиска.",
                parse_mode=ParseMode.HTML
            )
            return
        
        # Сохраняем в контекст
        context.user_data['pages_of_books'] = pages
        context.user_data['found_books_count'] = len(books)
        context.user_data['last_search_query'] = query_text
        
        # Показываем первую страницу
        page = 0
        keyboard = self._create_books_keyboard(page, pages, SearchType.BOOKS)
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        header_text = self._format_book_header(page, len(books), settings, query_text)
        
        await processing_msg.edit_text(header_text, reply_markup=reply_markup)
    
    async def _process_series_results(
        self,
        context: CallbackContext,
        series_list: List[SeriesResult],
        processing_msg,
        query_text: str,
        user,
        settings: UserSettings
    ) -> None:
        """Обработка результатов поиска серий"""
        if not series_list:
            await processing_msg.edit_text(
                "😞 Не нашёл подходящих книжных серий. Попробуйте другие критерии поиска.",
                parse_mode=ParseMode.HTML
            )
            return
        
        # Разбиваем на страницы
        pages = self._paginate(series_list, settings.max_books)
        
        # Сохраняем в контекст
        context.user_data['pages_of_series'] = pages
        context.user_data['found_series_count'] = len(series_list)
        context.user_data['last_search_query'] = query_text
        
        # Показываем первую страницу
        page = 0
        keyboard = self._create_series_keyboard(page, pages)
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        header_text = self._format_series_header(page, len(series_list), settings, query_text)
        
        await processing_msg.edit_text(header_text, reply_markup=reply_markup)
    
    async def _process_author_results(
        self,
        context: CallbackContext,
        authors_list: List[AuthorResult],
        processing_msg,
        query_text: str,
        user,
        settings: UserSettings
    ) -> None:
        """Обработка результатов поиска авторов"""
        if not authors_list:
            await processing_msg.edit_text(
                "😞 Не нашёл подходящих авторов. Попробуйте другие критерии поиска.",
                parse_mode=ParseMode.HTML
            )
            return
        
        # Разбиваем на страницы
        pages = self._paginate(authors_list, settings.max_books)
        
        # Сохраняем в контекст
        context.user_data['pages_of_authors'] = pages
        context.user_data['found_authors_count'] = len(authors_list)
        context.user_data['last_search_query'] = query_text
        
        # Показываем первую страницу
        page = 0
        keyboard = self._create_authors_keyboard(page, pages)
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        header_text = self._format_author_header(page, len(authors_list), settings, query_text)
        
        await processing_msg.edit_text(header_text, reply_markup=reply_markup)
    
    async def handle_callback(self, update: Update, context: CallbackContext) -> None:
        """Обработка callback'ов (пагинация, навигация)"""
        query = update.callback_query
        user = query.from_user
        
        # Проверка блокировки
        if self.user_service.is_user_blocked(user.id):
            await query.answer("❌ Вы заблокированы")
            return
        
        data = query.data
        
        try:
            # Обработка пагинации книг
            if data.startswith("books_page_"):
                page = int(data.split("_")[2])
                await self._handle_book_page_change(query, context, page)
            
            # Обработка пагинации серий
            elif data.startswith("series_page_"):
                page = int(data.split("_")[2])
                await self._handle_series_page_change(query, context, page)
            
            # Обработка пагинации авторов
            elif data.startswith("authors_page_"):
                page = int(data.split("_")[2])
                await self._handle_author_page_change(query, context, page)
            
            # Показ книг серии
            elif data.startswith("show_series:"):
                series_id = int(data.split(":")[1])
                await self._handle_show_series(query, context, series_id)
            
            # Показ книг автора
            elif data.startswith("show_author:"):
                author_id = int(data.split(":")[1])
                await self._handle_show_author(query, context, author_id)
            
            # Популярное/новинки (поддержка старого формата из старой архитектуры)
            elif data.startswith("show_pop_"):
                days_str = data.removeprefix("show_pop_")
                days_map = {
                    "999": 999,  # за всё время
                    "30": 30,    # за 30 дней
                    "7": 7,      # за 7 дней
                    "0": 0       # новинки
                }
                days = days_map.get(days_str, 0)
                await self._handle_popular(query, context, days)
            
            # Популярное/новинки (новый формат)
            elif data.startswith("pop:"):
                days = int(data.split(":")[1])
                await self._handle_popular(query, context, days)
            
            # Назад к сериям
            elif data == "back_to_series":
                await self._handle_back_to_series(query, context)
            
            # Назад к авторам
            elif data == "back_to_authors":
                await self._handle_back_to_authors(query, context)
            
            else:
                await query.answer("Неизвестная команда")
                
        except Exception as e:
            await query.answer("❌ Ошибка")
            self.logger.log_error(
                "callback_error",
                str(e),
                {"data": data},
                user.id,
                user.username
            )
    
    async def _handle_book_page_change(self, query, context: CallbackContext, page: int) -> None:
        """Обработка смены страницы книг"""
        pages_of_books = context.user_data.get('pages_of_books')
        if not pages_of_books:
            await query.edit_message_text("❌ Сессия поиска истекла. Начните поиск заново.")
            return
        
        if page < 0 or page >= len(pages_of_books):
            await query.answer("❌ Неверный номер страницы")
            return
        
        settings = self.user_service.get_user_settings(query.from_user.id)
        keyboard = self._create_books_keyboard(page, pages_of_books, SearchType.BOOKS)
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        found_count = context.user_data.get('found_books_count', 0)
        query_text = context.user_data.get('last_search_query', '')
        show_pop = context.user_data.get('show_pop')
        header_text = self._format_book_header(page, found_count, settings, query_text, show_pop=show_pop)
        
        await query.edit_message_text(header_text, reply_markup=reply_markup)
        await query.answer()
    
    async def _handle_series_page_change(self, query, context: CallbackContext, page: int) -> None:
        """Обработка смены страницы серий"""
        pages_of_series = context.user_data.get('pages_of_series')
        if not pages_of_series:
            await query.edit_message_text("❌ Результаты поиска устарели. Выполните новый поиск.")
            return
        
        if page < 0 or page >= len(pages_of_series):
            await query.answer("❌ Неверный номер страницы")
            return
        
        settings = self.user_service.get_user_settings(query.from_user.id)
        keyboard = self._create_series_keyboard(page, pages_of_series)
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        found_count = context.user_data.get('found_series_count', 0)
        query_text = context.user_data.get('last_search_query', '')
        header_text = self._format_series_header(page, found_count, settings, query_text)
        
        await query.edit_message_text(header_text, reply_markup=reply_markup)
        await query.answer()
    
    async def _handle_author_page_change(self, query, context: CallbackContext, page: int) -> None:
        """Обработка смены страницы авторов"""
        pages_of_authors = context.user_data.get('pages_of_authors')
        if not pages_of_authors:
            await query.edit_message_text("❌ Результаты поиска устарели. Выполните новый поиск.")
            return
        
        if page < 0 or page >= len(pages_of_authors):
            await query.answer("❌ Неверный номер страницы")
            return
        
        settings = self.user_service.get_user_settings(query.from_user.id)
        keyboard = self._create_authors_keyboard(page, pages_of_authors)
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        found_count = context.user_data.get('found_authors_count', 0)
        query_text = context.user_data.get('last_search_query', '')
        header_text = self._format_author_header(page, found_count, settings, query_text)
        
        await query.edit_message_text(header_text, reply_markup=reply_markup)
        await query.answer()
    
    async def _handle_show_series(self, query, context: CallbackContext, series_id: int) -> None:
        """Показ книг выбранной серии"""
        user = query.from_user
        settings = self.user_service.get_user_settings(user.id)
        query_text = context.user_data.get('last_search_query', '')
        
        # Создаем параметры поиска с фильтром по серии
        params = SearchParams(
            query=query_text,
            settings=settings,
            series_id=series_id
        )
        
        # Ищем книги
        result = await self.search_service.search_books(params)
        books = result.get('books', [])
        pages = result.get('pages', [])
        
        if not books:
            await query.edit_message_text("😞 Не найдено книг в этой серии")
            return
        
        # Сохраняем в контекст
        context.user_data['pages_of_books'] = pages
        context.user_data['found_books_count'] = len(books)
        context.user_data['current_series_id'] = series_id
        context.user_data['current_series_name'] = books[0].series_title if books else None
        
        # Показываем первую страницу
        page = 0
        keyboard = self._create_books_keyboard(page, pages, SearchType.SERIES)
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        header_text = self._format_book_header(
            page, len(books), settings, query_text,
            series_name=context.user_data['current_series_name']
        )
        
        await query.edit_message_text(header_text, reply_markup=reply_markup)
        await query.answer()
    
    async def _handle_show_author(self, query, context: CallbackContext, author_id: int) -> None:
        """Показ книг выбранного автора"""
        user = query.from_user
        settings = self.user_service.get_user_settings(user.id)
        query_text = context.user_data.get('last_search_query', '')
        
        # Создаем параметры поиска с фильтром по автору
        params = SearchParams(
            query=query_text,
            settings=settings,
            author_id=author_id
        )
        
        # Ищем книги
        result = await self.search_service.search_books(params)
        books = result.get('books', [])
        pages = result.get('pages', [])
        
        if not books:
            await query.edit_message_text("😞 Не найдено книг этого автора")
            return
        
        # Сохраняем в контекст
        context.user_data['pages_of_books'] = pages
        context.user_data['found_books_count'] = len(books)
        context.user_data['current_author_id'] = author_id
        context.user_data['current_author_name'] = self._format_author_name(books[0]) if books else None
        
        # Показываем первую страницу
        page = 0
        keyboard = self._create_books_keyboard(page, pages, SearchType.AUTHORS)
        keyboard.append([InlineKeyboardButton("👤 Об авторе", callback_data=f"author_info:{author_id}")])
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        header_text = self._format_book_header(
            page, len(books), settings, query_text,
            author_name=context.user_data['current_author_name']
        )
        
        await query.edit_message_text(header_text, reply_markup=reply_markup)
        await query.answer()
    
    async def _handle_popular(self, query, context: CallbackContext, days: int) -> None:
        """Обработка запроса популярных книг"""
        try:
            user = query.from_user
            settings = self.user_service.get_user_settings(user.id)
            
            # Получаем популярные книги
            result = await self.search_service.get_popular_books(settings, days)
            books = result.get('books', [])
            pages = result.get('pages', [])
            
            if not books:
                await query.edit_message_text("😞 Не найдено популярных книг за этот период")
                return
            
            # Сохраняем в контекст
            context.user_data['pages_of_books'] = pages
            context.user_data['found_books_count'] = len(books)
            
            # Сохраняем тип популярного (обратное преобразование дней в show_pop_xxx)
            days_to_show_pop = {
                999: "show_pop_999",
                30: "show_pop_30",
                7: "show_pop_7",
                0: "show_pop_0"
            }
            context.user_data['show_pop'] = days_to_show_pop.get(days, "show_pop_0")
            
            # Показываем первую страницу
            page = 0
            keyboard = self._create_books_keyboard(page, pages, SearchType.BOOKS)
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            header_text = self._format_book_header(
                page, len(books), settings, '',
                show_pop=days_to_show_pop.get(days, "show_pop_0")
            )
            
            await query.edit_message_text(header_text, reply_markup=reply_markup)
            await query.answer()
            
            self.logger.log_user_action(
                EventType.SEARCH_POPULAR, user.id, user.username,
                {"days": days, "count": len(books)}
            )
            
        except Exception as e:
            await query.answer("❌ Ошибка")
            self.logger.log_error(
                "popular_error",
                str(e),
                {"days": days},
                query.from_user.id,
                query.from_user.username
            )
    
    async def _handle_back_to_series(self, query, context: CallbackContext) -> None:
        """Возврат к списку серий"""
        pages_of_series = context.user_data.get('pages_of_series')
        if not pages_of_series:
            await query.edit_message_text("❌ Результаты поиска устарели")
            return
        
        page = context.user_data.get('last_series_page', 0)
        settings = self.user_service.get_user_settings(query.from_user.id)
        
        keyboard = self._create_series_keyboard(page, pages_of_series)
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        found_count = context.user_data.get('found_series_count', 0)
        query_text = context.user_data.get('last_search_query', '')
        header_text = self._format_series_header(page, found_count, settings, query_text)
        
        await query.edit_message_text(header_text, reply_markup=reply_markup)
        await query.answer()
    
    async def _handle_back_to_authors(self, query, context: CallbackContext) -> None:
        """Возврат к списку авторов"""
        pages_of_authors = context.user_data.get('pages_of_authors')
        if not pages_of_authors:
            await query.edit_message_text("❌ Результаты поиска устарели")
            return
        
        page = context.user_data.get('last_authors_page', 0)
        settings = self.user_service.get_user_settings(query.from_user.id)
        
        keyboard = self._create_authors_keyboard(page, pages_of_authors)
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        found_count = context.user_data.get('found_authors_count', 0)
        query_text = context.user_data.get('last_search_query', '')
        header_text = self._format_author_header(page, found_count, settings, query_text)
        
        await query.edit_message_text(header_text, reply_markup=reply_markup)
        await query.answer()
    
    # ===== УТИЛИТЫ ДЛЯ СОЗДАНИЯ КЛАВИАТУР =====
    
    def _create_books_keyboard(
        self,
        page: int,
        pages: List[List],
        search_context: SearchType
    ) -> List[List[InlineKeyboardButton]]:
        """Создание клавиатуры с книгами"""
        keyboard = []
        
        if not pages or page >= len(pages):
            return keyboard
        
        books_in_page = pages[page]
        
        for book in books_in_page:
            # Форматируем текст кнопки
            rating_emoji = self._get_rating_emoji(book.lib_rate)
            author_name = self._format_author_name(book)
            size_text = self._format_size(book.book_size)
            
            text = f"{rating_emoji} {book.title} ({author_name}) {size_text}"
            if hasattr(book, 'genre') and book.genre:
                text += f"/{book.genre}"
            if hasattr(book, 'search_year') and book.search_year:
                text += f"/{book.search_year}"
            
            keyboard.append([
                InlineKeyboardButton(text, callback_data=f"book_info:{book.file_name}")
            ])
        
        # Добавляем навигацию
        self._add_navigation_buttons(keyboard, "books", page, pages)
        
        # Добавляем кнопки возврата
        if search_context == SearchType.SERIES:
            keyboard.append([InlineKeyboardButton("⤴️ Назад к сериям", callback_data="back_to_series")])
        elif search_context == SearchType.AUTHORS:
            keyboard.append([InlineKeyboardButton("⤴️ Назад к авторам", callback_data="back_to_authors")])
        
        return keyboard
    
    def _create_series_keyboard(
        self,
        page: int,
        pages: List[List[SeriesResult]]
    ) -> List[List[InlineKeyboardButton]]:
        """Создание клавиатуры с сериями"""
        keyboard = []
        
        if not pages or page >= len(pages):
            return keyboard
        
        series_in_page = pages[page]
        
        for series in series_in_page:
            text = f"{series.series_title} ({series.book_count})"
            keyboard.append([
                InlineKeyboardButton(text, callback_data=f"show_series:{series.series_id}")
            ])
        
        # Добавляем навигацию
        self._add_navigation_buttons(keyboard, "series", page, pages)
        
        return keyboard
    
    def _create_authors_keyboard(
        self,
        page: int,
        pages: List[List[AuthorResult]]
    ) -> List[List[InlineKeyboardButton]]:
        """Создание клавиатуры с авторами"""
        keyboard = []
        
        if not pages or page >= len(pages):
            return keyboard
        
        authors_in_page = pages[page]
        
        for author in authors_in_page:
            text = f"{author.author_name} ({author.book_count})"
            keyboard.append([
                InlineKeyboardButton(text, callback_data=f"show_author:{author.author_id}")
            ])
        
        # Добавляем навигацию
        self._add_navigation_buttons(keyboard, "authors", page, pages)
        
        return keyboard
    
    def _add_navigation_buttons(
        self,
        keyboard: List[List],
        prefix: str,
        page: int,
        pages: List
    ) -> None:
        """Добавляет кнопки навигации"""
        navigation_buttons = []
        
        if page > 0:
            navigation_buttons.append(
                InlineKeyboardButton("⬆ В начало", callback_data=f"{prefix}_page_0")
            )
            navigation_buttons.append(
                InlineKeyboardButton("⬅️ Назад", callback_data=f"{prefix}_page_{page - 1}")
            )
        
        if page < len(pages) - 1:
            navigation_buttons.append(
                InlineKeyboardButton("Вперёд ➡️", callback_data=f"{prefix}_page_{page + 1}")
            )
            navigation_buttons.append(
                InlineKeyboardButton("В конец ⬇️", callback_data=f"{prefix}_page_{len(pages) - 1}")
            )
        
        if navigation_buttons:
            keyboard.append(navigation_buttons)
    
    # ===== УТИЛИТЫ ДЛЯ ФОРМАТИРОВАНИЯ =====
    
    def _format_book_header(
        self,
        page: int,
        total_count: int,
        settings: UserSettings,
        query: str = "",
        series_name: Optional[str] = None,
        author_name: Optional[str] = None,
        show_pop: Optional[str] = None
    ) -> str:
        """Форматирует заголовок для книг"""
        start = settings.max_books * page + 1
        end = min(settings.max_books * (page + 1), total_count)
        
        if show_pop:
            text = HEADING_POP.get(show_pop, 'популярных')
            header = f"Показываю с {start} по {end} из {total_count} найденных {text}"
        else:
            header = f"Показываю с {start} по {end} из {total_count} найденных книг"
        
        if series_name:
            header += f" в серии '{series_name}'"
        if author_name:
            header += f" автора '{author_name}'"
        
        search_area_text = {
            "b": "",
            "ba": " по аннотации книги",
            "aa": " по аннотации автора"
        }
        header += search_area_text.get(settings.search_area, "")
        
        if query and not show_pop:
            header += f"\n🔍 Запрос: {query}"
        
        return header
    
    def _format_series_header(
        self,
        page: int,
        total_count: int,
        settings: UserSettings,
        query: str = ""
    ) -> str:
        """Форматирует заголовок для серий"""
        start = settings.max_books * page + 1
        end = min(settings.max_books * (page + 1), total_count)
        
        header = f"📚 Показываю с {start} по {end} из {total_count} найденных серий"
        
        search_area_text = {
            "b": " по основным данным",
            "ba": " по аннотациям книг",
            "aa": " по аннотациям авторов"
        }
        header += search_area_text.get(settings.search_area, "")
        
        if query:
            header += f"\n🔍 Запрос: {query}"
        
        return header
    
    def _format_author_header(
        self,
        page: int,
        total_count: int,
        settings: UserSettings,
        query: str = ""
    ) -> str:
        """Форматирует заголовок для авторов"""
        start = settings.max_books * page + 1
        end = min(settings.max_books * (page + 1), total_count)
        
        header = f"👤 Показываю с {start} по {end} из {total_count} найденных авторов"
        
        search_area_text = {
            "b": " по основным данным",
            "ba": " по аннотациям книг",
            "aa": " по аннотациям авторов"
        }
        header += search_area_text.get(settings.search_area, "")
        
        if query:
            header += f"\n🔍 Запрос: {query}"
        
        return header
    
    def _format_author_name(self, book: BookInfo) -> str:
        """Форматирует имя автора"""
        parts = []
        if book.last_name:
            parts.append(book.last_name)
        if book.first_name:
            parts.append(book.first_name)
        return " ".join(parts) if parts else "Неизвестный автор"
    
    def _format_size(self, size_bytes: int) -> str:
        """Форматирует размер файла"""
        units = ["B", "K", "M", "G"]
        size = float(size_bytes)
        unit_index = 0
        
        while size >= 1024 and unit_index < len(units) - 1:
            size /= 1024
            unit_index += 1
        
        return f"{size:.1f}{units[unit_index]}"
    
    def _get_rating_emoji(self, rating: float) -> str:
        """Возвращает эмодзи для рейтинга"""
        rating_map = {
            0: "⚪️",
            1: "🔴",
            2: "🟠",
            3: "🟡",
            4: "🟢",
            5: "🔵"
        }
        return rating_map.get(int(rating), "⚪️")
    
    def _get_search_type_text(self, search_type: SearchType) -> str:
        """Возвращает текст для типа поиска"""
        texts = {
            SearchType.BOOKS: "книги",
            SearchType.SERIES: "серии",
            SearchType.AUTHORS: "авторов"
        }
        return texts.get(search_type, "книги")
    
    def _paginate(self, items: List, page_size: int) -> List[List]:
        """Разбивает список на страницы"""
        if not items:
            return []
        return [items[i:i + page_size] for i in range(0, len(items), page_size)]