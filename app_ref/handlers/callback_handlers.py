"""
Обработчики callback'ов (новая архитектура)
"""
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import CallbackContext
from telegram.constants import ParseMode
from telegram.error import BadRequest

from ..services.search_service import SearchService
from ..services.book_service import BookService
from ..services.user_service import UserService
from ..handlers.settings_handlers import SettingsHandlers
from ..core.structured_logger import StructuredLogger
from ..core.logging_schema import EventType
from ..utils.formatter import (
    format_book_info,
    format_book_details,
    format_author_info,
    format_book_reviews
)


class CallbackHandlers:
    """
    Обработчики inline callback'ов
    
    Обрабатывает:
    - Информация о книгах и авторах
    - Скачивание книг
    - Настройки пользователя
    - Пагинация и навигация
    - Закрытие сообщений
    """
    
    def __init__(
        self,
        search_service: SearchService,
        book_service: BookService,
        user_service: UserService,
        settings_handlers: SettingsHandlers,
        logger: StructuredLogger
    ):
        self.search_service = search_service
        self.book_service = book_service
        self.user_service = user_service
        self.settings_handlers = settings_handlers
        self.logger = logger
    
    async def handle_callback(self, update: Update, context: CallbackContext) -> None:
        """Основной обработчик callback'ов"""
        query = update.callback_query
        user = query.from_user
        
        try:
            await query.answer()
        except BadRequest as e:
            if "Query is too old" in str(e):
                return
            raise e
        
        # Проверка блокировки
        if self.user_service.is_user_blocked(user.id):
            await query.answer("❌ Вы заблокированы", show_alert=True)
            return
        
        data = query.data
        
        try:
            # Определяем тип callback'а и перенаправляем
            if data.startswith("book_info:"):
                book_id = int(data.split(":")[1])
                await self._handle_book_info(query, context, book_id)
            
            elif data.startswith("book_details:"):
                book_id = int(data.split(":")[1])
                await self._handle_book_details(query, context, book_id)
            
            elif data.startswith("book_reviews:"):
                book_id = int(data.split(":")[1])
                await self._handle_book_reviews(query, context, book_id)
            
            elif data.startswith("send_file:"):
                book_id = int(data.split(":")[1])
                await self._handle_send_file(query, context, book_id)
            
            elif data.startswith("author_info:"):
                author_id = int(data.split(":")[1])
                await self._handle_author_info(query, context, author_id)
            
            elif data.startswith("close_info"):
                await self._handle_close_info(query, context)
            
            elif data.startswith("close_message"):
                await self._handle_close_message(query, context)
            
            elif data.startswith("back_to_series"):
                await self._handle_back_to_series(query, context)
            
            elif data.startswith("back_to_authors"):
                await self._handle_back_to_authors(query, context)
            
            elif data.startswith("back_to_settings"):
                await self._handle_back_to_settings(query, context)
            
            elif data.startswith("show_series:"):
                series_id = int(data.split(":")[1])
                await self._handle_show_series(query, context, series_id)
            
            elif data.startswith("show_author:"):
                author_id = int(data.split(":")[1])
                await self._handle_show_author(query, context, author_id)
            
            elif data.startswith("show_pop_"):
                # Поддержка старого формата callback'ов из старой архитектуры
                days_str = data.removeprefix("show_pop_")
                days_map = {
                    "999": 999,  # за всё время
                    "30": 30,    # за 30 дней
                    "7": 7,      # за 7 дней
                    "0": 0       # новинки
                }
                days = days_map.get(days_str, 0)
                await self._handle_show_popular(query, context, days)
            
            elif data.startswith("pop:"):
                # Новый формат callback'ов (если используется)
                days = int(data.split(":")[1])
                await self._handle_show_popular(query, context, days)
            
            elif data.startswith("books_page_"):
                page = int(data.split("_")[2])
                await self._handle_books_page(query, context, page)
            
            elif data.startswith("series_page_"):
                page = int(data.split("_")[2])
                await self._handle_series_page(query, context, page)
            
            elif data.startswith("authors_page_"):
                page = int(data.split("_")[2])
                await self._handle_authors_page(query, context, page)
            
            elif data.startswith("settings:") or data.startswith("set_") or \
                 data.startswith("toggle_rating_") or data == "reset_ratings" or \
                 data == "back_to_settings":
                # Перенаправляем все callback'и настроек в SettingsHandlers
                await self.settings_handlers.handle_settings_callback(update, context)
            
            elif data.startswith("show_genres:"):
                genre_index = int(data.split(":")[1])
                await self._handle_show_genres(query, context, genre_index)
            
            else:
                await query.answer("Неизвестная команда")
                
        except Exception as e:
            print(f"[DEBUG CALLBACK] EXCEPTION user={user.id} data='{data}': {type(e).__name__}: {e}")
            import traceback
            traceback.print_exc()

            await query.answer("❌ Ошибка")
            self.logger.log_error(
                "callback_error",
                str(e),
                {"data": data},
                user.id,
                user.username
            )
    
    async def _handle_popular(self, query, user, days: int) -> None:
        """Обработка популярных книг (для совместимости со старым форматом)"""
        # Перенаправляем в новый метод с context
        from telegram.ext import CallbackContext
        context = CallbackContext()
        context.user_data = query.message.chat_data or {}
        await self._handle_show_popular(query, context, days)
    
    

    
    async def _handle_book_info(self, query, context, book_id: int):
        """Обработка информации о книге"""
        try:
            user = query.from_user
            
            # Получаем информацию о книге
            book_info = await self.book_service.get_book_details(book_id)
            
            if not book_info:
                await query.answer("❌ Книга не найдена")
                return
            
            # Форматируем информацию о книге
            text = format_book_info(
                {
                    'bookid': book_id,
                    'title': book_info.title,
                    'authors': book_info.authors or '',
                    'genres': book_info.genres or '',
                    'series': book_info.series,
                    'seqid': book_info.seqid,
                    'year': book_info.year,
                    'lang': book_info.lang,
                    'pages': book_info.pages,
                    'size': book_info.size,
                    'rate': book_info.rate
                },
                self.book_service.flibusta_service
            )
            
            # Создаем клавиатуру
            keyboard = [
                [
                    InlineKeyboardButton("📖 Аннотация", callback_data=f"book_details:{book_id}"),
                    InlineKeyboardButton("💬 Отзывы", callback_data=f"book_reviews:{book_id}")
                ],
                [
                    InlineKeyboardButton("📥 Скачать", callback_data=f"send_file:{book_id}"),
                    InlineKeyboardButton("❌ Закрыть", callback_data="close_info")
                ]
            ]
            
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await query.edit_message_text(
                text,
                reply_markup=reply_markup,
                parse_mode=ParseMode.HTML,
                disable_web_page_preview=False
            )
            await query.answer()
            
            self.logger.log_user_action(
                EventType.BOOK_INFO_VIEW, user.id, user.username,
                {"book_id": book_id, "book_title": book_info.title}
            )
            
        except Exception as e:
            print(f"[DEBUG CALLBACK] _handle_book_info ERROR user={query.from_user.id} book_id={book_id}: {e}")
            await query.answer("❌ Ошибка")
            self.logger.log_error(
                "book_info_error", str(e), {"book_id": book_id},
                query.from_user.id, query.from_user.username
            )
    
    async def _handle_book_details(self, query, context, book_id: int):
        """Обработка аннотации книги"""
        try:
            user = query.from_user
            
            # Получаем детальную информацию
            book_details = await self.book_service.book_repo.get_book_details(book_id)
            
            if not book_details or not book_details.get('annotation'):
                await query.answer("📖 Аннотация отсутствует")
                return
            
            # Форматируем аннотацию
            text = format_book_details(book_details)
            
            keyboard = [[
                InlineKeyboardButton("❌ Закрыть", callback_data="close_info")
            ]]
            
            await query.edit_message_text(
                text,
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode=ParseMode.HTML
            )
            await query.answer()
            
            self.logger.log_user_action(
                EventType.BOOK_DETAILS_VIEW, user.id, user.username,
                {"book_id": book_id}
            )
            
        except Exception as e:
            print(f"[DEBUG CALLBACK] _handle_book_details ERROR user={query.from_user.id} book_id={book_id}: {e}")
            await query.answer("❌ Ошибка")
            self.logger.log_error(
                "book_details_error", str(e), {"book_id": book_id},
                query.from_user.id, query.from_user.username
            )
    
    async def _handle_book_reviews(self, query, context, book_id: int):
        """Обработка отзывов о книге"""
        try:
            user = query.from_user
            
            # Получаем отзывы
            reviews = await self.book_service.book_repo.get_book_reviews(book_id)
            
            if not reviews:
                await query.answer("💬 Отзывы отсутствуют")
                return
            
            # Форматируем отзывы
            text = format_book_reviews(reviews)
            
            keyboard = [[
                InlineKeyboardButton("❌ Закрыть", callback_data="close_info")
            ]]
            
            await query.edit_message_text(
                text,
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode=ParseMode.HTML
            )
            await query.answer()
            
            self.logger.log_user_action(
                EventType.BOOK_REVIEWS_VIEW, user.id, user.username,
                {"book_id": book_id, "reviews_count": len(reviews)}
            )
            
        except Exception as e:
            print(f"[DEBUG CALLBACK] _handle_book_reviews ERROR user={query.from_user.id} book_id={book_id}: {e}")
            await query.answer("❌ Ошибка")
            self.logger.log_error(
                "book_reviews_error", str(e), {"book_id": book_id},
                query.from_user.id, query.from_user.username
            )
    
    async def _handle_send_file(self, query, context, book_id: int):
        """Обработка скачивания книги"""
        try:
            user = query.from_user
            settings = self.user_service.get_user_settings(user.id)
            
            # Уведомление о начале скачивания
            await query.edit_message_text(
                "📥 <b>Скачиваю книгу...</b>\n\nПожалуйста, подождите.",
                parse_mode=ParseMode.HTML
            )
            
            # Скачиваем книгу с fallback стратегией
            book_data, filename, via_tmpfiles = await self.book_service.download_book_with_fallback(
                book_id, settings.book_format
            )
            
            if book_data is None:
                await query.edit_message_text(
                    "❌ <b>Ошибка скачивания</b>\n\nКнига не найдена или недоступна.",
                    parse_mode=ParseMode.HTML
                )
                return
            
            if via_tmpfiles:
                # Файл загружен в облако
                await query.edit_message_text(
                    f"📁 <b>Файл слишком большой для Telegram</b>\n\n"
                    f"Скачайте по ссылке (действительна 15 минут):\n"
                    f"{filename}",
                    parse_mode=ParseMode.HTML
                )
            else:
                # Отправляем файл
                await context.bot.send_document(
                    chat_id=user.id,
                    document=book_data,
                    filename=filename,
                    caption=f"📚 {filename}"
                )
                
                await query.edit_message_text(
                    f"✅ <b>Книга отправлена!</b>\n\n{filename}",
                    parse_mode=ParseMode.HTML
                )
            
            await query.answer()
            
            # Логируем скачивание
            book_info = await self.book_service.get_book_details(book_id)
            self.logger.log_download(
                user.id, user.username,
                book_id, book_info.title if book_info else "Unknown",
                settings.book_format,
                len(book_data) if book_data else 0,
                success=True,
                via_tmpfiles=via_tmpfiles,
                chat_type="private",
                chat_id=user.id
            )
            
        except Exception as e:
            print(f"[DEBUG CALLBACK] _handle_send_file ERROR user={query.from_user.id} book_id={book_id}: {e}")
            await query.answer("❌ Ошибка скачивания")
            self.logger.log_error(
                "send_file_error", str(e), {"book_id": book_id},
                query.from_user.id, query.from_user.username
            )
    
    async def _handle_author_info(self, query, context, author_id: int):
        """Обработка информации об авторе"""
        try:
            user = query.from_user
            
            # Получаем информацию об авторе
            author_info = await self.book_service.get_author_details(author_id)
            
            if not author_info:
                await query.answer("❌ Автор не найден")
                return
            
            # Форматируем информацию об авторе
            text = format_author_info(
                {
                    'author_id': author_id,
                    'name': f"{author_info.last_name} {author_info.first_name} {author_info.middle_name}".strip(),
                    'biography': author_info.biography
                },
                self.book_service.flibusta_service
            )
            
            keyboard = [[
                InlineKeyboardButton("❌ Закрыть", callback_data="close_info")
            ]]
            
            await query.edit_message_text(
                text,
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode=ParseMode.HTML
            )
            await query.answer()
            
            self.logger.log_user_action(
                EventType.AUTHOR_INFO_VIEW, user.id, user.username,
                {"author_id": author_id}
            )
            
        except Exception as e:
            print(f"[DEBUG CALLBACK] _handle_author_info ERROR user={query.from_user.id} author_id={author_id}: {e}")
            await query.answer("❌ Ошибка")
            self.logger.log_error(
                "author_info_error", str(e), {"author_id": author_id},
                query.from_user.id, query.from_user.username
            )
    
    async def _handle_close_info(self, query, context):
        """Закрытие информационного сообщения"""
        try:
            await query.edit_message_text(
                "❌ <b>Информация закрыта</b>",
                parse_mode=ParseMode.HTML
            )
            await query.answer()
            
        except Exception as e:
            # Если сообщение уже удалено или нет прав
            await query.answer("✅ Закрыто")
    
    async def _handle_close_message(self, query, context):
        """Удаление сообщения"""
        try:
            await query.message.delete()
            await query.answer()
            
        except Exception as e:
            await query.answer("❌ Не удалось удалить сообщение")
    
    # ===== РЕАЛИЗАЦИЯ ОТСУТСТВУЮЩИХ МЕТОДОВ =====
    
    async def _handle_back_to_series(self, query, context):
        """Возврат к списку серий"""
        await query.answer("⤴️ Возврат к сериям (в разработке)")
        # TODO: Реализовать восстановление контекста серий
    
    async def _handle_back_to_authors(self, query, context):
        """Возврат к списку авторов"""
        await query.answer("⤴️ Возврат к авторам (в разработке)")
        # TODO: Реализовать восстановление контекста авторов
    
    async def _handle_back_to_settings(self, query, context):
        """Возврат к настройкам"""
        await self.settings_handlers._show_settings_menu(query, query.from_user, from_callback=True)
    
    async def _handle_show_series(self, query, context, series_id: int):
        """Показ книг серии"""
        try:
            user = query.from_user
            settings = self.user_service.get_user_settings(user.id)
            query_text = context.user_data.get('last_search_query', '')
            
            # Создаем параметры поиска с фильтром по серии
            from ..services.search_service import SearchParams
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
            from ..core.custom_types import SearchType
            keyboard = self._create_books_keyboard(page, pages, SearchType.SERIES)
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            header_text = self._format_book_header(
                page, len(books), settings, query_text,
                series_name=context.user_data['current_series_name']
            )
            
            await query.edit_message_text(header_text, reply_markup=reply_markup)
            await query.answer()
            
            self.logger.log_user_action(
                EventType.SEARCH_SERIES, user.id, user.username,
                {"series_id": series_id, "count": len(books)}
            )
            
        except Exception as e:
            print(f"[DEBUG CALLBACK] _handle_show_series ERROR user={query.from_user.id} series_id={series_id}: {e}")
            await query.answer("❌ Ошибка")
            self.logger.log_error(
                "show_series_error", str(e), {"series_id": series_id},
                query.from_user.id, query.from_user.username
            )
    
    async def _handle_show_author(self, query, context, author_id: int):
        """Показ книг автора"""
        try:
            user = query.from_user
            settings = self.user_service.get_user_settings(user.id)
            query_text = context.user_data.get('last_search_query', '')
            
            # Создаем параметры поиска с фильтром по автору
            from ..services.search_service import SearchParams
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
            from ..core.custom_types import SearchType
            keyboard = self._create_books_keyboard(page, pages, SearchType.AUTHORS)
            keyboard.append([InlineKeyboardButton("👤 Об авторе", callback_data=f"author_info:{author_id}")])
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            header_text = self._format_book_header(
                page, len(books), settings, query_text,
                author_name=context.user_data['current_author_name']
            )
            
            await query.edit_message_text(header_text, reply_markup=reply_markup)
            await query.answer()
            
            self.logger.log_user_action(
                EventType.SEARCH_AUTHORS, user.id, user.username,
                {"author_id": author_id, "count": len(books)}
            )
            
        except Exception as e:
            print(f"[DEBUG CALLBACK] _handle_show_author ERROR user={query.from_user.id} author_id={author_id}: {e}")
            await query.answer("❌ Ошибка")
            self.logger.log_error(
                "show_author_error", str(e), {"author_id": author_id},
                query.from_user.id, query.from_user.username
            )
    
    async def _handle_show_popular(self, query, context, days: int):
        """Показ популярных книг (аналогично старой архитектуре)"""
        try:
            user = query.from_user
            settings = self.user_service.get_user_settings(user.id)
            
            # Получаем популярные книги через search_service
            result = await self.search_service.get_popular_books(settings, days)
            books = result.get('books', [])
            pages = result.get('pages', [])
            
            if not books:
                await query.edit_message_text(
                    "😞 Не нашёл подходящих книг. Попробуйте другие критерии поиска.",
                    parse_mode=ParseMode.HTML
                )
                return
            
            # Сохраняем в контекст для пагинации
            context.user_data['pages_of_books'] = pages
            context.user_data['found_books_count'] = len(books)
            context.user_data['show_pop'] = f'show_pop_{days}'
            
            # Показываем первую страницу
            page = 0
            from ..core.custom_types import SearchType
            keyboard = self._create_books_keyboard(page, pages, SearchType.BOOKS)
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            # Форматируем заголовок
            header_text = self._format_book_header(
                page, len(books), settings, query_text="",
                show_pop=f'show_pop_{days}'
            )
            
            await query.edit_message_text(header_text, reply_markup=reply_markup)
            await query.answer()
            
            self.logger.log_user_action(
                EventType.SEARCH_POPULAR, user.id, user.username,
                {"days": days, "count": len(books)}
            )
            
        except Exception as e:
            print(f"[DEBUG CALLBACK] _handle_show_popular ERROR user={query.from_user.id} days={days}: {e}")
            await query.answer("❌ Ошибка")
            self.logger.log_error(
                "show_popular_error", str(e), {"days": days},
                query.from_user.id, query.from_user.username
            )
    
    async def _handle_books_page(self, query, context, page: int):
        """Обработка пагинации книг"""
        try:
            user = query.from_user
            pages_of_books = context.user_data.get('pages_of_books')
            
            if not pages_of_books:
                await query.edit_message_text("❌ Сессия поиска истекла. Начните поиск заново.")
                return
            
            if page < 0 or page >= len(pages_of_books):
                await query.answer("❌ Неверный номер страницы")
                return
            
            settings = self.user_service.get_user_settings(user.id)
            from ..core.custom_types import SearchType
            
            # Определяем контекст поиска
            search_context = SearchType.BOOKS
            if 'current_series_id' in context.user_data:
                search_context = SearchType.SERIES
            elif 'current_author_id' in context.user_data:
                search_context = SearchType.AUTHORS
            
            keyboard = self._create_books_keyboard(page, pages_of_books, search_context)
            
            # Добавляем кнопку "Об авторе" для контекста автора
            if search_context == SearchType.AUTHORS:
                author_id = context.user_data.get('current_author_id')
                if author_id:
                    keyboard.append([InlineKeyboardButton("👤 Об авторе", callback_data=f"author_info:{author_id}")])
            
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            found_count = context.user_data.get('found_books_count', 0)
            query_text = context.user_data.get('last_search_query', '')
            show_pop = context.user_data.get('show_pop')
            
            header_text = self._format_book_header(
                page, found_count, settings, query_text,
                series_name=context.user_data.get('current_series_name'),
                author_name=context.user_data.get('current_author_name'),
                show_pop=show_pop
            )
            
            await query.edit_message_text(header_text, reply_markup=reply_markup)
            await query.answer()
            
            self.logger.log_user_action(
                EventType.SEARCH_BOOKS, user.id, user.username,
                {"action": "page_change", "page": page, "context": search_context.value}
            )
            
        except Exception as e:
            print(f"[DEBUG CALLBACK] _handle_books_page ERROR user={query.from_user.id} page={page}: {e}")
            await query.answer("❌ Ошибка")
            self.logger.log_error(
                "books_page_error", str(e), {"page": page},
                query.from_user.id, query.from_user.username
            )
    
    async def _handle_series_page(self, query, context, page: int):
        """Обработка пагинации серий"""
        try:
            user = query.from_user
            pages_of_series = context.user_data.get('pages_of_series')
            
            if not pages_of_series:
                await query.edit_message_text("❌ Результаты поиска устарели. Выполните новый поиск.")
                return
            
            if page < 0 or page >= len(pages_of_series):
                await query.answer("❌ Неверный номер страницы")
                return
            
            settings = self.user_service.get_user_settings(user.id)
            keyboard = self._create_series_keyboard(page, pages_of_series)
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            found_count = context.user_data.get('found_series_count', 0)
            query_text = context.user_data.get('last_search_query', '')
            header_text = self._format_series_header(page, found_count, settings, query_text)
            
            await query.edit_message_text(header_text, reply_markup=reply_markup)
            await query.answer()
            
            # Сохраняем текущую страницу
            context.user_data['last_series_page'] = page
            
            self.logger.log_user_action(
                EventType.SEARCH_SERIES, user.id, user.username,
                {"action": "page_change", "page": page}
            )
            
        except Exception as e:
            print(f"[DEBUG CALLBACK] _handle_series_page ERROR user={query.from_user.id} page={page}: {e}")
            await query.answer("❌ Ошибка")
            self.logger.log_error(
                "series_page_error", str(e), {"page": page},
                query.from_user.id, query.from_user.username
            )
    
    async def _handle_authors_page(self, query, context, page: int):
        """Обработка пагинации авторов"""
        try:
            user = query.from_user
            pages_of_authors = context.user_data.get('pages_of_authors')
            
            if not pages_of_authors:
                await query.edit_message_text("❌ Результаты поиска устарели. Выполните новый поиск.")
                return
            
            if page < 0 or page >= len(pages_of_authors):
                await query.answer("❌ Неверный номер страницы")
                return
            
            settings = self.user_service.get_user_settings(user.id)
            keyboard = self._create_authors_keyboard(page, pages_of_authors)
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            found_count = context.user_data.get('found_authors_count', 0)
            query_text = context.user_data.get('last_search_query', '')
            header_text = self._format_author_header(page, found_count, settings, query_text)
            
            await query.edit_message_text(header_text, reply_markup=reply_markup)
            await query.answer()
            
            # Сохраняем текущую страницу
            context.user_data['last_authors_page'] = page
            
            self.logger.log_user_action(
                EventType.SEARCH_AUTHORS, user.id, user.username,
                {"action": "page_change", "page": page}
            )
            
        except Exception as e:
            print(f"[DEBUG CALLBACK] _handle_authors_page ERROR user={query.from_user.id} page={page}: {e}")
            await query.answer("❌ Ошибка")
            self.logger.log_error(
                "authors_page_error", str(e), {"page": page},
                query.from_user.id, query.from_user.username
            )
    
    async def _handle_show_genres(self, query, context, genre_index: int):
        """Обработка показа дочерних жанров (отдельным сообщением)"""
        try:
            user = query.from_user
            
            # Получаем список родительских жанров
            parent_genres = await self.book_service.get_parent_genres_with_counts()
            
            if genre_index >= len(parent_genres):
                await query.answer("❌ Жанр не найден")
                return
            
            parent_genre_name, _ = parent_genres[genre_index]
            
            # Получаем дочерние жанры
            child_genres = await self.book_service.get_child_genres_with_counts(parent_genre_name)
            
            if not child_genres:
                await query.answer(f"❌ Для жанра '{parent_genre_name}' нет поджанров")
                return
            
            # Форматируем сообщение с дочерними жанрами
            text = f"📚 <b>Поджанры: {parent_genre_name}</b>\n\n"
            
            # Создаем ссылки на сайт Флибусты через FlibustaService
            for genre_name, count, genre_id in child_genres:
                search_url = self.book_service.flibusta_service.get_genre_url(genre_id)
                
                # Форматируем количество
                count_text = f"({count:,})".replace(",", " ") if count else "(0)"
                
                text += f"<a href='{search_url}'>{genre_name}</a> {count_text}\n"
            
            # Добавляем кнопку закрытия
            keyboard = [[
                InlineKeyboardButton("❌ Закрыть", callback_data="close_message")
            ]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            # Отправляем новое сообщение (не редактируем существующее)
            await context.bot.send_message(
                chat_id=user.id,
                text=text,
                reply_markup=reply_markup,
                parse_mode=ParseMode.HTML,
                disable_web_page_preview=False
            )
            
            await query.answer()
            
            self.logger.log_user_action(
                EventType.GENRES_VIEW, user.id, user.username,
                {"action": "view_child_genres", "parent_genre": parent_genre_name, "count": len(child_genres)}
            )
            
        except Exception as e:
            print(f"[DEBUG CALLBACK] _handle_show_genres ERROR user={query.from_user.id} genre_index={genre_index}: {e}")
            await query.answer("❌ Ошибка при загрузке поджанров")
            self.logger.log_error(
                "show_genres_error", str(e), {"genre_index": genre_index},
                query.from_user.id, query.from_user.username
            )
    
    # ===== УТИЛИТЫ ДЛЯ СОЗДАНИЯ КЛАВИАТУР =====
    
    def _create_books_keyboard(
        self,
        page: int,
        pages,
        search_context
    ):
        """Создание клавиатуры с книгами"""
        from ..core.custom_types import SearchType
        from typing import List
        
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
        pages
    ):
        """Создание клавиатуры с сериями"""
        from typing import List
        
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
        pages
    ):
        """Создание клавиатуры с авторами"""
        from typing import List
        
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
        keyboard,
        prefix: str,
        page: int,
        pages
    ) -> None:
        """Добавляет кнопки навигации"""
        from typing import List
        
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
        settings,
        query: str = "",
        series_name: str = None,
        author_name: str = None,
        show_pop: str = None
    ) -> str:
        """Форматирует заголовок для книг (аналогично старой архитектуре)"""
        from ..core.constants import HEADING_POP
        from typing import Optional
        
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
        settings,
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
        settings,
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
    
    def _format_author_name(self, book) -> str:
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