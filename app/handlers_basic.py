import os

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, CallbackQuery, LabeledPrice
from telegram.ext import CallbackContext
from telegram.constants import ParseMode

from .handlers_settings import show_settings_menu
from .tools import get_latest_news, get_platform_recommendations
from .constants import BOT_NEWS_FILE_PATH, SHOW_POPULAR_ALL_TIME, SHOW_POPULAR_30_DAYS, SHOW_POPULAR_7_DAYS, SHOW_NOVELTY
from .database import DB_BOOKS
from .core.structured_logger import structured_logger
from .health import log_stats
from .core.logging_schema import EventType

# ===== КОНСТАНТЫ И КОНФИГУРАЦИЯ =====
CONTACT_INFO = {'email': os.getenv("FEEDBACK_EMAIL", "не указан"),
                'blog': os.getenv("FEEDBACK_BLOG", ""), 'blog_name': os.getenv("FEEDBACK_BLOG_USERNAME", "не указан"),
                'tg_channel': os.getenv("FEEDBACK_TG_CHANNEL",""),'tg_channel_name': os.getenv("FEEDBACK_TG_CHANNEL_NAME","")
                }


# ===== КОМАНДЫ БОТА =====
async def start_cmd(update: Update, context: CallbackContext):
    """Обработка команды /start с deep linking"""
    user = update.effective_user

    #Вывод приглашения и помощи по поиску книг
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

    await log_stats(context)

    structured_logger.log_user_action(
        event_type=EventType.BOT_START,
        user_id=user.id,
        username=user.username or user.first_name or "Unknown",
        data={},
        chat_type="private",
        chat_id=user.id
    )

async def genres_cmd(update: Update, context: CallbackContext):
    """Показывает родительские жанры"""
    try:
        results = DB_BOOKS.get_parent_genres_with_counts()

        # print(f"DEBUG: genres_cmd results = {results}")
        # print(f"DEBUG: Number of results = {len(results)}")

        keyboard = []
        for genre_name, count in results:
            count_text = f"({count:,})".replace(","," ") if count else "(0)"
            button_text = f"{genre_name} {count_text}"
            genre_index = results.index((genre_name, count))
            keyboard.append([InlineKeyboardButton(button_text, callback_data=f"show_genres:{genre_index}")])

        # print(f"DEBUG: Keyboard has {len(keyboard)} rows")

        reply_markup = InlineKeyboardMarkup(keyboard)
        # print(f"DEBUG: Reply markup created")

        await update.message.reply_text(f"Посмотреть жанры:", reply_markup=reply_markup)
        # print(f"DEBUG: Message sent successfully")
    except Exception as e:
        await update.message.reply_text(f"❌ Ошибка при загрузке жанров")

    await log_stats(context)
    user = update.message.from_user
    structured_logger.log_user_action(
        event_type=EventType.GENRES_VIEW,
        user_id=user.id,
        username=user.username or user.first_name or "Unknown",
        data={},
        chat_type="private",
        chat_id=user.id
    )

async def pop_cmd(update: Update, context: CallbackContext):
    """Показывает варианты просмотра популярных книг и новинок публикаций"""
    keyboard = []
    keyboard.append([InlineKeyboardButton("Популярные за всё время", callback_data=f"{SHOW_POPULAR_ALL_TIME}")])
    keyboard.append([InlineKeyboardButton("Популярные за 30 дней", callback_data=f"{SHOW_POPULAR_30_DAYS}")])
    keyboard.append([InlineKeyboardButton("Популярные за 7 дней", callback_data=f"{SHOW_POPULAR_7_DAYS}")])
    keyboard.append([InlineKeyboardButton("Новинки", callback_data=f"{SHOW_NOVELTY}")])
    # add_close_button(keyboard)

    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_text(f"Посмотреть:", reply_markup=reply_markup)


# async def langs_cmd(update: Update, context: CallbackContext):
#     """Показывает доступные языки"""
#     results = DB_BOOKS.get_langs()
#     langs = ", ".join([f"<code>{lang[0].strip()}</code>" for lang in results])
#     await update.message.reply_text(
#         langs,
#         parse_mode=ParseMode.HTML,
#         disable_notification=True
#     )
#
#     await log_stats(context)
#     user = update.message.from_user
#     logger.log_user_action(user, "viewed langs of books")


async def settings_cmd(update: Update, context: CallbackContext):
    """Показывает главное меню настроек"""
    await show_settings_menu(update, context, from_callback=False)


async def donate_cmd(update: Update, context: CallbackContext):
    """Команда /donate с HTML сообщением"""
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

    user = update.message.from_user
    structured_logger.log_user_action(
        event_type=EventType.DONATE_VIEW,
        user_id=user.id,
        username=user.username or user.first_name or "Unknown",
        data={},
        chat_type="private",
        chat_id=user.id
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


async def help_cmd(update: Update, context: CallbackContext):
    """Команда помощи со списком всех команд"""
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

    user = update.message.from_user
    structured_logger.log_user_action(
        event_type=EventType.HELP_VIEW,
        user_id=user.id,
        username=user.username or user.first_name or "Unknown",
        data={},
        chat_type="private",
        chat_id=user.id
    )


async def about_cmd(update: Update, context: CallbackContext):
    """Команда /about - информация о боте и библиотеке"""
    try:
        stats = DB_BOOKS.get_library_stats()
        last_update = stats['last_update']
        last_update_str = last_update

        # print(f"DEBUG: {last_update}, {last_update_str}")

        reader_recommendations = get_platform_recommendations()

        about_text = f"""
<b>Flibusta Bot</b> - телеграм бот для поиска и скачивания книг непосредственно с сайта библиотеки Флибуста.

📊 <b>Статистика БД библиотеки бота:</b>
• 📚 Книг: <code>{f"{stats['books_count']:,}".replace(",", " ")}</code>
• 👥 Авторов: <code>{f"{stats['authors_count']:,}".replace(",", " ")}</code>
• 📖 Серий: <code>{f"{stats['series_count']:,}".replace(",", " ")}</code>
• 🏷️ Жанров: <code>{stats['genres_count']}</code>
• 🌐 Языков: <code>{stats['languages_count']}</code>
• 📅 Обновлено: <code>{last_update_str}</code>
• 🔢 Максимальный ID файла книги: <code>{stats['max_filename']}</code>

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
            parse_mode=ParseMode.HTML,
            disable_web_page_preview=True
        )

    except Exception as e:
        print(f"Error in about command: {e}")
        await update.message.reply_text(
            "❌ Не удалось получить информацию о библиотеке",
            parse_mode=ParseMode.HTML
        )

    await log_stats(context)

    user = update.message.from_user
    structured_logger.log_user_action(
        event_type=EventType.ABOUT_VIEW,
        user_id=user.id,
        username=user.username or user.first_name or "Unknown",
        data={},
        chat_type="private",
        chat_id=user.id
    )


async def news_cmd(update: Update, context: CallbackContext):
    """Команда /news - показывает последние новости бота"""
    try:
        # Загружаем новости из файла
        latest_news = await get_latest_news(BOT_NEWS_FILE_PATH, count=3)

        if not latest_news:
            await update.message.reply_text(
                "📢 Пока нет новостей. Следите за обновлениями!",
                parse_mode=ParseMode.HTML
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
            parse_mode=ParseMode.HTML,
            disable_web_page_preview=True
        )

        # Логируем действие
        user = update.message.from_user
        structured_logger.log_user_action(
            event_type=EventType.NEWS_VIEW,
            user_id=user.id,
            username=user.username or user.first_name or "Unknown",
            data={},
            chat_type="private",
            chat_id=user.id
        )

    except Exception as e:
        print(f"Error in news command: {e}")
        await update.message.reply_text(
            "❌ Не удалось загрузить новости",
            parse_mode=ParseMode.HTML
        )


# ===== ПЛАТЕЖИ =====
async def send_invoice(context, chat_id, title, description, payload, currency, prices):
    await context.bot.send_invoice(
            chat_id=chat_id,
            title=title,
            description=description,
            payload=payload,
            provider_token=None,  # Обязательно None для Stars
            currency=currency,
            prices=prices,
            start_parameter="donate"  # Добавляем start_parameter
            # need_name=False,
            # need_phone_number=False,
            # need_email=False,
            # need_shipping_address=False,
            # is_flexible=False
            # max_tip_amount=5000,  # Максимальное количество звезд
            # suggested_tip_amounts=[100, 500, 1000]  # Предлагаемые суммы
        )
