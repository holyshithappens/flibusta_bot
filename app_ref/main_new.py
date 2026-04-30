"""
Flibusta Bot - Новая архитектура (main_new.py)

Параллельная версия с новой архитектурой:
- Репозитории (BookRepository, UserRepository, LogsRepository)
- Сервисы (SearchService, BookService, UserService, AdminService)
- Обработчики (все 8 типов)
- Структурированное логирование
- Кеширование
- Полная типизация

Статус: Development/Testing
Версия: 1.1.0
"""

import os
import sys
from typing import Optional

# Добавляем путь для импорта модулей
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from telegram import BotCommand, Update
from telegram.ext import (
    Application, CommandHandler, MessageHandler, filters, 
    CallbackQueryHandler, ConversationHandler, CallbackContext,
    PreCheckoutQueryHandler
)
from telegram.request import HTTPXRequest
from telegram.error import Forbidden, BadRequest, TimedOut

# ===== ИМПОРТ НОВОЙ АРХИТЕКТУРЫ =====

# Репозитории
from .repositories.book_repository import BookRepository
from .repositories.user_repository import UserRepository
from .repositories.logs_repository import LogsRepository

# Сервисы
from .services.search_service import SearchService
from .services.book_service import BookService
from .services.user_service import UserService
from .services.admin_service import AdminService

# Обработчики
from .handlers.command_handlers import CommandHandlers
from .handlers.search_handlers import SearchHandlers
from .handlers.callback_handlers import CallbackHandlers
from .handlers.settings_handlers import SettingsHandlers
from .handlers.group_handlers import GroupHandlers
from .handlers.payment_handlers import PaymentHandlers
from .handlers.admin_handlers import AdminHandlers

# Логирование
from .core.structured_logger import StructuredLogger
from .core.logging_schema import EventType

# Ядро
from .core.context_manager import ContextManager

# ===== КОНФИГУРАЦИЯ =====

# Конфигурация MariaDB (для книг)
MARIADB_CONFIG = {
    'host': os.getenv('DB_HOST', 'localhost'),
    'user': os.getenv('DB_USER', 'flibusta'),
    'password': os.getenv('DB_PASSWORD', 'flibusta'),
    'database': os.getenv('DB_NAME', 'flibusta'),
    'charset': 'utf8mb3',
    'use_unicode': True,
    'connect_timeout': 60
}

# Путь к SQLite базам
SQLITE_DB_PATH = os.getenv('SQLITE_DB_PATH', 'data/FlibustaBot.sqlite')
LOGS_DB_PATH = os.getenv('LOGS_DB_PATH', 'data/FlibustaLogs.sqlite')

# Токен бота
BOT_TOKEN = os.getenv('BOT_TOKEN', '')


# ===== ГЛОБАЛЬНЫЕ ПЕРЕМЕННЫЕ =====

# Сервисы (будут инициализированы в main)
search_service: Optional[SearchService] = None
book_service: Optional[BookService] = None
user_service: Optional[UserService] = None
admin_service: Optional[AdminService] = None

# Обработчики
cmd_handlers: Optional[CommandHandlers] = None
search_handlers: Optional[SearchHandlers] = None
callback_handlers: Optional[CallbackHandlers] = None
settings_handlers: Optional[SettingsHandlers] = None
group_handlers: Optional[GroupHandlers] = None
payment_handlers: Optional[PaymentHandlers] = None
admin_handlers: Optional[AdminHandlers] = None

# Логгер
logger = StructuredLogger()


# ===== ИНИЦИАЛИЗАЦИЯ =====

def init_services() -> None:
    """
    Инициализация всех сервисов и репозиториев
    
    Порядок инициализации:
    1. Репозитории
    2. Сервисы
    3. Обработчики
    """
    global search_service, book_service, user_service, admin_service
    global cmd_handlers, search_handlers, callback_handlers
    global settings_handlers, group_handlers, payment_handlers, admin_handlers
    
    print("🚀 Инициализация новой архитектуры...")
    
    # 1. Репозитории
    print("  📦 Инициализация репозиториев...")
    book_repo = BookRepository(MARIADB_CONFIG)
    user_repo = UserRepository(SQLITE_DB_PATH)
    logs_repo = LogsRepository(LOGS_DB_PATH)
    
    # 2. Настройка логгера
    logger.set_db_logger(logs_repo)
    logger.log_system(
        EventType.SYSTEM_STARTUP,
        "New architecture initialization started",
        {"version": "1.1.0"}
    )
    
    # 3. Сервисы
    print("  ⚙️ Инициализация сервисов...")
    search_service = SearchService(book_repo, logger)
    book_service = BookService(book_repo, logger=logger)
    user_service = UserService(user_repo)
    admin_service = AdminService(user_repo, logs_repo, logger)
    
    # 4. Обработчики
    print("  🎯 Инициализация обработчиков...")
    
    # Команды
    cmd_handlers = CommandHandlers(
        search_service=search_service,
        book_service=book_service,
        user_service=user_service,
        admin_service=admin_service,
        logger=logger
    )
    
    # Поиск
    search_handlers = SearchHandlers(
        search_service=search_service,
        book_service=book_service,
        user_service=user_service,
        logger=logger
    )
    
    # Callback'и
    callback_handlers = CallbackHandlers(
        search_service=search_service,
        book_service=book_service,
        user_service=user_service,
        settings_handlers=None,  # Будет установлен после создания
        logger=logger
    )
    
    # Настройки
    settings_handlers = SettingsHandlers(
        user_service=user_service,
        book_service=book_service,
        logger=logger
    )
    
    # Инжектируем settings_handlers в callback_handlers
    callback_handlers.settings_handlers = settings_handlers
    
    # Группы
    group_handlers = GroupHandlers(
        search_service=search_service,
        book_service=book_service,
        user_service=user_service,
        logger=logger
    )
    
    # Платежи
    payment_handlers = PaymentHandlers(
        user_service=user_service,
        logger=logger
    )
    
    # Админка
    admin_handlers = AdminHandlers(
        admin_service=admin_service,
        user_service=user_service,
        logger=logger
    )
    
    print("✅ Инициализация завершена!")


# ===== ОБРАБОТЧИКИ ОШИБОК =====

async def error_handler(update: Update, context: CallbackContext) -> None:
    """Глобальный обработчик ошибок"""
    error = context.error
    
    # Пользователь заблокировал бота
    if isinstance(error, Forbidden) and "bot was blocked by the user" in str(error):
        user_id = update.effective_user.id if update.effective_user else 'Unknown'
        print(f"Пользователь заблокировал бота: {user_id}")
        logger.log_error(
            "user_blocked_bot",
            str(error),
            {"user_id": user_id}
        )
        return
    
    # Устаревший callback query
    if isinstance(error, BadRequest) and "Query is too old" in str(error):
        print(f"Устаревший callback query: {error}")
        return
    
    # Таймаут
    if isinstance(error, TimedOut):
        print(f"Таймаут запроса: {error}")
        logger.log_error(
            "timeout_error",
            str(error),
            {"update": str(update)[:200] if update else None}
        )
        return
    
    # Другие ошибки
    print(f"❌ Необработанная ошибка: {error}")
    if update and update.effective_user:
        print(f"User: {update.effective_user.id}")
    
    logger.log_error(
        "unhandled_error",
        str(error),
        {
            "update": str(update)[:200] if update else None,
            "user_id": update.effective_user.id if update.effective_user else None
        },
        user_id=update.effective_user.id if update.effective_user else None,
        username=update.effective_user.username if update.effective_user else None
    )


# ===== УСТАНОВКА КОМАНД =====

async def set_commands(application: Application) -> None:
    """Устанавливает меню команд"""
    commands = [
        BotCommand("start", "Запустить бота"),
        BotCommand("news", "Новости и обновления"),
        BotCommand("about", "Инфа о боте и библиотеке"),
        BotCommand("help", "Помощь по запросам"),
        BotCommand("genres", "Список жанров"),
        BotCommand("pop", "Популярные и новинки"),
        BotCommand("set", "Настройки поиска"),
        BotCommand("donate", "Поддержать разработчика")
        # BotCommand("admin", "Админ-панель")
    ]
    await application.bot.set_my_commands(commands)
    print("✅ Меню команд установлено")


# ===== ПЕРИОДИЧЕСКИЕ ЗАДАЧИ =====

async def cleanup_task(context: CallbackContext) -> None:
    """Периодическая очистка кеша и сессий"""
    try:
        # Очистка кеша
        if book_service:
            cleaned = book_service.book_repo.cleanup_cache()
            if cleaned > 0:
                print(f"🧹 Очищено {cleaned} записей из кеша")
        
        # Очистка старых сессий
        cleaned_private, cleaned_group = ContextManager.cleanup_inactive_sessions(
            context.application, 
            3600  # 1 час
        )
        if cleaned_private > 0 or cleaned_group > 0:
            print(f"🧹 Очищено {cleaned_private} приватных и {cleaned_group} групповых сессий")
            
    except Exception as e:
        print(f"Ошибка в cleanup_task: {e}")


# ===== ОСНОВНАЯ ФУНКЦИЯ =====

def main():
    """Основная функция запуска бота с новой архитектурой"""
    
    # Проверка токена
    if not BOT_TOKEN:
        raise ValueError("❌ Токен бота не найден в переменной окружения BOT_TOKEN")
    
    # Инициализация сервисов
    try:
        init_services()
    except Exception as e:
        print(f"❌ Ошибка инициализации: {e}")
        import traceback
        traceback.print_exc()
        return
    
    # Создание приложения
    print("\n🔄 Создание Telegram приложения...")
    request = HTTPXRequest(connect_timeout=60, read_timeout=60)
    application = Application.builder().token(BOT_TOKEN).request(request).build()
    
    # Регистрация обработчика ошибок
    application.add_error_handler(error_handler)
    
    # ===== РЕГИСТРАЦИЯ ОБРАБОТЧИКОВ =====
    
    print("📝 Регистрация обработчиков...")
    
    # 1. Команды (CommandHandlers)
    application.add_handler(CommandHandler("start", cmd_handlers.start_cmd))
    application.add_handler(CommandHandler("help", cmd_handlers.help_cmd))
    application.add_handler(CommandHandler("about", cmd_handlers.about_cmd))
    application.add_handler(CommandHandler("news", cmd_handlers.news_cmd))
    application.add_handler(CommandHandler("genres", cmd_handlers.genres_cmd))
    application.add_handler(CommandHandler("pop", cmd_handlers.pop_cmd))
    application.add_handler(CommandHandler("set", settings_handlers.set_cmd))
    application.add_handler(CommandHandler("donate", payment_handlers.donate_cmd))
    
    # 2. Поиск (SearchHandlers)
    application.add_handler(MessageHandler(
        filters.ChatType.PRIVATE & filters.TEXT & ~filters.COMMAND, 
        search_handlers.handle_message
    ))
    
    # 3. Callback'и (CallbackHandlers)
    application.add_handler(CallbackQueryHandler(callback_handlers.handle_callback))
    
    # 4. Групповые чаты (GroupHandlers)
    application.add_handler(MessageHandler(
        filters.ChatType.GROUP & filters.TEXT, 
        group_handlers.handle_group_message
    ))
    application.add_handler(CallbackQueryHandler(group_handlers.handle_group_callback, pattern="^group_"))
    
    # 5. Настройки (SettingsHandlers) - простой CallbackQueryHandler
    # SettingsHandlers использует единый обработчик handle_settings_callback
    application.add_handler(CallbackQueryHandler(
        settings_handlers.handle_settings_callback,
        pattern="^(settings:|set_|toggle_rating_|reset_ratings|back_to_settings|close_message)"
    ))
    
    # 6. Платежи (PaymentHandlers)
    application.add_handler(PreCheckoutQueryHandler(payment_handlers.pre_checkout_handler))
    application.add_handler(MessageHandler(filters.SUCCESSFUL_PAYMENT, payment_handlers.successful_payment_handler))
    
    # 7. Админка (AdminHandlers) - ConversationHandler
    admin_conv = admin_handlers.get_conversation_handler()
    application.add_handler(admin_conv)
    
    # Также добавляем callback handler для админских callback'ов
    application.add_handler(CallbackQueryHandler(admin_handlers.handle_callback, pattern="^(users_list|user_detail|toggle_block|back_to_stats|show_system_info)"))
    
    # ===== ПЕРИОДИЧЕСКИЕ ЗАДАЧИ =====
    
    print("⏰ Настройка периодических задач...")
    job_queue = application.job_queue
    
    if job_queue:
        # Очистка каждые 30 минут
        job_queue.run_repeating(
            cleanup_task, 
            interval=1800,  # 30 минут
            first=60  # через 1 минуту после старта
        )
        print("  ✅ Задача очистки добавлена")
    
    # Установка команд
    application.post_init = set_commands
    
    # Запуск
    application.run_polling()


# ===== ТОЧКА ВХОДА =====

if __name__ == '__main__':
    main()