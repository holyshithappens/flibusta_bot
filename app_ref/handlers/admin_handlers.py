"""
Обработчики админ-панели
Полная интеграция с новой архитектурой
"""
import os
import time
from typing import List, Dict, Any
from datetime import datetime

from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import CallbackContext, ConversationHandler, MessageHandler, CallbackQueryHandler, filters
from telegram.constants import ParseMode

from ..services.admin_service import AdminService
from ..services.user_service import UserService
from ..core.structured_logger import StructuredLogger

# Константы для ConversationHandler
(
    ADMIN_AUTH,
    ADMIN_MENU,
    ADMIN_USER_MANAGE,
    ADMIN_BROADCAST
) = range(4)

# Глобальный словарь для хранения сессий администраторов
admin_sessions: Dict[int, Dict[str, Any]] = {}

# Константы
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "")
ADMIN_SESSION_TIMEOUT = 1800  # 30 минут
USERS_PER_PAGE = 10


class AdminHandlers:
    """
    Обработчики для админ-панели
    
    Полная интеграция с новой архитектурой:
    - Аутентификация с сессиями
    - Управление пользователями через UserService
    - Статистика через AdminService
    - Бэкапы через AdminService
    - Системная информация
    """
    
    def __init__(
        self,
        admin_service: AdminService,
        user_service: UserService,
        logger: StructuredLogger
    ):
        self.admin_service = admin_service
        self.user_service = user_service
        self.logger = logger
    
    # ===== УТИЛИТЫ АУТЕНТИФИКАЦИИ =====
    
    def _authenticate_admin(self, password: str) -> bool:
        """Проверяет пароль администратора"""
        return password == ADMIN_PASSWORD and ADMIN_PASSWORD != ""
    
    def _grant_admin_access(self, user_id: int, duration: int = ADMIN_SESSION_TIMEOUT) -> None:
        """Дает права администратора на указанное время"""
        admin_until = int(time.time()) + duration
        admin_sessions[user_id] = {
            "admin_until": admin_until,
            "permissions": {
                "view_stats": True,
                "broadcast": True,
                "manage_users": True,
                "view_logs": True
            }
        }
    
    def _revoke_admin_access(self, user_id: int) -> None:
        """Забирает права администратора"""
        admin_sessions.pop(user_id, None)
    
    def _is_admin(self, user_id: int) -> bool:
        """Проверяет, является ли пользователь администратором"""
        self._cleanup_expired_sessions()
        
        session = admin_sessions.get(user_id)
        if session and session["admin_until"] > time.time():
            return True
        if session:
            self._revoke_admin_access(user_id)
        return False
    
    def _cleanup_expired_sessions(self) -> int:
        """Очищает просроченные админские сессии"""
        current_time = time.time()
        expired_users = [
            user_id for user_id, session in admin_sessions.items()
            if session["admin_until"] <= current_time
        ]
        for user_id in expired_users:
            self._revoke_admin_access(user_id)
        return len(expired_users)
    
    # ===== ОСНОВНЫЕ ОБРАБОТЧИКИ =====
    
    async def admin_cmd(self, update: Update, context: CallbackContext) -> int:
        """Команда /admin - Начало входа"""
        user = update.effective_user
        
        # Проверка прав (только определенные пользователи)
        allowed_admins = [int(x) for x in os.getenv("ADMIN_USER_IDS", "").split(",") if x]
        
        if user.id not in allowed_admins:
            await update.message.reply_text(
                "❌ <b>Доступ запрещен</b>\n\n"
                "У вас нет прав администратора",
                parse_mode=ParseMode.HTML
            )
            return ConversationHandler.END
        
        if self._is_admin(user.id):
            await update.message.reply_text(
                "👑 <b>Панель администратора</b>\n\n"
                "Выберите действие:",
                reply_markup=self._admin_menu_keyboard(),
                parse_mode=ParseMode.HTML
            )
            return ADMIN_MENU
        
        await update.message.reply_text(
            "🔐 <b>Админ-панель</b>\n\n"
            "Введите пароль:",
            parse_mode=ParseMode.HTML
        )
        
        self.logger.log_user_action(
            user.id, user.username, "admin_attempt"
        )
        
        return ADMIN_AUTH
    
    async def auth_password(self, update: Update, context: CallbackContext) -> int:
        """Проверка пароля"""
        user = update.effective_user
        password = update.message.text.strip()
        
        if self._authenticate_admin(password):
            self._grant_admin_access(user.id)
            
            await update.message.reply_text(
                f"✅ <b>Доступ разрешен!</b>\n\n"
                f"Права администратора активны до {time.strftime('%H:%M:%S', time.localtime(admin_sessions[user.id]['admin_until']))}\n\n"
                "Выберите действие:",
                reply_markup=self._admin_menu_keyboard(),
                parse_mode=ParseMode.HTML
            )
            
            self.logger.log_user_action(
                user.id, user.username, "admin_auth_success"
            )
            
            return ADMIN_MENU
        else:
            await update.message.reply_text(
                "❌ <b>Неверный пароль</b>\n\n"
                "Попробуйте еще раз или /cancel",
                parse_mode=ParseMode.HTML
            )
            
            self.logger.log_user_action(
                user.id, user.username, "admin_auth_fail"
            )
            
            return ADMIN_AUTH
    
    async def admin_menu_handler(self, update: Update, context: CallbackContext) -> int:
        """Обработчик главного меню админ-панели"""
        user = update.effective_user
        
        if not self._is_admin(user.id):
            await update.message.reply_text(
                "❌ Права администратора истекли",
                reply_markup=ReplyKeyboardRemove()
            )
            return ConversationHandler.END
        
        text = update.message.text
        
        if text == "📊 Статистика":
            await self._show_stats(update, context)
        elif text == "👥 Пользователи":
            await self._show_users_list(update, context, page=0)
        elif text == "📢 Рассылка":
            await update.message.reply_text(
                "📢 <b>Массовая рассылка</b>\n\n"
                "Введите сообщение для рассылки:",
                parse_mode=ParseMode.HTML
            )
            return ADMIN_BROADCAST
        elif text == "💾 Резервные копии":
            await self._create_backup(update, context)
        elif text == "⚙️ Система":
            await self._show_system_info(update, context)
        elif text == "👤 Кто я":
            await self._show_whoami(update, context)
        elif text == "🔍 Последняя активность":
            await self._show_recent_activity(update, context)
        elif text == "🚪 Выход":
            await self._admin_logout(update, context)
            return ConversationHandler.END
        
        return ADMIN_MENU
    
    async def handle_broadcast(self, update: Update, context: CallbackContext) -> int:
        """Обработка рассылки"""
        user = update.effective_user
        
        if not self._is_admin(user.id):
            await update.message.reply_text(
                "❌ Права администратора истекли",
                reply_markup=ReplyKeyboardRemove()
            )
            return ConversationHandler.END
        
        message_text = update.message.text
        
        # TODO: Реализовать рассылку всем пользователям
        await update.message.reply_text(
            f"📢 <b>Рассылка начата</b>\n\n"
            f"Сообщение: {message_text}\n\n"
            f"Функция в разработке...",
            parse_mode=ParseMode.HTML,
            reply_markup=self._admin_menu_keyboard()
        )
        
        return ADMIN_MENU
    
    async def handle_callback(self, update: Update, context: CallbackContext) -> None:
        """Обработчик callback-запросов"""
        query = update.callback_query
        await query.answer()
        
        user = query.from_user
        
        if not self._is_admin(user.id):
            await query.edit_message_text(
                "❌ Права администратора истекли"
            )
            return
        
        data = query.data
        
        if data.startswith("users_list:"):
            page = int(data.split(":")[1])
            await self._show_users_list_callback(query, context, page)
        elif data.startswith("user_detail:"):
            user_id = int(data.split(":")[1])
            await self._show_user_detail(query, context, user_id)
        elif data.startswith("toggle_block:"):
            user_id = int(data.split(":")[1])
            await self._toggle_user_block(query, context, user_id)
        elif data == "back_to_stats":
            await self._show_stats_callback(query, context)
        elif data == "show_system_info":
            await self._show_system_info_callback(query, context)
    
    # ===== СТАТИСТИКА =====
    
    async def _show_stats(self, update: Update, context: CallbackContext) -> None:
        """Показывает статистику"""
        stats = self.admin_service.get_system_stats()
        
        text = self.admin_service.format_stats_message(stats)
        
        keyboard = [
            [InlineKeyboardButton("📋 Детальный список пользователей", callback_data="users_list:0")],
            [InlineKeyboardButton("🔍 Топ поисковых запросов", callback_data="top_searches")],
            [InlineKeyboardButton("📥 Топ скачиваний", callback_data="top_downloads")],
            [InlineKeyboardButton("⚙️ Системная информация", callback_data="show_system_info")]
        ]
        
        await update.message.reply_text(
            text,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode=ParseMode.HTML
        )
    
    async def _show_stats_callback(self, query, context: CallbackContext) -> None:
        """Показывает статистику (callback version)"""
        stats = self.admin_service.get_system_stats()
        text = self.admin_service.format_stats_message(stats)
        
        keyboard = [
            [InlineKeyboardButton("📋 Детальный список пользователей", callback_data="users_list:0")],
            [InlineKeyboardButton("🔍 Топ поисковых запросов", callback_data="top_searches")],
            [InlineKeyboardButton("📥 Топ скачиваний", callback_data="top_downloads")],
            [InlineKeyboardButton("⚙️ Системная информация", callback_data="show_system_info")]
        ]
        
        await query.edit_message_text(
            text,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode=ParseMode.HTML
        )
    
    # ===== ПОЛЬЗОВАТЕЛИ =====
    
    async def _show_users_list(self, update: Update, context: CallbackContext, page: int = 0) -> None:
        """Показывает список пользователей"""
        users = self.admin_service.get_user_list()
        total_users = len(users)
        
        start_idx = page * USERS_PER_PAGE
        end_idx = start_idx + USERS_PER_PAGE
        page_users = users[start_idx:end_idx]
        
        text = f"👥 <b>Список пользователей</b>\n\n"
        text += f"Страница {page + 1} из {((total_users - 1) // USERS_PER_PAGE) + 1}\n\n"
        
        keyboard = []
        
        for user_info in page_users:
            user_id = user_info['user_id']
            is_blocked = user_info['is_blocked']
            last_activity = user_info['last_activity']
            
            status = "❌" if is_blocked else "✅"
            activity_str = f" | 📅{last_activity.split()[0]}" if last_activity else ""
            
            button_text = f"{status} ID: {user_id}{activity_str}"
            
            keyboard.append([InlineKeyboardButton(
                button_text,
                callback_data=f"user_detail:{user_id}"
            )])
        
        # Кнопки навигации
        nav_buttons = []
        if page > 0:
            nav_buttons.append(InlineKeyboardButton("⬅️ Назад", callback_data=f"users_list:{page - 1}"))
        if end_idx < total_users:
            nav_buttons.append(InlineKeyboardButton("Вперёд ➡️", callback_data=f"users_list:{page + 1}"))
        if nav_buttons:
            keyboard.append(nav_buttons)
        
        keyboard.append([InlineKeyboardButton("⬅️ Назад в статистику", callback_data="back_to_stats")])
        
        await update.message.reply_text(
            text,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode=ParseMode.HTML
        )
    
    async def _show_users_list_callback(self, query, context: CallbackContext, page: int = 0) -> None:
        """Показывает список пользователей (callback version)"""
        users = self.admin_service.get_user_list()
        total_users = len(users)
        
        start_idx = page * USERS_PER_PAGE
        end_idx = start_idx + USERS_PER_PAGE
        page_users = users[start_idx:end_idx]
        
        text = f"👥 <b>Список пользователей</b>\n\n"
        text += f"Страница {page + 1} из {((total_users - 1) // USERS_PER_PAGE) + 1}\n\n"
        
        keyboard = []
        
        for user_info in page_users:
            user_id = user_info['user_id']
            is_blocked = user_info['is_blocked']
            last_activity = user_info['last_activity']
            
            status = "❌" if is_blocked else "✅"
            activity_str = f" | 📅{last_activity.split()[0]}" if last_activity else ""
            
            button_text = f"{status} ID: {user_id}{activity_str}"
            
            keyboard.append([InlineKeyboardButton(
                button_text,
                callback_data=f"user_detail:{user_id}"
            )])
        
        # Кнопки навигации
        nav_buttons = []
        if page > 0:
            nav_buttons.append(InlineKeyboardButton("⬅️ Назад", callback_data=f"users_list:{page - 1}"))
        if end_idx < total_users:
            nav_buttons.append(InlineKeyboardButton("Вперёд ➡️", callback_data=f"users_list:{page + 1}"))
        if nav_buttons:
            keyboard.append(nav_buttons)
        
        keyboard.append([InlineKeyboardButton("⬅️ Назад в статистику", callback_data="back_to_stats")])
        
        await query.edit_message_text(
            text,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode=ParseMode.HTML
        )
    
    async def _show_user_detail(self, query, context: CallbackContext, user_id: int) -> None:
        """Показывает детальную информацию о пользователе"""
        user_details = self.admin_service.get_user_details(user_id)
        
        settings = user_details['settings']
        
        text = f"👤 <b>Информация о пользователе</b>\n\n"
        text += f"<b>ID:</b> {user_id}\n"
        text += f"<b>Статус:</b> {'❌ Заблокирован' if settings['is_blocked'] else '✅ Активен'}\n"
        text += f"<b>Книг на странице:</b> {settings['max_books']}\n"
        text += f"<b>Язык:</b> {settings['lang'] or 'все'}\n"
        text += f"<b>Формат:</b> {settings['book_format']}\n"
        text += f"<b>Тип поиска:</b> {settings['search_type']}\n"
        text += f"<b>Последняя активность:</b> {user_details['last_activity'] or 'нет данных'}\n"
        text += f"<b>Всего событий:</b> {user_details['activity_count']}\n"
        
        keyboard = [
            [InlineKeyboardButton(
                "🚫 Заблокировать" if not settings['is_blocked'] else "✅ Разблокировать",
                callback_data=f"toggle_block:{user_id}"
            )],
            [InlineKeyboardButton("⬅️ Назад к списку", callback_data="users_list:0")]
        ]
        
        await query.edit_message_text(
            text,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode=ParseMode.HTML
        )
    
    async def _toggle_user_block(self, query, context: CallbackContext, user_id: int) -> None:
        """Блокирует/разблокирует пользователя"""
        current_user_id = query.from_user.id
        
        # Проверяем, не пытаемся ли заблокировать самого себя
        if user_id == current_user_id:
            await query.answer("❌ Нельзя заблокировать самого себя")
            return
        
        # Проверяем, не пытаемся ли заблокировать другого администратора
        allowed_admins = [int(x) for x in os.getenv("ADMIN_USER_IDS", "").split(",") if x]
        if user_id in allowed_admins:
            await query.answer("❌ Нельзя заблокировать администратора")
            return
        
        user_details = self.admin_service.get_user_details(user_id)
        current_block_status = user_details['settings']['is_blocked']
        
        if current_block_status:
            success = self.admin_service.unblock_user(user_id)
            action = "разблокирован"
        else:
            success = self.admin_service.block_user(user_id)
            action = "заблокирован"
        
        if success:
            await query.answer(f"Пользователь {action}")
            await self._show_user_detail(query, context, user_id)
        else:
            await query.answer(f"❌ Ошибка при {action} пользователя")
    
    # ===== БЭКАП =====
    
    async def _create_backup(self, update: Update, context: CallbackContext) -> None:
        """Создает резервные копии"""
        await update.message.reply_text(
            "💾 <b>Создание резервных копий...</b>",
            parse_mode=ParseMode.HTML
        )
        
        backup_info = self.admin_service.backup_databases()
        
        if backup_info['success']:
            text = f"""
💾 <b>Резервные копии созданы</b>

<b>Базы данных:</b>
{chr(10).join([f'• {db_file}' for db_file in backup_info['db_files']]) if backup_info['db_files'] else '• Файлы БД не найдены'}
• Размер архива: {backup_info['db_size'] / 1024:.1f} KB

<b>Логи:</b>
• Найдено файлов: {backup_info['log_files_count']}
• Размер архива: {backup_info['logs_size'] / 1024:.1f} KB
"""
            
            await update.message.reply_text(text, parse_mode=ParseMode.HTML)
            
            # Отправляем файлы если они созданы
            if backup_info['db_backup_path'] and os.path.exists(backup_info['db_backup_path']):
                await update.message.reply_document(
                    document=open(backup_info['db_backup_path'], 'rb'),
                    filename=f"databases_backup_{backup_info['timestamp']}.zip",
                    caption="📊 Архив баз данных"
                )
                os.remove(backup_info['db_backup_path'])
            
            if backup_info['logs_backup_path'] and os.path.exists(backup_info['logs_backup_path']):
                await update.message.reply_document(
                    document=open(backup_info['logs_backup_path'], 'rb'),
                    filename=f"logs_backup_{backup_info['timestamp']}.zip",
                    caption="📝 Архив логов"
                )
                os.remove(backup_info['logs_backup_path'])
        else:
            await update.message.reply_text(
                f"❌ <b>Ошибка при создании резервных копий:</b>\n{backup_info['error']}",
                parse_mode=ParseMode.HTML
            )
    
    # ===== СИСТЕМНАЯ ИНФОРМАЦИЯ =====
    
    async def _show_system_info(self, update: Update, context: CallbackContext) -> None:
        """Показывает системную информацию"""
        sys_info = self.admin_service.get_system_info()
        
        text = f"""
⚙️ <b>Системная информация</b>

<b>Система:</b>
• Платформа: {sys_info['system']['platform']}
• Версия: {sys_info['system']['version']}
• Процессор: {sys_info['system']['processor']}

<b>Python:</b>
• Версия: {sys_info['python']['version']}
• Реализация: {sys_info['python']['implementation']}

<b>Память:</b>
• Всего: {sys_info['memory']['total']} GB
• Доступно: {sys_info['memory']['available']} GB
• Использовано: {sys_info['memory']['percent']}%

<b>Диск:</b>
• Всего: {sys_info['disk']['total']} GB
• Использовано: {sys_info['disk']['used']} GB
• Свободно: {sys_info['disk']['free']} GB
• Использовано: {sys_info['disk']['percent']}%

<b>Процесс:</b>
• PID: {sys_info['process']['pid']}
• CPU: {sys_info['process']['cpu_percent']}%
• Память: {sys_info['process']['memory_mb']} MB

<b>Админские сессии:</b>
• Активных сессий: {len([uid for uid in admin_sessions if admin_sessions[uid]['admin_until'] > time.time()])}
• Очищено просроченных: {self._cleanup_expired_sessions()}
"""
        
        keyboard = [
            [InlineKeyboardButton("⬅️ Назад", callback_data="back_to_stats")]
        ]
        
        await update.message.reply_text(
            text,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode=ParseMode.HTML
        )
    
    async def _show_system_info_callback(self, query, context: CallbackContext) -> None:
        """Показывает системную информацию (callback version)"""
        sys_info = self.admin_service.get_system_info()
        
        text = f"""
⚙️ <b>Системная информация</b>

<b>Система:</b>
• Платформа: {sys_info['system']['platform']}
• Версия: {sys_info['system']['version']}
• Процессор: {sys_info['system']['processor']}

<b>Python:</b>
• Версия: {sys_info['python']['version']}
• Реализация: {sys_info['python']['implementation']}

<b>Память:</b>
• Всего: {sys_info['memory']['total']} GB
• Доступно: {sys_info['memory']['available']} GB
• Использовано: {sys_info['memory']['percent']}%

<b>Диск:</b>
• Всего: {sys_info['disk']['total']} GB
• Использовано: {sys_info['disk']['used']} GB
• Свободно: {sys_info['disk']['free']} GB
• Использовано: {sys_info['disk']['percent']}%

<b>Процесс:</b>
• PID: {sys_info['process']['pid']}
• CPU: {sys_info['process']['cpu_percent']}%
• Память: {sys_info['process']['memory_mb']} MB

<b>Админские сессии:</b>
• Активных сессий: {len([uid for uid in admin_sessions if admin_sessions[uid]['admin_until'] > time.time()])}
• Очищено просроченных: {self._cleanup_expired_sessions()}
"""
        
        keyboard = [
            [InlineKeyboardButton("⬅️ Назад", callback_data="back_to_stats")]
        ]
        
        await query.edit_message_text(
            text,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode=ParseMode.HTML
        )
    
    async def _show_whoami(self, update: Update, context: CallbackContext) -> None:
        """Показывает информацию о текущей сессии"""
        user = update.effective_user
        session = admin_sessions.get(user.id)
        
        if session and session["admin_until"] > time.time():
            expires = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(session["admin_until"]))
            await update.message.reply_text(
                f"👑 <b>Вы администратор</b>\n\n"
                f"• ID: {user.id}\n"
                f"• Имя: {user.first_name}\n"
                f"• Сессия действительна до: {expires}\n"
                f"• Осталось: {session['admin_until'] - time.time():.0f} секунд",
                parse_mode=ParseMode.HTML
            )
        else:
            await update.message.reply_text(
                "❌ <b>Вы не администратор</b>\n\n"
                "Используйте /admin для входа",
                parse_mode=ParseMode.HTML
            )
    
    async def _show_recent_activity(self, update: Update, context: CallbackContext) -> None:
        """Показывает последнюю активность"""
        # TODO: Реализовать получение последней активности из логов
        await update.message.reply_text(
            "🔍 <b>Последняя активность</b>\n\n"
            "Функция в разработке...",
            parse_mode=ParseMode.HTML
        )
    
    async def _admin_logout(self, update: Update, context: CallbackContext) -> None:
        """Выход из режима администратора"""
        user = update.effective_user
        self._revoke_admin_access(user.id)
        
        await update.message.reply_text(
            "🚪 <b>Режим администратора завершен</b>",
            parse_mode=ParseMode.HTML,
            reply_markup=ReplyKeyboardRemove()
        )
    
    async def cancel(self, update: Update, context: CallbackContext) -> int:
        """Отмена"""
        await update.message.reply_text(
            "❌ <b>Отменено</b>",
            parse_mode=ParseMode.HTML,
            reply_markup=ReplyKeyboardRemove()
        )
        return ConversationHandler.END
    
    def _admin_menu_keyboard(self):
        """Клавиатура меню администратора"""
        keyboard = [
            ["📊 Статистика", "🔍 Последняя активность"],
            ["👥 Пользователи", "💾 Резервные копии"],
            ["📢 Рассылка", "⚙️ Система"],
            ["👤 Кто я", "🚪 Выход"]
        ]
        return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    
    def get_conversation_handler(self):
        """Возвращает ConversationHandler для админ-панели"""
        return ConversationHandler(
            entry_points=[filters.Regex("^/admin$")],
            states={
                ADMIN_AUTH: [
                    MessageHandler(filters.TEXT & ~filters.COMMAND, self.auth_password)
                ],
                ADMIN_MENU: [
                    MessageHandler(filters.TEXT & ~filters.COMMAND, self.admin_menu_handler),
                    CallbackQueryHandler(self.handle_callback)
                ],
                ADMIN_BROADCAST: [
                    MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_broadcast)
                ]
            },
            fallbacks=[MessageHandler(filters.Regex("^/cancel$"), self.cancel)],
            allow_reentry=True
        )