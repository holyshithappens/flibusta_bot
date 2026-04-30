"""
Обработчики команд Telegram
"""
import os
import sys
import importlib.util
from typing import List, Dict, Any, Tuple, Optional

from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton, LabeledPrice
from telegram.ext import CallbackContext
from telegram.constants import ParseMode
from datetime import datetime

from ..services.search_service import SearchService, SearchParams
from ..services.book_service import BookService
from ..services.user_service import UserService
from ..services.admin_service import AdminService
from ..core.structured_logger import StructuredLogger
from ..core.logging_schema import EventType
from ..core import (
    SHOW_POPULAR_ALL_TIME, SHOW_POPULAR_30_DAYS,
    SHOW_POPULAR_7_DAYS, SHOW_NOVELTY
)

# ===== КОНСТАНТЫ И КОНФИГУРАЦИЯ (как в старой архитектуре) =====
CONTACT_INFO = {
    'email': os.getenv("FEEDBACK_EMAIL", "не указан"),
    'blog': os.getenv("FEEDBACK_BLOG", ""),
    'blog_name': os.getenv("FEEDBACK_BLOG_USERNAME", "не указан"),
    'tg_channel': os.getenv("FEEDBACK_TG_CHANNEL", ""),
    'tg_channel_name': os.getenv("FEEDBACK_TG_CHANNEL_NAME", "")
}

# Путь к файлу с новостями
BOT_NEWS_FILE_PATH = "./data/bot_news.py"


# ===== ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ =====


def get_platform_recommendations() -> str:
    """
    Возвращает рекомендации для всех платформ
    (универсальный подход, так как определить платформу сложно)
    """
    return """
📱 <b>Рекомендуемые читалки для всех платформ:</b>
<u>Для Android:</u>
• 📖 <a href="https://play.google.com/store/apps/details?id=org.readera">ReadEra</a> - лучшая бесплатная
• 📚 <a href="https://play.google.com/store/apps/details?id=com.flyersoft.moonreader">Moon+ Reader</a>
• 🔥 <a href="https://play.google.com/store/apps/details?id=com.amazon.kindle">Kindle</a>

<u>Для iOS:</u>
• 📖 <a href="https://apps.apple.com/ru/app/readera-читалка-книг-pdf/id1441824222">ReadEra</a>
• 📚 <a href="https://apps.apple.com/ru/app/kybook-3-ebook-reader/id1259787028">KyBook 3</a>
• 🔥 <a href="https://apps.apple.com/ru/app/amazon-kindle/id302584613">Kindle</a>

<u>Для компьютера:</u>
• 📚 <a href="https://www.calibre-ebook.com/">Calibre</a> (Windows/Mac/Linux)
• 📘 <a href="https://apps.apple.com/ru/app/apple-books/id364709193">Apple Books</a> (Mac)
• 📖 <a href="https://www.amazon.com/b?node=16571048011">Kindle</a> (все платформы)
"""


async def send_invoice(context, chat_id, title, description, payload, currency, prices):
    """Отправляет инвойс для оплаты Telegram Stars"""
    await context.bot.send_invoice(
        chat_id=chat_id,
        title=title,
        description=description,
        payload=payload,
        provider_token=None,  # Обязательно None для Stars
        currency=currency,
        prices=prices,
        start_parameter="donate"
    )


# ===== ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ ДЛЯ НОВОСТЕЙ =====


async def load_bot_news(file_path: str) -> List[Dict[str, Any]]:
    """Загружает новости бота из Python файла (как в старой архитектуре)"""
    try:
        # Принудительно удаляем модуль из кэша, если он уже был загружен
        if "bot_news" in sys.modules:
            del sys.modules["bot_news"]

        # Динамически импортируем модуль с новостями
        spec = importlib.util.spec_from_file_location("bot_news", file_path)
        if spec is None or spec.loader is None:
            return []

        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)

        # Получаем список новостей
        if hasattr(module, 'BOT_NEWS'):
            return module.BOT_NEWS
        elif hasattr(module, 'news'):
            return module.news
        else:
            return []
    except Exception as e:
        print(f"Error loading news: {e}")
        return []


async def get_latest_news(file_path: str, count: int = 3) -> List[Dict[str, Any]]:
    """Возвращает последние count новостей"""
    all_news = await load_bot_news(file_path)
    return all_news[-count:] if all_news else []


class CommandHandlers:
    """
    Обработчики текстовых команд
    
    Команды:
    /start - Приветствие
    /help - Справка
    /about - О боте
    /news - Новости
    /genres - Жанры
    /pop - Популярное
    /set - Настройки
    /donate - Поддержка
    """
    
    def __init__(
        self,
        search_service: SearchService,
        book_service: BookService,
        user_service: UserService,
        admin_service: AdminService,
        logger: StructuredLogger
    ):
        self.search_service = search_service
        self.book_service = book_service
        self.user_service = user_service
        self.admin_service = admin_service
        self.logger = logger
    
    async def start_cmd(self, update: Update, context: CallbackContext) -> None:
        """Команда /start с deep linking (как в старой архитектуре)"""
        user = update.effective_user

        # Проверка блокировки
        if self.user_service.is_user_blocked(user.id):
            await update.message.reply_text(
                "❌ Вы заблокированы и не можете использовать бота.",
                parse_mode=ParseMode.HTML
            )
            return

        # Инициализация пользователя
        settings = self.user_service.get_user_settings(user.id)

        # Вывод приглашения и помощи по поиску книг (как в старой архитектуре)
        welcome_text = """
📚 <b>Привет! Я помогу тебе искать и скачивать книги непосредственно из библиотеки Флибуста.</b> 

<u>Управление</u>
/news - новости и обновления бота
/about - информация о боте и библиотеке 
/help - помощь в составлении поисковых запросов
/genres - посмотреть доступные жанры
/pop - популярные книги и новинки библиотеки
/set - установка настроек поиска и вывода книг
/donate - поддержать разработчика
    """

        await update.message.reply_text(welcome_text, parse_mode='HTML', disable_web_page_preview=True)

        # Логирование
        self.logger.log_user_action(
            EventType.BOT_START, user.id, user.username or user.first_name or "Unknown", {}
        )
    
    async def help_cmd(self, update: Update, context: CallbackContext) -> None:
        """Команда помощи со списком всех команд (как в старой архитектуре)"""
        user = update.effective_user

        if self.user_service.is_user_blocked(user.id):
            return

        help_text = """
    <b>Помощь в поиске книг.</b>

    <u>Простой поиск по любым словам:</u>
    ✏️ <code>Лев Толстой война мир</code>
    ✏️ <code>фантастика космос звёзды 2025</code>
    ✏️ <code>Harry Potter</code>
    ✏️ <code>Перельман математика физика</code>

    <u>Советы для эффективного поиска:</u>
    🔍 <b>Несколько слов</b> - бот ищет книги, содержащие какие-либо из перечисленных слов
    ➕ <b>Обязательное слово</b> - используйте + перед словом: <code>+жизнь +замечательных людей</code>
    ➖ <b>Исключение слов</b> - используйте - перед словом: <code>+Распутин -Валентин</code>
    ⭐️ <b>Части слов</b> - можно использовать *: <code>математи* задач*</code>
    🔄 <b>Группировка слов</b> - используйте (): <code>+(эльф гоблин орк гном) +(одинокий злой грустный огромный)</code>
    📏 <b>Расстояние между словами</b> - используйте @N после фразы в двойных кавычках: <code>"настоящее время проживает Москве" @5</code>
    🔎 <b>Поиск по аннотациям</b> - в настройках включите "Область поиска" → "по аннотации книг" или "по аннотации авторов"

    <u>Область поиска:</u>
    📖 Основной поиск осуществляется по: <b>названию книги, авторам, жанрам, серии и году издания</b>
    📚 Поиск по аннотациям - по <b>полным текстам описаний книг или биографиям авторов</b>. Выполнена индексация слов от трёх букв

    <u>Примеры запросов для поиска по аннотациям книг:</u>
    📘 <code>+(эльфы гномы орки) +(злые одинокие большие грустные)</code> - фэнтези миры с магией
    📘 <code>+(путешествия вторжения пришельцев) +(космические времени другие миры)</code> - космическая фантастика
    📘 <code>+автор +создал удивительный волшебный +мир</code> - книги с богатым миром
    📘 <code>+русский +полководец Отечественной войны</code> - историческая литература
    📘 <code>+сборник +фантастических +(рассказов повестей) +советских -(зарубежных иностранных)</code> - советская фантастика

    <u>Примеры запросов для поиска по аннотациям авторов:</u>
    👤 <code>+награждён +(медалями орденами)</code> - авторы, награжденные медалями или орденами
    👤 <code>"умер 1980 году" @5</code> - авторы, умершие в 1980 году (слова в пределах 5 слов друг от друга)
    👤 <code>+(родился проживал умер) +Пензенской +губернии</code> - авторы, связанные с Пензенской губернией
    👤 <code>+филолог +переводчик +журналист</code> - авторы-филологи, переводчики и журналисты
    👤 <code>"настоящее время проживает Москве" @5</code> - ныне живущие в Москве авторы
    👤 <code>"воевал получил ранение" @10</code> - авторы, получившие ранения в боях

    <u>Ограничение выдачи:</u>
    ⚡️ Результаты поиска временно ограничены <b>2000 книгами, 200 авторами и 200 сериями</b> для скорости работы

    <u>Доступные форматы выдачи (в настройках):</u>
    📚 <b>По книгам</b> - список книг
    👥 <b>По авторам</b> - группировка по авторам
    📖 <b>По сериям</b> - группировка по сериям
    """

        await update.message.reply_text(help_text, parse_mode='HTML', disable_web_page_preview=True)

        self.logger.log_user_action(
            EventType.HELP_VIEW, user.id, user.username or user.first_name or "Unknown", {}
        )
    
    
    async def about_cmd(self, update: Update, context: CallbackContext) -> None:
        """Команда /about - информация о боте и библиотеке (как в старой архитектуре)"""
        user = update.effective_user

        if self.user_service.is_user_blocked(user.id):
            return

        try:
            # Получаем статистику
            stats = self.book_service.get_library_stats()
            last_update = stats.get('last_update', 'неизвестно')
            last_update_str = last_update

            reader_recommendations = get_platform_recommendations()

            about_text = f"""
<b>Flibusta Bot</b> - телеграм бот для поиска и скачивания книг непосредственно с сайта библиотеки Флибуста.

📊 <b>Статистика БД библиотеки бота:</b>
• 📚 Книг: <code>{f"{stats.get('books_count', 0):,}".replace(",", " ")}</code>
• 👥 Авторов: <code>{f"{stats.get('authors_count', 0):,}".replace(",", " ")}</code>
• 📖 Серий: <code>{f"{stats.get('series_count', 0):,}".replace(",", " ")}</code>
• 🏷️ Жанров: <code>{stats.get('genres_count', 0)}</code>
• 🌐 Языков: <code>{stats.get('languages_count', 0)}</code>
• 📅 Обновлено: <code>{last_update_str}</code>
• 🔢 Максимальный ID файла книги: <code>{stats.get('max_filename', 0)}</code>

⚡ <b>Возможности бота:</b>
• 🔍 Основной поиск книг по названию, автору, жанру, серии и году
• 📝 Поиск по аннотациям книг и авторов
• 📈 Просмотр новинок и популярных книг
• 📚 Вывод результатов с группировкой по сериям и авторам
• 👤 Детальная информация об авторах с фото и биографией
• 📖 Аннотации к книгам, авторам и отзывы читателей
• 🖼️ Обложки книг и фото авторов с сайта Флибуста
• 📥 Скачивание в форматах fb2, epub, mobi
• ⭐ Фильтрация по рейтингу книг, размеру и языку
• ⚙️ Гибкие настройки поиска
{reader_recommendations}
📞 <b>Обратная связь:</b>
• 📧 Email: <code>{CONTACT_INFO['email']}</code>
• 🎮 Блог: <a href="{CONTACT_INFO['blog']}">{CONTACT_INFO['blog_name']}</a>
• 📢 ТГ-канал: <a href="{CONTACT_INFO['tg_channel']}">{CONTACT_INFO['tg_channel_name']}</a>

🛠 <b>Технологии:</b>
• Python 3.11 + python-telegram-bot
• MariaDB + родная БД Флибусты
        """

            await update.message.reply_text(
                about_text,
                parse_mode='HTML',
                disable_web_page_preview=True
            )

        except Exception as e:
            print(f"Error in about command: {e}")
            await update.message.reply_text(
                "❌ Не удалось получить информацию о библиотеке",
                parse_mode='HTML'
            )

        self.logger.log_user_action(
            EventType.ABOUT_VIEW, user.id, user.username or user.first_name or "Unknown", {}
        )
    
    async def news_cmd(self, update: Update, context: CallbackContext) -> None:
        """Команда /news - показывает последние новости бота (как в старой архитектуре)"""
        user = update.effective_user

        if self.user_service.is_user_blocked(user.id):
            return

        try:
            # Загружаем новости из файла (как в старой архитектуре)
            latest_news = await get_latest_news(BOT_NEWS_FILE_PATH, count=3)

            if not latest_news:
                await update.message.reply_text(
                    "📢 Пока нет новостей. Следите за обновлениями!",
                    parse_mode='HTML'
                )
                return

            news_text = "📢 <b>Последние новости бота:</b>\n\n"

            for i, news_item in enumerate(latest_news, 1):
                news_text += f"📅 <b>{news_item['date']}</b>\n"
                news_text += f"<b>{news_item['title']}</b>\n"
                news_text += f"{news_item['content']}\n"

                # Добавляем разделитель между новостями (кроме последней)
                if i < len(latest_news):
                    news_text += "─" * 18 + "\n\n"

            await update.message.reply_text(
                news_text,
                parse_mode='HTML',
                disable_web_page_preview=True
            )

            # Логируем действие
            self.logger.log_user_action(
                EventType.NEWS_VIEW, user.id, user.username or user.first_name or "Unknown", {}
            )

        except Exception as e:
            print(f"Error in news command: {e}")
            await update.message.reply_text(
                "❌ Не удалось загрузить новости",
                parse_mode='HTML'
            )
    
    async def genres_cmd(self, update: Update, context: CallbackContext) -> None:
        """Команда /genres - показывает родительские жанры с кнопками"""
        user = update.effective_user
        
        if self.user_service.is_user_blocked(user.id):
            return
        
        try:
            # Получаем родительские жанры с количеством книг
            results = await self.book_service.get_parent_genres_with_counts()
            
            if not results:
                await update.message.reply_text(
                    "❌ Не удалось загрузить список жанров",
                    parse_mode=ParseMode.HTML
                )
                return
            
            # Создаем клавиатуру с кнопками
            from telegram import InlineKeyboardMarkup, InlineKeyboardButton
            
            keyboard = []
            for genre_name, count in results:
                # Форматируем количество с пробелами вместо запятых
                count_text = f"({count:,})".replace(",", " ") if count else "(0)"
                button_text = f"{genre_name} {count_text}"
                genre_index = results.index((genre_name, count))
                keyboard.append([InlineKeyboardButton(button_text, callback_data=f"show_genres:{genre_index}")])
            
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await update.message.reply_text(
                "Посмотреть жанры:",
                reply_markup=reply_markup,
                parse_mode=ParseMode.HTML
            )
            
            self.logger.log_user_action(
                EventType.GENRES_VIEW, user.id, user.username, {"action": "genres"}
            )
            
        except Exception as e:
            await update.message.reply_text(
                "❌ Ошибка при загрузке жанров",
                parse_mode=ParseMode.HTML
            )
            self.logger.log_error(
                "genres_error", str(e), {"action": "genres"}, user.id, user.username
            )
    
    async def pop_cmd(self, update: Update, context: CallbackContext) -> None:
        """Команда /pop - Популярное и новинки (как в старой архитектуре)"""
        user = update.effective_user
        
        if self.user_service.is_user_blocked(user.id):
            return
        
        # Клавиатура для выбора (идентично старой архитектуре)
        keyboard = []
        keyboard.append([InlineKeyboardButton("Популярные за всё время", callback_data=SHOW_POPULAR_ALL_TIME)])
        keyboard.append([InlineKeyboardButton("Популярные за 30 дней", callback_data=SHOW_POPULAR_30_DAYS)])
        keyboard.append([InlineKeyboardButton("Популярные за 7 дней", callback_data=SHOW_POPULAR_7_DAYS)])
        keyboard.append([InlineKeyboardButton("Новинки", callback_data=SHOW_NOVELTY)])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(f"Посмотреть:", reply_markup=reply_markup)
        
        self.logger.log_user_action(
            EventType.SEARCH_POPULAR, user.id, user.username, {"action": "popular_menu"}
        )
    
    async def set_cmd(self, update: Update, context: CallbackContext) -> None:
        """Команда /set - Настройки (перенаправление в SettingsHandlers)"""
        # Импортируем здесь, чтобы избежать циклических зависимостей
        from ..handlers.settings_handlers import SettingsHandlers
        
        # Создаем экземпляр SettingsHandlers
        settings_handlers = SettingsHandlers(
            user_service=self.user_service,
            book_service=self.book_service,
            logger=self.logger
        )
        
        # Перенаправляем обработку
        await settings_handlers.set_cmd(update, context)
    
    async def donate_cmd(self, update: Update, context: CallbackContext) -> None:
        """Команда /donate с HTML сообщением (как в старой архитектуре)"""
        user = update.effective_user

        if self.user_service.is_user_blocked(user.id):
            return

        # Адреса из переменных окружения (как в старой архитектуре)
        addresses = {
            '₿ Bitcoin (BTC)': os.getenv('DONATE_BTC'),
            'Ξ Ethereum & Poligon (ETH & POL)': os.getenv('DONATE_ETH'),
            '◎ Solana (SOL & USDC)': os.getenv('DONATE_SOL'),
            '🔵 Sui (SUI)': os.getenv('DONATE_SUI'),
            '₮ Toncoin (TON & USDT)': os.getenv('DONATE_TON'),
            '🔴 Tron (TRX & USDT)': os.getenv('DONATE_TRX')
        }

        donate_html = "💰 <b>Поддержать разработчика крипто-копеечкой</b>"
        for crypto_name, address in addresses.items():
            if address:
                donate_html += f"\n{crypto_name}:\n<code>{address}</code>\n"

        await update.message.reply_text(
            donate_html,
            parse_mode=ParseMode.HTML,
            disable_web_page_preview=True
        )

        self.logger.log_user_action(
            EventType.DONATE_VIEW, user.id, user.username or user.first_name or "Unknown", {}
        )

        try:
            chat_id = update.message.chat_id
            title = "Поддержать разработчика"
            payload = "donation-payload"
            currency = "XTR"  # Telegram Stars

            descr_5 = "Так, просто так!"
            prices_5 = [LabeledPrice("5 звёзд", 5),]
            await send_invoice(context, chat_id, title, descr_5, payload, currency, prices_5)
            descr_50 = "Примерно неделя аренды текущего VPS"
            prices_50 = [LabeledPrice("50 звезда", 50),]
            await send_invoice(context, chat_id, title, descr_50, payload, currency, prices_50)
            descr_200 = "Примерно месяц аренды текущего VPS"
            prices_200 = [LabeledPrice("200 звёзд", 200),]
            await send_invoice(context, chat_id, title, descr_200, payload, currency, prices_200)
            descr_1200 = "Примерно полгода аренды текущего VPS"
            prices_1200 = [LabeledPrice("1200 звёзд", 1200),]
            await send_invoice(context, chat_id, title, descr_1200, payload, currency, prices_1200)

        except Exception as e:
            print(f"Ошибка при создании инвойса: {e}")
            await update.message.reply_text("Произошла ошибка при создании платежа")
