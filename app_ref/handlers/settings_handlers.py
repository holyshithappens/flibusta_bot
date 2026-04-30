"""
Обработчики настроек пользователя
"""
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import CallbackContext
from telegram.constants import ParseMode
from telegram.error import BadRequest

from ..services.user_service import UserService
from ..services.book_service import BookService
from ..core.structured_logger import StructuredLogger
from ..core.logging_schema import EventType

# Константы и конфигурация настроек
SETTING_MAX_BOOKS = 'max_books'
SETTING_LANG_SEARCH = 'lang_search'
SETTING_SIZE_LIMIT = 'size_limit'
SETTING_BOOK_FORMAT = 'book_format'
SETTING_SEARCH_TYPE = 'search_type'
SETTING_RATING_FILTER = 'rating_filter'
SETTING_SEARCH_AREA = 'aux_search'

# Централизованная конфигурация настроек
SETTINGS_CONFIG = {
    SETTING_MAX_BOOKS: {
        'title': 'Постраничный вывод',
        'field': 'max_books',
        'options': [(20, '20'), (40, '40')]
    },
    SETTING_LANG_SEARCH: {
        'title': 'Язык книг',
        'field': 'lang',
        'options': []  # Динамически из БД
    },
    SETTING_SIZE_LIMIT: {
        'title': 'Ограничение на размер книг',
        'field': 'book_size',
        'options': [('less800', '<800K'), ('more800', '>800K'), ('', 'Сбросить')]
    },
    SETTING_BOOK_FORMAT: {
        'title': 'Формат скачивания книг',
        'field': 'book_format',
        'options': [('fb2', 'FB2'), ('mobi', 'MOBI'), ('epub', 'EPUB')]
    },
    SETTING_SEARCH_TYPE: {
        'title': 'Вывод результатов',
        'field': 'search_type',
        'options': [('books', 'по книгам'), ('series', 'по сериям'), ('authors', 'по авторам')]
    },
    SETTING_RATING_FILTER: {
        'title': 'Фильтр по рейтингу',
        'field': 'rating',
        'options': [
            (0, '⚪️ Без рейтинга (0)'),
            (1, '🔴 Нечитаемо (1)'),
            (2, '🟠 Плохо (2)'),
            (3, '🟡 Неплохо (3)'),
            (4, '🟢 Хорошо (4)'),
            (5, '🔵 Отлично (5)')
        ],
        'multiple': True
    },
    SETTING_SEARCH_AREA: {
        'title': 'Область поиска',
        'field': 'search_area',
        'options': [
            ('b', 'по основным данным книг'),
            "__NEWLINE__",
            ('ba', 'по аннотации книг'),
            ('aa', 'по аннотации авторов')
        ]
    }
}


class SettingsHandlers:
    """
    Обработчики для управления настройками пользователя
    
    Команды:
    - /set - Меню настроек
    - Callback'и для изменения настроек
    """
    
    def __init__(
        self,
        user_service: UserService,
        book_service: BookService,
        logger: StructuredLogger
    ):
        self.user_service = user_service
        self.book_service = book_service
        self.logger = logger
    
    async def set_cmd(self, update: Update, context: CallbackContext) -> None:
        """Команда /set - Главное меню настроек"""
        user = update.effective_user
        
        if self.user_service.is_user_blocked(user.id):
            return
        
        await self._show_settings_menu(update, user)
        
        self.logger.log_user_action(
            EventType.SETTINGS_CHANGE, user.id, user.username,
            {"action": "viewed_settings_menu"}
        )
    
    async def handle_settings_callback(self, update: Update, context: CallbackContext) -> None:
        """Основной обработчик callback'ов настроек"""
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
            if data.startswith("settings:"):
                # Показ значений для настройки
                setting = data.split(":")[1]
                await self._show_setting_values(query, user, setting)
            
            elif data.startswith("set_"):
                # Установка значения настройки
                await self._handle_set_action(query, context, data)
            
            elif data.startswith("toggle_rating_"):
                # Переключение рейтинга (множественный выбор)
                await self._handle_toggle_rating(query, context, data)
            
            elif data == "reset_ratings":
                # Сброс всех рейтингов
                await self._handle_reset_ratings(query, context)
            
            elif data == "back_to_settings":
                # Возврат в главное меню настроек
                await self._show_settings_menu(query, user, from_callback=True)
            
            elif data == "close_message":
                # Закрытие сообщения
                await self._handle_close_message(query, context)
            
            else:
                await query.answer("Неизвестная команда")
                
        except Exception as e:
            print(f"[DEBUG SETTINGS] EXCEPTION user={user.id} data='{data}': {type(e).__name__}: {e}")
            import traceback
            traceback.print_exc()
            
            await query.answer("❌ Ошибка")
            self.logger.log_error(
                "settings_callback_error",
                str(e),
                {"data": data},
                user.id,
                user.username
            )
    
    def _get_setting_display_value(self, setting_type: str, settings) -> str:
        """Получить отображаемое значение для настройки"""
        config = SETTINGS_CONFIG[setting_type]
        field = config['field']
        current_value = getattr(settings, field, None)
        
        if not current_value:
            return ""
        
        # Для множественного выбора (рейтинги)
        if config.get('multiple'):
            ratings = current_value.split(',')
            emojis = "".join([config['options'][int(r)][1].split()[0] for r in ratings if r and int(r) in range(6)])
            return f"({emojis})" if emojis else ""
        
        # Ищем совпадение среди опций
        for option in config['options']:
            if option == "__NEWLINE__":
                continue
            value, display = option
            if str(value) == str(current_value):
                return f"({display})" if value else ""
        
        # Если не нашли, показываем как есть
        return f"({current_value})"
    
    async def _show_settings_menu(self, update_or_query, user, from_callback=False):
        """Показывает главное меню настроек - компактная версия"""
        try:
            settings = self.user_service.get_user_settings(user.id)
            keyboard = []
            
            for setting_type, config in SETTINGS_CONFIG.items():
                current_display = self._get_setting_display_value(setting_type, settings)
                title = config['title']
                button_text = f"{title} {current_display}" if current_display else title
                
                keyboard.append([InlineKeyboardButton(
                    button_text, callback_data=f"settings:{setting_type}"
                )])
            
            keyboard.append([InlineKeyboardButton(t('common.close'), callback_data="close_message")])
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            if from_callback:
                await update_or_query.edit_message_text(
                    "⚙️ <b>Настроить:</b>", reply_markup=reply_markup, parse_mode=ParseMode.HTML
                )
                await update_or_query.answer()
            else:
                await update_or_query.message.reply_text(
                    "⚙️ <b>Настроить:</b>", reply_markup=reply_markup, parse_mode=ParseMode.HTML
                )
            
            self.logger.log_user_action(
                EventType.SETTINGS_CHANGE, user.id, user.username,
                {"action": "viewed_settings_menu"}
            )
            
        except Exception as e:
            print(f"[DEBUG SETTINGS] _show_settings_menu ERROR user={user.id}: {e}")
            if from_callback:
                await update_or_query.answer("❌ Ошибка при загрузке настроек")
    
    async def _show_setting_values(self, query, user, setting: str) -> None:
        """Показывает варианты значений для настройки - компактная версия"""
        try:
            settings = self.user_service.get_user_settings(user.id)
            config = SETTINGS_CONFIG[setting]
            field = config['field']
            current_value = getattr(settings, field, None)
            
            # Для рейтинга особый случай - множественный выбор
            if setting == SETTING_RATING_FILTER:
                await self._show_rating_filter_keyboard(query, user, current_value)
                return
            
            # Для языка - динамические опции из БД
            if setting == SETTING_LANG_SEARCH:
                await self._show_lang_selection_keyboard(query, user, current_value)
                return
            
            # Для остальных настроек - стандартный выбор
            keyboard = []
            row = []
            
            for option in config['options']:
                if option == "__NEWLINE__":
                    if row:
                        keyboard.append(row)
                        row = []
                    continue
                
                value, display_text = option
                prefix = "✔️ " if str(value) == str(current_value) else ""
                row.append(InlineKeyboardButton(
                    f"{prefix}{display_text}",
                    callback_data=f"set_{setting}_to_{value}"
                ))
            
            if row:
                keyboard.append(row)
            
            keyboard.append([InlineKeyboardButton("⬅ Назад в настройки", callback_data="back_to_settings")])
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            try:
                await query.edit_message_text(
                    config['title'], reply_markup=reply_markup, parse_mode=ParseMode.HTML
                )
            except BadRequest as e:
                if "Message is not modified" in str(e):
                    print(f"[DEBUG SETTINGS] Message not modified (expected): setting='{setting}' user={user.id}")
                else:
                    raise e
            
            await query.answer()
            self.logger.log_user_action(
                EventType.SETTINGS_CHANGE, user.id, user.username,
                {"action": "settings_select", "setting": setting}
            )
            
        except Exception as e:
            print(f"[DEBUG SETTINGS] _show_setting_values ERROR setting='{setting}' user={user.id}: {e}")
            import traceback
            traceback.print_exc()
            await query.answer("❌ Ошибка при загрузке значений")
    
    async def _show_lang_selection_keyboard(self, query, user, current_value):
        """Показывает клавиатуру выбора языка - компактная версия"""
        try:
            keyboard = []
            
            # Если есть текущее значение, добавляем кнопку сброса
            if current_value:
                keyboard.append([
                    InlineKeyboardButton(
                        f"✔ {current_value} - сбросить",
                        callback_data=f"set_{SETTING_LANG_SEARCH}_to_"
                    )
                ])
            
            # Получаем языки из БД
            try:
                langs = await self.book_service.get_available_languages()
                buttons = []
                for lang_code, book_count in langs:
                    if lang_code:  # Пропускаем пустые значения
                        buttons.append(InlineKeyboardButton(
                            f"{lang_code}",
                            callback_data=f"set_{SETTING_LANG_SEARCH}_to_{lang_code}"
                        ))
                
                # Группируем по 8 кнопок в строку
                keyboard.extend([buttons[i:i + 8] for i in range(0, len(buttons), 8)])
            except Exception as e:
                print(f"[DEBUG SETTINGS] Error getting languages: {e}")
                await query.answer("❌ Ошибка при загрузке языков")
                return
            
            # Добавляем кнопку "Назад"
            keyboard.append([
                InlineKeyboardButton("⬅ Назад в настройки", callback_data="back_to_settings")
            ])
            
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await query.edit_message_text(
                SETTINGS_CONFIG[SETTING_LANG_SEARCH]['title'],
                reply_markup=reply_markup,
                parse_mode=ParseMode.HTML
            )
            await query.answer()
            
        except Exception as e:
            print(f"[DEBUG SETTINGS] _show_lang_selection_keyboard ERROR user={user.id}: {e}")
            await query.answer("❌ Ошибка при загрузке языков")
    
    async def _handle_set_action(self, query, context, data: str):
        """Обрабатывает установку значений настроек"""
        try:
            user = query.from_user
            
            # Парсим action: set_{setting}_to_{value}
            parts = data.split('_to_')
            if len(parts) != 2:
                await query.answer("❌ Неверный формат команды")
                return
            
            setting_full = parts[0]  # set_{setting}
            new_value = parts[1] if parts[1] else None  # value или пустое значение
            
            # Извлекаем название настройки
            if setting_full.startswith("set_"):
                setting = setting_full[4:]  # Убираем "set_"
                # Маппинг для совместимости с UserRepository
                setting_mapping = {
                    SETTING_LANG_SEARCH: 'lang',
                    SETTING_SIZE_LIMIT: 'book_size',
                    SETTING_BOOK_FORMAT: 'book_format',
                    SETTING_SEARCH_TYPE: 'search_type',
                    SETTING_RATING_FILTER: 'rating',
                    SETTING_SEARCH_AREA: 'search_area',
                    SETTING_MAX_BOOKS: 'max_books'
                }
                setting = setting_mapping.get(setting, setting)
            else:
                await query.answer("❌ Неверный формат настройки")
                return
            
            # Получаем старые настройки
            old_settings = self.user_service.get_user_settings(user.id)
            old_value = getattr(old_settings, setting, None)
            
            # Преобразуем значение если нужно
            if setting == SETTING_MAX_BOOKS and new_value is not None:
                new_value = int(new_value)
            
            # Обновляем настройку
            self.user_service.update_setting(user.id, setting, new_value)
            
            # Логируем изменение
            self.logger.log_settings_change(
                user.id, user.username or user.first_name,
                setting, old_value, new_value
            )
            
            # # DEBUG: Проверяем, что настройка сохранилась
            # updated_settings = self.user_service.get_user_settings(user.id)
            # actual_new_value = getattr(updated_settings, setting, None)
            # print(f"[DEBUG SETTINGS] After update - setting='{setting}' new_value='{new_value}' actual='{actual_new_value}'")
            
            # После изменения настройки показываем обновленное меню выбора
            # Используем try-except для обработки "Message is not modified" ошибки
            try:
                # Обратное маппинг для получения оригинального названия настройки
                reverse_mapping = {
                    'lang': SETTING_LANG_SEARCH,
                    'book_size': SETTING_SIZE_LIMIT,
                    'book_format': SETTING_BOOK_FORMAT,
                    'search_type': SETTING_SEARCH_TYPE,
                    'rating': SETTING_RATING_FILTER,
                    'search_area': SETTING_SEARCH_AREA,
                    'max_books': SETTING_MAX_BOOKS
                }
                original_setting = reverse_mapping.get(setting, setting)
                await self._show_setting_values(query, user, original_setting)
            except BadRequest as e:
                if "Message is not modified" in str(e):
                    # Игнорируем эту ошибку - сообщение уже в правильном состоянии
                    print(f"[DEBUG SETTINGS] Message not modified (expected): user={user.id} setting='{setting}' new_value='{new_value}'")
                else:
                    raise e
            
            await query.answer(f"✅ Установлено: {new_value or 'сброшено'}")
            
        except Exception as e:
            print(f"[DEBUG SETTINGS] _handle_set_action ERROR user={user.id} data='{data}': {e}")
            import traceback
            traceback.print_exc()
            await query.answer("❌ Ошибка при изменении настройки")
    
    async def _show_rating_filter_keyboard(self, query, user, current_value):
        """Показывает клавиатуру для множественного выбора рейтингов"""
        try:
            # Текущие рейтинги (множественный выбор)
            current_ratings = current_value.split(',') if current_value else []
            
            keyboard = []
            options = SETTINGS_CONFIG[SETTING_RATING_FILTER]['options']
            
            for value, display_text in options:
                is_selected = str(value) in current_ratings
                emoji = "✔" if is_selected else ""
                button_text = f"{emoji} {display_text}"
                
                keyboard.append([InlineKeyboardButton(
                    button_text,
                    callback_data=f"toggle_rating_{value}"
                )])
            
            # Кнопка сброса
            keyboard.append([InlineKeyboardButton("🔄 Сбросить все", callback_data="reset_ratings")])
            
            # Кнопка назад
            keyboard.append([InlineKeyboardButton("⬅ Назад в настройки", callback_data="back_to_settings")])
            
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await query.edit_message_text(
                SETTINGS_CONFIG[SETTING_RATING_FILTER]['title'],
                reply_markup=reply_markup,
                parse_mode=ParseMode.HTML
            )
            await query.answer()
            
        except Exception as e:
            print(f"[DEBUG SETTINGS] _show_rating_filter_keyboard ERROR user={user.id}: {e}")
            await query.answer("❌ Ошибка при загрузке фильтра рейтинга")
    
    async def _handle_toggle_rating(self, query, context, data: str):
        """Переключение рейтинга (множественный выбор)"""
        try:
            user = query.from_user
            rating_value = data.replace("toggle_rating_", "")
            
            # Получаем текущие настройки
            settings = self.user_service.get_user_settings(user.id)
            current_ratings = settings.rating.split(',') if settings.rating else []
            
            # Переключаем рейтинг
            if rating_value in current_ratings:
                # Удаляем если уже есть
                current_ratings = [r for r in current_ratings if r != rating_value]
            else:
                # Добавляем если нет
                current_ratings.append(rating_value)
            
            # Сортируем и сохраняем
            current_ratings.sort()
            new_value = ','.join(current_ratings) if current_ratings else None
            
            # Обновляем настройку
            old_value = settings.rating
            self.user_service.update_setting(user.id, 'rating', new_value)
            
            # Логируем
            self.logger.log_settings_change(
                user.id, user.username or user.first_name,
                SETTING_RATING_FILTER, old_value, new_value
            )
            
            # Обновляем клавиатуру
            await self._show_rating_filter_keyboard(query, user, new_value)
            
        except Exception as e:
            print(f"[DEBUG SETTINGS] _handle_toggle_rating ERROR user={user.id} data='{data}': {e}")
            await query.answer("❌ Ошибка при изменении рейтинга")
    
    async def _handle_reset_ratings(self, query, context):
        """Сброс всех рейтингов"""
        try:
            user = query.from_user
            
            # Получаем текущие настройки
            settings = self.user_service.get_user_settings(user.id)
            old_value = settings.rating
            
            # Сбрасываем рейтинги
            self.user_service.update_setting(user.id, 'rating', None)
            
            # Логируем
            self.logger.log_settings_change(
                user.id, user.username or user.first_name,
                SETTING_RATING_FILTER, old_value, None
            )
            
            # Обновляем клавиатуру
            await self._show_rating_filter_keyboard(query, user, None)
            
            await query.answer("🔄 Все рейтинги сброшены")
            
        except Exception as e:
            print(f"[DEBUG SETTINGS] _handle_reset_ratings ERROR user={user.id}: {e}")
            await query.answer("❌ Ошибка при сбросе рейтингов")
    
    async def _handle_close_message(self, query, context):
        """Удаление сообщения"""
        try:
            await query.message.delete()
            await query.answer()
            
        except Exception as e:
            await query.answer("❌ Не удалось удалить сообщение")