import zipfile
from datetime import datetime
import json
import os
import time

from telegram import Update, ReplyKeyboardMarkup, ReplyKeyboardRemove, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.constants import ParseMode
from telegram.ext import CallbackContext, ConversationHandler

from .context import get_user_params, update_user_params
from .repositories.logs_repository import LogsRepository

# Создаем экземпляр репозитория логов
LOGS_REPO = LogsRepository()

# Добавляем константы для пагинации
USERS_PER_PAGE = 10

# Админские кнопки: ключ - имя обработчика, значение - текст кнопки
# Добавляем новые админские кнопки
ADMIN_BUTTONS = {
    "admin_user_stats": "📊 Статистика",
    "admin_users": "👥 Пользователи",
    "admin_broadcast": "📢 Рассылка",
    "admin_backup": "💾 Резервные копии",
    "admin_system": "⚙️ Система",
    "admin_whoami": "👤 Кто я",
    "admin_logout": "🚪 Выход",
    "admin_recent_activity": "🔍 Последняя активность"
}

# Обратное mapping: текст кнопки -> имя обработчика
ADMIN_BUTTONS_REVERSE = {v: k for k, v in ADMIN_BUTTONS.items()}

# Глобальный словарь для хранения сессий администраторов
# Format: {user_id: {"admin_until": timestamp, "permissions": {...}}}
admin_sessions = {}

# Константы
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "")
ADMIN_SESSION_TIMEOUT = 1800  # 30 минут

# ===== АДМИНИСТРИРОВАНИЕ =====

AUTH_PASSWORD = 1

def authenticate_admin(password: str) -> bool:
    """Проверяет пароль администратора"""
    return password == ADMIN_PASSWORD and ADMIN_PASSWORD != ""


def grant_admin_access(user_id: int, duration: int = ADMIN_SESSION_TIMEOUT):
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


def revoke_admin_access(user_id: int):
    """Забирает права администратора"""
    admin_sessions.pop(user_id, None)


def is_admin(user_id: int) -> bool:
    """Проверяет, является ли пользователь администратором"""
    # Сначала очищаем просроченные сессии
    cleanup_expired_sessions()

    session = admin_sessions.get(user_id)
    if session and session["admin_until"] > time.time():
        return True
    # Автоматически очищаем просроченные сессии
    if session:
        revoke_admin_access(user_id)
    return False


def cleanup_expired_sessions():
    """Очищает просроченные админские сессии"""
    current_time = time.time()
    expired_users = [
        user_id for user_id, session in admin_sessions.items()
        if session["admin_until"] <= current_time
    ]
    for user_id in expired_users:
        revoke_admin_access(user_id)
    return len(expired_users)


async def cleanup_admin_sessions(context: CallbackContext):
    """Периодическая очистка просроченных админских сессий"""
    cleaned = cleanup_expired_sessions()
    if cleaned > 0:
        print(f"Очищено {cleaned} просроченных админских сессий")


async def cancel_auth(update: Update, context: CallbackContext):
    """Отмена аутентификации"""
    await update.message.reply_text("❌ Аутентификация отменена")
    return ConversationHandler.END


async def show_admin_panel(update: Update, context: CallbackContext):
    """Показывает панель администратора"""
    # Клавиатура админ-панели
    ADMIN_KEYBOARD = [
        [ADMIN_BUTTONS["admin_user_stats"], ADMIN_BUTTONS["admin_recent_activity"]],
        [ADMIN_BUTTONS["admin_users"], ADMIN_BUTTONS["admin_backup"]],
        [ADMIN_BUTTONS["admin_broadcast"], ADMIN_BUTTONS["admin_system"]],
        [ADMIN_BUTTONS["admin_whoami"], ADMIN_BUTTONS["admin_logout"]]
    ]

    reply_markup = ReplyKeyboardMarkup(ADMIN_KEYBOARD, resize_keyboard=True)

    await update.message.reply_text(
        "👑 <b>Панель администратора</b>\n\n"
        "Выберите действие:",
        parse_mode=ParseMode.HTML,
        reply_markup=reply_markup
    )


async def handle_admin_buttons(update: Update, context: CallbackContext):
    """Обрабатывает нажатия кнопок в админ-панели"""
    user = update.effective_user

    if not is_admin(user.id):
        await update.message.reply_text("❌ Права администратора истекли",
                                        #parse_mode=ParseMode.HTML,
                                        reply_markup=ReplyKeyboardRemove()
        )
        revoke_admin_access(user.id)
        return

    text = update.message.text
    handler_name = ADMIN_BUTTONS_REVERSE.get(text)

    if handler_name:
        handler = globals().get(handler_name)
        if handler and callable(handler):
            await handler(update, context)
        else:
            await update.message.reply_text(
                f"❌ Обработчик {handler_name} не найден",
                parse_mode=ParseMode.HTML
            )
    else:
        await show_admin_panel(update, context)


async def admin_cmd(update: Update, context: CallbackContext):
    """Главная команда администратора"""
    user = update.effective_user

    if is_admin(user.id):
        await show_admin_panel(update, context)
        return

    # Запрашиваем пароль
    await update.message.reply_text(
        "🔐 <b>Введите пароль администратора:</b>",
        parse_mode=ParseMode.HTML
    )
    return AUTH_PASSWORD


async def auth_password(update: Update, context: CallbackContext):
    """Обработка ввода пароля"""
    user = update.effective_user
    password = update.message.text

    if authenticate_admin(password):
        grant_admin_access(user.id)
        await update.message.reply_text(
            "✅ <b>Доступ предоставлен!</b>\n"
            f"Права администратора активны до {time.strftime('%H:%M:%S', time.localtime(admin_sessions[user.id]['admin_until']))}",
            parse_mode=ParseMode.HTML
        )
        await show_admin_panel(update, context)
        return ConversationHandler.END
    else:
        await update.message.reply_text(
            "❌ <b>Неверный пароль</b>\n"
            "Попробуйте еще раз или отмените командой /cancel",
            parse_mode=ParseMode.HTML
        )
        return AUTH_PASSWORD


async def admin_whoami(update: Update, context: CallbackContext):
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


async def admin_broadcast(update: Update, context: CallbackContext):
    """Массовая рассылка"""
    if not is_admin(update.effective_user.id):
        return

    if context.args:
        message = " ".join(context.args)
        # ... код рассылки ...
    else:
        await update.message.reply_text(
            "📢 <b>Массовая рассылка</b>\n\n"
            "Использование: /broadcast Ваше сообщение",
            parse_mode=ParseMode.HTML
        )


async def admin_backup(update: Update, context: CallbackContext):
    """Создание резервных копий БД и логов"""
    if not is_admin(update.effective_user.id):
        return

    await update.message.reply_text("💾 <b>Создание резервных копий...</b>", parse_mode=ParseMode.HTML)

    try:
        # Создаем временную директорию если не существует
        from .constants import BACKUP_TMP_PATH, BACKUP_DB_FILES, BACKUP_LOG_PATTERN
        import glob

        tmp_dir = BACKUP_TMP_PATH
        os.makedirs(tmp_dir, exist_ok=True)

        # Текущая дата для имен файлов
        current_date = datetime.now().strftime("%Y%m%d_%H%M%S")

        # 1. Создаем архив с базами данных
        db_backup_path = os.path.join(tmp_dir, f"databases_backup_{current_date}.zip")

        db_files_exist = []
        for db_file in BACKUP_DB_FILES:
            if os.path.exists(db_file):
                db_files_exist.append(db_file)

        if db_files_exist:
            with zipfile.ZipFile(db_backup_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
                for db_file in db_files_exist:
                    zipf.write(db_file, os.path.basename(db_file))
            db_size = os.path.getsize(db_backup_path)
        else:
            db_backup_path = None
            db_size = 0

        # 2. Создаем архив с логами
        logs_backup_path = os.path.join(tmp_dir, f"logs_backup_{current_date}.zip")
        log_files = glob.glob(BACKUP_LOG_PATTERN)

        if log_files:
            with zipfile.ZipFile(logs_backup_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
                for log_file in log_files:
                    zipf.write(log_file, os.path.basename(log_file))
            logs_size = os.path.getsize(logs_backup_path)
        else:
            logs_backup_path = None
            logs_size = 0

        # Формируем отчет
        backup_text = f"""
💾 <b>Резервные копии созданы</b>

<b>Базы данных:</b>
{chr(10).join([f'• {os.path.basename(db)}' for db in db_files_exist]) if db_files_exist else '• Файлы БД не найдены'}
• Размер архива: {db_size / 1024:.1f} KB

<b>Логи:</b>
• Найдено файлов: {len(log_files)}
• Размер архива: {logs_size / 1024:.1f} KB
"""

        # Отправляем файлы если они созданы
        if db_backup_path and os.path.exists(db_backup_path):
            await update.message.reply_document(
                document=open(db_backup_path, 'rb'),
                filename=f"databases_backup_{current_date}.zip",
                caption="📊 Архив баз данных"
            )
            # Удаляем архив после отправки
            os.remove(db_backup_path)

        if logs_backup_path and os.path.exists(logs_backup_path):
            await update.message.reply_document(
                document=open(logs_backup_path, 'rb'),
                filename=f"logs_backup_{current_date}.zip",
                caption="📝 Архив логов"
            )
            # Удаляем архив после отправки
            os.remove(logs_backup_path)

        await update.message.reply_text(backup_text, parse_mode=ParseMode.HTML)

    except Exception as e:
        error_text = f"❌ <b>Ошибка при создании резервных копий:</b>\n{str(e)}"
        await update.message.reply_text(error_text, parse_mode=ParseMode.HTML)


async def admin_logout(update: Update, context: CallbackContext):
    """Выход из режима администратора"""
    revoke_admin_access(update.effective_user.id)
    await update.message.reply_text(
        "🚪 <b>Режим администратора завершен</b>",
        parse_mode=ParseMode.HTML,
        reply_markup=ReplyKeyboardRemove()
    )


async def admin_users(update: Update, context: CallbackContext):
    """Управление пользователями"""
    if not is_admin(update.effective_user.id):
        return

    # TODO: реализовать управление пользователями
    await update.message.reply_text(
        "👥 <b>Управление пользователями</b>\n\n"
        "Функция в разработке...",
        parse_mode=ParseMode.HTML
    )


async def admin_system(update: Update, context: CallbackContext):
    """Системные команды"""
    if not is_admin(update.effective_user.id):
        return

    # Получаем версию бота
    from .VERSION import __version__

    # Получаем системную статистику
    from .health import get_system_stats, get_memory_usage
    stats = get_system_stats()

    # Получаем информацию о текущих админских сессиях
    active_admins = len([uid for uid in admin_sessions if admin_sessions[uid]["admin_until"] > time.time()])
    cleaned_sessions = cleanup_expired_sessions()

    system_text = f"""
⚙️ <b>Системная информация</b>

<b>Версия бота:</b>
• Текущая версия: <code>{__version__}</code>

<b>Память:</b>
• Используется процессом: <code>{stats['memory_used']} MB</code>
• Используется системой: <code>{stats['memory_percent']}%</code>
• Загрузка CPU: <code>{stats['cpu_percent']}%</code>

<b>Процесс:</b>
• Открытых файлов: <code>{stats['open_files']}</code>
• Потоков: <code>{stats['threads']}</code>
• Время: <code>{stats['timestamp']}</code>

<b>Админские сессии:</b>
• Активных сессий: <code>{active_admins}</code>
• Очищено просроченных: <code>{cleaned_sessions}</code>
"""

    await update.message.reply_text(system_text, parse_mode=ParseMode.HTML)


async def admin_user_stats(update: Update, context: CallbackContext, from_callback=False):
    """Универсальная функция для показа статистики пользователей"""
    if from_callback:
        query = update.callback_query
        user = query.from_user
        message_func = query.edit_message_text
    else:
        query = update.callback_query
        user = update.effective_user
        message_func = update.message.reply_text

    if not is_admin(user.id):
        if from_callback:
            await query.edit_message_text("❌ Недостаточно прав")
        else:
            await update.message.reply_text("❌ Недостаточно прав")
        return

    # Получаем общую статистику
    stats = LOGS_REPO.get_user_stats_summary()

    # Получаем статистику по дням
    daily_stats = LOGS_REPO.get_daily_user_stats(7)

    # Получаем статистику по донатам
    payment_stats = LOGS_REPO.get_payment_stats(30)

    stats_text = f"""
📈 <b>Статистика пользователей</b>

👥 <b>Общая статистика:</b>
• Новых за неделю, месяц, всего: <code>{stats['new_users_week']:,}, {stats['new_users_month']:,}, {stats['total_users']:,}</code>
• Активных за неделю, месяц, всего: <code>{stats['active_users_week']:,}, {stats['active_users_month']:,}, {stats['active_users_total']:,}</code>

📊 <b>Активность</b>
• Поисковых запросов за неделю, месяц, всего: <code>{stats['searches_week']:,}, {stats['searches_month']:,}, {stats['searches_total']:,}</code>
• Скачиваний книг за неделю, месяц, всего: <code>{stats['downloads_week']:,}, {stats['downloads_month']:,}, {stats['downloads_total']:,}</code>

📅 <b>Статистика по дням (последние 7 дней):</b>
"""

    # Добавляем статистику по дням в виде таблицы
    stats_text += "\n<pre>"
    stats_text += "Дата      | Новые | Активные | Поиски | Скачивания\n"
    stats_text += "──────────┼───────┼──────────┼────────┼───────────\n"

    for i in range(len(daily_stats['dates'])):
        date = daily_stats['dates'][i]
        new_users = daily_stats['new_users'][i]
        active_users = daily_stats['active_users'][i]
        searches = daily_stats['searches'][i]
        downloads = daily_stats['downloads'][i]

        # Форматируем дату (только день.месяц)
        date_formatted = datetime.strptime(date, '%Y-%m-%d').strftime('%d.%m')

        stats_text += f"{date_formatted:9} | {new_users:5} | {active_users:8} | {searches:6} | {downloads:9}\n"

    stats_text += "</pre>"

    stats_text += f"""
    💰 <b>Статистика платежей (за 30 дней)</b>

    📊 <b>Общая статистика:</b>
    • Всего платежей: <code>{payment_stats['total_payments']}</code>
    • Общая сумма: <code>{payment_stats['total_amount']:.2f}</code>
    • Средний чек: <code>{payment_stats['avg_amount']:.2f}</code>
    • Уникальных доноров: <code>{payment_stats['unique_donors']}</code>
    """

    # Кнопки действий
    keyboard = [
        [InlineKeyboardButton("📋 Детальный список пользователей", callback_data="users_list:0")],
        [InlineKeyboardButton("🔍 Топ поисковых запросов", callback_data="top_searches")],
        [InlineKeyboardButton("📥 Топ скачиваний", callback_data="top_downloads")],
        [InlineKeyboardButton("📋 Список платежей", callback_data="payments_list:0")]
    ]

    reply_markup = InlineKeyboardMarkup(keyboard)

    # Используем правильный метод в зависимости от контекста
    await message_func(stats_text, parse_mode=ParseMode.HTML, reply_markup=reply_markup)


async def show_top_searches(query, context: CallbackContext):
    """Показывает топ поисковых запросов"""
    top_searches = LOGS_REPO.get_top_searches(15)

    searches_text = "🔍 <b>Топ поисковых запросов</b>\n\n"

    for i, search in enumerate(top_searches, 1):
        # Обрезаем длинные запросы
        query_text = search['query'][:50] + "..." if search['query'] and len(search['query']) > 50 else (search['query'] or 'N/A')

        searches_text += f"{i}. {query_text}\n"
        searches_text += f"   👥 {search['count']} раз ({search['unique_users']} пользователей)\n\n"

    keyboard = [[InlineKeyboardButton("⬅️ Назад в статистику", callback_data="back_to_stats")]]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await query.edit_message_text(searches_text, parse_mode=ParseMode.HTML, reply_markup=reply_markup)


PAYMENTS_PER_PAGE = 20


async def show_payments_list(query, context: CallbackContext, page=0):
    """Показывает список платежей с пагинацией"""
    total_payments = LOGS_REPO.get_payments_count()
    payments = LOGS_REPO.get_payments_list(PAYMENTS_PER_PAGE, page * PAYMENTS_PER_PAGE)

    payments_text = "💰 <b>Список платежей</b>\n\n"
    payments_text += f"Страница {page + 1} из {((total_payments - 1) // PAYMENTS_PER_PAGE) + 1 if total_payments > 0 else 1}\n\n"

    if not payments:
        payments_text += "Платежи не найдены."
    else:
        for payment in payments:
            status_emoji = "✅" if payment['payment_status'] == 'completed' else "⏳"
            payments_text += (
                f"{status_emoji} <b>{payment['username'] or 'Пользователь #' + str(payment['user_id'])}</b>\n"
                f"   💵 {payment['amount']} {payment['currency']}\n"
                f"   📅 {payment['payment_date']}\n"
                f"   🆔 {payment['payment_id']}\n\n"
            )

    keyboard = []
    if page > 0:
        keyboard.append([InlineKeyboardButton("⬅️ Назад", callback_data=f"payments_list:{page - 1}")])
    if (page + 1) * PAYMENTS_PER_PAGE < total_payments:
        keyboard.append([InlineKeyboardButton("Вперёд ➡️", callback_data=f"payments_list:{page + 1}")])
    keyboard.append([InlineKeyboardButton("⬅️ Назад в статистику", callback_data="back_to_stats")])

    reply_markup = InlineKeyboardMarkup(keyboard)

    await query.edit_message_text(payments_text, parse_mode=ParseMode.HTML, reply_markup=reply_markup)


async def admin_recent_activity(update: Update, context: CallbackContext):
    """Последняя активность"""
    if not is_admin(update.effective_user.id):
        await update.message.reply_text("❌ Недостаточно прав")
        return

    # Получаем последние действия
    activities = []
    recent_searches = LOGS_REPO.get_recent_searches(10)
    recent_downloads = LOGS_REPO.get_recent_downloads(10)

    activity_text = "🔍 <b>Последняя активность</b>\n\n"

    if recent_searches:
        activity_text += "📚 <b>Последние поиски:</b>\n"
        for search, timestamp, username in recent_searches:
            activity_text += f"• {username}: {search} ({timestamp})\n"
        activity_text += "\n"

    if recent_downloads:
        activity_text += "📥 <b>Последние скачивания:</b>\n"
        for filename, timestamp, username in recent_downloads:
            activity_text += f"• {username}: {filename} ({timestamp})\n"

    keyboard = [
        [InlineKeyboardButton("📋 Полный список пользователей", callback_data="users_list:0")],
        [InlineKeyboardButton("⬅️ Назад в статистику", callback_data="back_to_stats")]
    ]

    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_text(activity_text, parse_mode=ParseMode.HTML, reply_markup=reply_markup)


async def show_users_list(query, context: CallbackContext, page=0):
    """Показывает список пользователей"""
    users = LOGS_REPO.get_users_list(USERS_PER_PAGE, page * USERS_PER_PAGE)
    total_users = LOGS_REPO.get_user_stats_summary()['total_users']

    users_text = f"👥 <b>Список пользователей</b>\n\n"
    users_text += f"Страница {page + 1} из {((total_users - 1) // USERS_PER_PAGE) + 1}\n\n"

    keyboard = []

    for user in users:
        # Сокращаем информацию для кнопки
        user_info = f"{user['username']}"
        user_info += f" | 📅{user['first_seen'].split()[0]}"
        user_info += f" | 🔍{user['total_searches']} | 📥{user['total_downloads']}"

        keyboard.append([InlineKeyboardButton(
            user_info,
            callback_data=f"user_detail:{user['user_id']}"
        )])

    # Кнопки навигации
    nav_buttons = []
    if page > 0:
        nav_buttons.append(InlineKeyboardButton("⬅️ Назад", callback_data=f"users_list:{page - 1}"))
    if (page + 1) * USERS_PER_PAGE < total_users:
        nav_buttons.append(InlineKeyboardButton("Вперёд ➡️", callback_data=f"users_list:{page + 1}"))
    if nav_buttons:
        keyboard.append(nav_buttons)

    keyboard.append([InlineKeyboardButton("⬅️ Назад в статистику", callback_data="back_to_stats")])

    reply_markup = InlineKeyboardMarkup(keyboard)

    await query.edit_message_text(users_text, parse_mode=ParseMode.HTML, reply_markup=reply_markup)


async def show_user_detail(query, context: CallbackContext, user_id):
    """Показывает детальную информацию о пользователе"""
    # Получаем информацию о пользователе напрямую по ID
    user = LOGS_REPO.get_user_by_id(user_id)

    if not user:
        await query.edit_message_text("❌ Пользователь не найден")
        return

    # Получаем историю действий
    activities = LOGS_REPO.get_user_activity(user_id, 10)

    # Проверяем статус блокировки
    # user_settings = DB_SETTINGS.get_user_settings(user_id)
    user_settings = get_user_params(context)
    is_blocked = user_settings.IsBlocked

    user_text = f"👤 <b>Информация о пользователе</b>\n\n"
    user_text += f"<b>Имя:</b> {user['username']}\n"
    user_text += f"<b>ID:</b> {user_id}\n"
    user_text += f"<b>Первый визит:</b> {user['first_seen']}\n"
    user_text += f"<b>Последний визит:</b> {user['last_seen']}\n"
    user_text += f"<b>Всего поисков:</b> {user['total_searches']}\n"
    user_text += f"<b>Всего скачиваний:</b> {user['total_downloads']}\n"
    user_text += f"<b>Статус:</b> {'❌ Заблокирован' if is_blocked else '✅ Активен'}\n\n"

    user_text += "📋 <b>Последние действия:</b>\n"
    for activity in activities:
        event_type = activity.get('event_type', '')
        data_json = activity.get('data_json', '')

        # Parse data_json if available
        try:
            data = json.loads(data_json) if data_json else {}
        except (json.JSONDecodeError, TypeError):
            data = {}

        # Map event_type to human-readable description
        if event_type.startswith('search.'):
            search_query = data.get('query', '')
            action_desc = f"🔍 Поиск: {search_query}"
        elif event_type == 'book.download':
            book_title = data.get('book_title', '')
            action_desc = f"📥 Скачал: {book_title}"
        elif event_type == 'bot.start':
            action_desc = "🚀 Запустил бота"
        elif event_type == 'book.info.view':
            book_title = data.get('book_title', '')
            action_desc = f"📖 Просмотр книги: {book_title}"
        elif event_type == 'author.info.view':
            author_name = data.get('author_name', '')
            action_desc = f"👤 Просмотр автора: {author_name}"
        elif event_type == 'book.details.view':
            book_title = data.get('book_title', '')
            action_desc = f"📋 Детали книги: {book_title}"
        elif event_type == 'book.reviews.view':
             action_desc = "💬 Просмотр отзывов"
        elif event_type == 'settings.change':
            setting_name = data.get('setting_name', '')
            action_desc = f"⚙️ Изменение настроек: {setting_name}"
        elif event_type == 'settings.menu.view':
            action_desc = "⚙️ Просмотр меню настроек"
        elif event_type == 'settings.rating.view':
            action_desc = "⭐ Просмотр рейтингов"
        elif event_type == 'genres.view':
            action_desc = "📚 Просмотр жанров"
        elif event_type == 'csv.download':
            action_desc = "📥 Скачивание CSV"
        elif event_type == 'help.view':
            action_desc = "❓ Просмотр справки"
        elif event_type == 'about.view':
            action_desc = "ℹ️ Просмотр информации"
        elif event_type == 'news.view':
            action_desc = "📰 Просмотр новостей"
        elif event_type == 'donate.view':
            action_desc = "💰 Просмотр донатов"
        elif event_type == 'payment.received':
            payment_id = data.get('payment_id', '')
            amount = data.get('amount', '')
            currency = data.get('currency', '')
            action_desc = f"💳 Получен платёж: {amount} {currency} ({payment_id})"
        elif event_type == 'payment.refund':
            action_desc = "💸 Возврат платежа"
        elif event_type.startswith('error.'):
            action_desc = f"❌ Ошибка: {event_type}"
        elif event_type.startswith('system.'):
            action_desc = f"🔧 Системное: {event_type}"
        else:
            action_desc = event_type

        user_text += f"• {activity['timestamp']}: {action_desc}\n"

    keyboard = [
        [InlineKeyboardButton(
            "🚫 Заблокировать" if not is_blocked else "✅ Разблокировать",
            callback_data=f"toggle_block:{user_id}"
        )],
        [InlineKeyboardButton("⬅️ Назад к списку", callback_data="users_list:0")]
    ]

    reply_markup = InlineKeyboardMarkup(keyboard)

    await query.edit_message_text(user_text, parse_mode=ParseMode.HTML, reply_markup=reply_markup)


async def toggle_user_block(query, context: CallbackContext, user_id):
    """Блокирует/разблокирует пользователя с проверками"""
    # user_settings = DB_SETTINGS.get_user_settings(user_id)
    user_settings = get_user_params(context)
    current_block_status = user_settings.IsBlocked
    new_block_status = not current_block_status

    # Проверяем, не пытаемся ли заблокировать самого себя
    if user_id == query.from_user.id and new_block_status:
        await query.answer("❌ Нельзя заблокировать самого себя")
        return

    # Проверяем, не пытаемся ли заблокировать другого администратора
    if is_admin(user_id) and new_block_status:
        await query.answer("❌ Нельзя заблокировать администратора")
        return

    # DB_SETTINGS.update_user_settings(user_id, IsBlocked=new_block_status)
    update_user_params(context, IsBlocked=new_block_status)

    action = "заблокирован" if new_block_status else "разблокирован"
    await query.answer(f"Пользователь {action}")

    # Возвращаемся к деталям пользователя
    await show_user_detail(query, context, user_id)


async def show_recent_searches(query, context: CallbackContext):
    """Показывает последние поисковые запросы"""
    searches = LOGS_REPO.get_recent_searches(20)

    searches_text = "🔍 <b>Последние поисковые запросы</b>\n\n"

    for search, timestamp, username in searches:
        searches_text += f"<b>{username}</b> ({timestamp}):\n{search}\n\n"

    keyboard = [[InlineKeyboardButton("⬅️ Назад", callback_data="back_to_stats")]]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await query.edit_message_text(searches_text, parse_mode=ParseMode.HTML, reply_markup=reply_markup)


async def show_recent_downloads(query, context: CallbackContext):
    """Показывает последние скачивания"""
    downloads = LOGS_REPO.get_recent_downloads(20)

    downloads_text = "📥 <b>Последние скачивания</b>\n\n"

    for filename, timestamp, username in downloads:
        downloads_text += f"<b>{username}</b> ({timestamp}):\n{filename}\n\n"

    keyboard = [[InlineKeyboardButton("⬅️ Назад", callback_data="back_to_stats")]]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await query.edit_message_text(downloads_text, parse_mode=ParseMode.HTML, reply_markup=reply_markup)


async def show_top_downloads(query, context: CallbackContext):
    """Показывает топ скачанных книг"""
    top_downloads = LOGS_REPO.get_top_downloads(20)

    top_text = "🏆 <b>Топ скачанных книг</b>\n\n"

    for filename, count in top_downloads:
        top_text += f"<b>{count} раз</b>: {filename}\n"

    keyboard = [[InlineKeyboardButton("⬅️ Назад", callback_data="back_to_stats")]]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await query.edit_message_text(top_text, parse_mode=ParseMode.HTML, reply_markup=reply_markup)


async def handle_admin_callback(update: Update, context: CallbackContext):
    """Обработчик callback для админских действий"""
    query = update.callback_query
    await query.answer()

    data = query.data.split(':')
    action = data[0]

    try:
        if action == "users_list":
            page = int(data[1]) if len(data) > 1 else 0
            await show_users_list(query, context, page)

        elif action == "user_detail":
            user_id = int(data[1])
            await show_user_detail(query, context, user_id)

        elif action == "toggle_block":
            user_id = int(data[1])
            await toggle_user_block(query, context, user_id)

        elif action == "recent_searches":
            await show_recent_searches(query, context)

        elif action == "recent_downloads":
            await show_recent_downloads(query, context)

        elif action == "top_downloads":
            await show_top_downloads(query, context)

        elif action == "top_searches":
            await show_top_searches(query, context)

        elif action == "payments_list":
            page = int(data[1]) if len(data) > 1 else 0
            await show_payments_list(query, context, page)

        elif action == "back_to_stats":
            await admin_user_stats(update, context, from_callback=True)

        elif action == "refresh_stats":
            await admin_user_stats(update, context, from_callback=True)

    except Exception as e:
        print(f"Error in admin callback: {e}")
        await query.edit_message_text("❌ Произошла ошибка при обработке запроса")
