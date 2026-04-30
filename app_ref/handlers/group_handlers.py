"""
Обработчики групповых чатов
"""
from typing import List
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import CallbackContext
from telegram.constants import ParseMode

from ..services.search_service import SearchService
from ..services.book_service import BookService
from ..services.user_service import UserService
from ..core.structured_logger import StructuredLogger
from ..core.logging_schema import EventType
from ..services.search_service import SearchParams
from ..core.custom_types import BookInfo


class GroupHandlers:
    """
    Обработчики для групповых чатов
    
    Особенности:
    - Проверка прав доступа
    - Обработка только сообщений для бота
    - Контекст групповых поисков
    - Полная интеграция с новой архитектурой
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
    
    # ===== ОСНОВНОЙ ОБРАБОТЧИК СООБЩЕНИЙ =====
    
    async def handle_group_message(self, update: Update, context: CallbackContext) -> None:
        """Обработка сообщений в групповых чатах"""
        message = update.message
        user = message.from_user
        chat = message.chat
        
        # Проверка блокировки
        if self.user_service.is_user_blocked(user.id):
            return
        
        # Проверка, что сообщение адресовано боту
        bot_username = context.bot.username
        if not self._is_message_for_bot(message.text or "", bot_username):
            return
        
        # Извлекаем запрос (убираем mention)
        query = self._extract_clean_query(message.text or "", bot_username)
        
        if not query:
            await message.reply_text(
                f"ℹ️ <b>Использование в группе:</b>\n\n"
                f"@{bot_username} <i>название книги/автора</i>\n\n"
                f"Пример:\n"
                f"@{bot_username} Толстой Война и мир",
                parse_mode=ParseMode.HTML
            )
            return
        
        # Выполняем поиск
        try:
            # Показываем сообщение о обработке
            processing_msg = await message.reply_text(
                f"⏰ <i>Ищу книги по запросу от {user.first_name}...</i>",
                parse_mode=ParseMode.HTML,
                reply_to_message_id=message.message_id
            )
            
            # Получаем настройки пользователя
            settings = self.user_service.get_user_settings(user.id)
            
            # Выполняем поиск через SearchService
            params = SearchParams(
                query=query,
                settings=settings
            )
            result = await self.search_service.search_books(params)
            
            # Удаляем сообщение о обработке
            await processing_msg.delete()
            
            if not result['books']:
                await message.reply_text(
                    f"😞 Не нашёл подходящих книг для запроса '{query}'",
                    reply_to_message_id=message.message_id
                )
                return
            
            # Создаем клавиатуру
            pages = result['pages']
            page = 0
            keyboard = self._create_books_keyboard(page, pages)
            
            if not keyboard:
                await message.reply_text(
                    "❌ Ошибка при формировании результатов",
                    reply_to_message_id=message.message_id
                )
                return
            
            # Сохраняем контекст поиска в chat_data для пагинации
            if hasattr(message.chat, 'id'):
                if 'group_search_context' not in context.chat_data:
                    context.chat_data['group_search_context'] = {}
                context.chat_data['group_search_context'][message.message_id] = {
                    'pages': pages,
                    'query': query,
                    'total_count': result['total_count'],
                    'user_id': user.id,
                    'username': user.username or user.first_name
                }
            
            # Форматируем заголовок
            user_name = user.first_name or ""
            header = self._format_search_header(
                result['total_count'],
                page,
                len(pages),
                query,
                user_name
            )
            
            # Отправляем результаты
            await message.reply_text(
                header,
                reply_markup=InlineKeyboardMarkup(keyboard),
                reply_to_message_id=message.message_id
            )
            
            # Логируем поиск
            self.logger.log_search(
                user_id=user.id,
                username=user.username or user.first_name or "Unknown",
                query=query,
                search_type="books",
                search_area=settings.search_area,
                results_count=result['total_count'],
                duration_ms=0,
                chat_type=chat.type,
                chat_id=chat.id
            )
            
        except Exception as e:
            await message.reply_text(
                "❌ Произошла ошибка при поиске книг",
                reply_to_message_id=message.message_id
            )
            self.logger.log_error(
                error_type="group_search_error",
                error_message=str(e),
                context={"query": query, "chat_id": chat.id},
                user_id=user.id,
                username=user.username or user.first_name or "Unknown"
            )
    
    async def handle_group_callback(self, update: Update, context: CallbackContext) -> None:
        """Обработка callback'ов в групповых чатах"""
        query = update.callback_query
        user = query.from_user
        chat = query.message.chat
        
        # Проверка блокировки
        if self.user_service.is_user_blocked(user.id):
            await query.answer("❌ Вы заблокированы")
            return
        
        data = query.data
        
        # Обработка смены страницы
        if data.startswith("books_page_"):
            await self._handle_group_page_change(query, context)
            return
        
        # Проверка прав (только админы могут управлять настройками группы)
        if data.startswith("group_"):
            if chat.type != "private":
                member = await context.bot.get_chat_member(chat.id, user.id)
                if member.status not in ["creator", "administrator"]:
                    await query.answer("❌ Только админы могут управлять")
                    return
            
            # Обработка команд управления группой
            if data == "group_settings":
                await self._show_group_settings(query, chat)
            elif data.startswith("group_set:"):
                setting = data.split(":")[1]
                await self._set_group_setting(query, chat, setting)
            else:
                await query.answer("Неизвестный callback")
        else:
            # Все остальные callback'и (book_info, send_file и т.д.)
            # обрабатываются в личных сообщениях
            await query.answer("Это действие доступно только в личных сообщениях с ботом")
    
    async def _show_group_settings(self, query, chat) -> None:
        """Показать настройки группы"""
        keyboard = [
            [
                InlineKeyboardButton("📚 Лимит результатов", callback_data="group_set:limit"),
                InlineKeyboardButton("🔍 Поиск по", callback_data="group_set:search_area")
            ],
            [
                InlineKeyboardButton("✅ Готово", callback_data="group_done")
            ]
        ]
        
        from telegram import InlineKeyboardMarkup
        await query.edit_message_text(
            f"⚙️ <b>Настройки группы {chat.title}</b>\n\n"
            f"Выберите настройку:",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode=ParseMode.HTML
        )
        await query.answer()
    
    async def _set_group_setting(self, query, chat, setting: str) -> None:
        """Установить настройку группы"""
        # TODO: Реализовать сохранение настроек группы
        await query.edit_message_text(
            f"⚙️ <b>Настройка: {setting}</b>\n\n"
            f"Значение установлено (в разработке)",
            parse_mode=ParseMode.HTML
        )
        await query.answer()
    
    # ===== УТИЛИТЫ ДЛЯ ГРУППОВЫХ ЧАТОВ =====
    
    def _is_message_for_bot(self, message_text: str, bot_username: str) -> bool:
        """Проверяет, обращается ли пользователь к боту"""
        if not bot_username or not message_text:
            return False
        return message_text.startswith(f"@{bot_username}")
    
    def _extract_clean_query(self, message_text: str, bot_username: str) -> str:
        """Извлекает чистый поисковый запрос из сообщения"""
        if not message_text:
            return ""
        if bot_username:
            clean_text = message_text.replace(f"@{bot_username}", "").strip()
        else:
            clean_text = message_text.strip()
        return clean_text
    
    def _create_books_keyboard(
        self,
        page: int,
        pages_of_books: List[List[BookInfo]]
    ) -> List[List[InlineKeyboardButton]]:
        """Создание клавиатуры с кнопками книг и навигацией"""
        keyboard = []
        
        if not pages_of_books or page >= len(pages_of_books):
            return keyboard
        
        books_in_page = pages_of_books[page]
        
        for book in books_in_page:
            # Форматируем текст кнопки
            rating_emoji = self._get_rating_emoji(book.lib_rate)
            author_name = f"{book.last_name or ''} {book.first_name or ''}".strip()
            size_str = self._format_size(book.book_size)
            
            button_text = f"{rating_emoji} {book.title} ({author_name}) {size_str}"
            if book.search_year != 0:
                button_text += f"/{book.search_year}"
            
            keyboard.append([
                InlineKeyboardButton(
                    button_text,
                    callback_data=f"book_info:{book.file_name}"
                )
            ])
        
        # Добавляем кнопки навигации
        self._add_navigation_buttons(keyboard, page, pages_of_books)
        
        return keyboard
    
    def _format_search_header(
        self,
        total_count: int,
        page: int,
        total_pages: int,
        query: str,
        user_name: str = ""
    ) -> str:
        """Форматирует заголовок результатов поиска для группы"""
        header = f"📚 Результаты поиска"
        if user_name:
            header += f" для {user_name}"
        header += ":\n\n"
        
        header += self.search_service.format_results_header(
            total_count, page, total_pages, query
        )
        
        return header
    
    def _get_rating_emoji(self, rating: float) -> str:
        """Возвращает эмодзи для рейтинга"""
        if rating >= 5:
            return "🔵"
        elif rating >= 4:
            return "🟢"
        elif rating >= 3:
            return "🟡"
        elif rating >= 2:
            return "🟠"
        elif rating >= 1:
            return "🔴"
        else:
            return "⚪️"
    
    def _format_size(self, size_bytes: int) -> str:
        """Форматирует размер файла"""
        units = ["B", "K", "M", "G", "T"]
        unit_index = 0
        size = size_bytes
        while size >= 1024 and unit_index < len(units) - 1:
            size /= 1024
            unit_index += 1
        return f"{size:.1f}{units[unit_index]}"
    
    def _add_navigation_buttons(
        self,
        keyboard: List,
        page: int,
        pages: List[List]
    ) -> None:
        """Добавляет кнопки навигации в клавиатуру"""
        navigation_buttons = []
        
        if page > 0:
            navigation_buttons.append(
                InlineKeyboardButton("⬆ В начало", callback_data=f"books_page_0")
            )
            navigation_buttons.append(
                InlineKeyboardButton("⬅️ Назад", callback_data=f"books_page_{page - 1}")
            )
        
        if page < len(pages) - 1:
            navigation_buttons.append(
                InlineKeyboardButton("Вперёд ➡️", callback_data=f"books_page_{page + 1}")
            )
            navigation_buttons.append(
                InlineKeyboardButton("В конец ⬇️", callback_data=f"books_page_{len(pages) - 1}")
            )
        
        if navigation_buttons:
            keyboard.append(navigation_buttons)
    
    async def _handle_group_page_change(self, query, context: CallbackContext) -> None:
        """Обработка смены страницы в группе"""
        try:
            data = query.data
            page = int(data.split("_")[-1])
            message = query.message
            
            # Восстанавливаем контекст поиска из chat_data
            search_contexts = context.chat_data.get('group_search_context', {})
            message_context = search_contexts.get(message.message_id)
            
            if not message_context:
                await query.edit_message_text(
                    "⏰ <b>Контекст поиска устарел</b>\n\n"
                    "Выполните новый поиск в группе.\n"
                    f"@{context.bot.username} <i>название книги</i>",
                    parse_mode=ParseMode.HTML,
                    reply_markup=None
                )
                await query.answer()
                return
            
            pages = message_context['pages']
            query_text = message_context['query']
            total_count = message_context['total_count']
            
            if page < 0 or page >= len(pages):
                await query.answer("❌ Неверная страница")
                return
            
            # Создаем новую клавиатуру для страницы
            keyboard = self._create_books_keyboard(page, pages)
            
            # Форматируем заголовок
            user_name = message_context.get('username', '')
            header = self._format_search_header(
                total_count, page, len(pages), query_text, user_name
            )
            
            # Обновляем сообщение
            await query.edit_message_text(
                header,
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode=ParseMode.HTML
            )
            
            await query.answer()
            
            # Логируем действие
            self.logger.log_user_action(
                EventType.PAGE_CHANGE,
                query.from_user.id,
                query.from_user.username or query.from_user.first_name or "Unknown",
                {"page": page, "chat_type": "group"},
                chat_type="group",
                chat_id=message.chat.id
            )
            
        except Exception as e:
            await query.edit_message_text(
                "❌ <b>Ошибка при смене страницы</b>\n\n"
                "Попробуйте выполнить поиск заново.",
                parse_mode=ParseMode.HTML
            )
            self.logger.log_error(
                "group_page_change_error",
                str(e),
                {"page": page},
                query.from_user.id,
                query.from_user.username
            )