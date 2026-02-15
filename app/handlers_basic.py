import os

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, LabeledPrice
from telegram.ext import CallbackContext
from telegram.constants import ParseMode

from .handlers_settings import show_settings_menu
from .tools import get_latest_news, get_platform_recommendations
from .constants import BOT_NEWS_FILE_PATH, SHOW_POPULAR_ALL_TIME, SHOW_POPULAR_30_DAYS, SHOW_POPULAR_7_DAYS, SHOW_NOVELTY
from .database import DB_BOOKS
from .core.structured_logger import structured_logger
from .health import log_stats
from .core.logging_schema import EventType
from .i18n import t, get_or_detect_locale

# ===== КОНСТАНТЫ И КОНФИГУРАЦИЯ =====
CONTACT_INFO = {'email': os.getenv("FEEDBACK_EMAIL", "не указан"),
                'blog': os.getenv("FEEDBACK_BLOG", ""), 'blog_name': os.getenv("FEEDBACK_BLOG_USERNAME", "не указан"),
                'tg_channel': os.getenv("FEEDBACK_TG_CHANNEL",""),'tg_channel_name': os.getenv("FEEDBACK_TG_CHANNEL_NAME","")
                }


# ===== КОМАНДЫ БОТА =====
async def start_cmd(update: Update, context: CallbackContext):
    """Обработка команды /start с deep linking"""
    user = update.effective_user

    # Initialize locale (auto-detect if needed)
    get_or_detect_locale(update, context)

    # Get localized welcome message
    welcome_text = t('welcome.title', context)
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
    # Initialize locale (auto-detect if needed)
    get_or_detect_locale(update, context)
    
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

        title = t('genres.title', context)
        await update.message.reply_text(title, reply_markup=reply_markup)
        # print(f"DEBUG: Message sent successfully")
    except Exception as e:
        error_msg = t('genres.error', context)
        await update.message.reply_text(error_msg)

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
    # Initialize locale (auto-detect if needed)
    get_or_detect_locale(update, context)
    
    keyboard = []
    keyboard.append([InlineKeyboardButton(t('popular.all_time', context), callback_data=f"{SHOW_POPULAR_ALL_TIME}")])
    keyboard.append([InlineKeyboardButton(t('popular.days_30', context), callback_data=f"{SHOW_POPULAR_30_DAYS}")])
    keyboard.append([InlineKeyboardButton(t('popular.days_7', context), callback_data=f"{SHOW_POPULAR_7_DAYS}")])
    keyboard.append([InlineKeyboardButton(t('popular.novelty', context), callback_data=f"{SHOW_NOVELTY}")])
    # add_close_button(keyboard)

    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_text(t('popular.title', context), reply_markup=reply_markup)


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
    # Initialize locale (auto-detect if needed)
    get_or_detect_locale(update, context)
    
    addresses = {
        '₿ Bitcoin (BTC)': os.getenv('DONATE_BTC'),
        'Ξ Ethereum & Poligon (ETH & POL)': os.getenv('DONATE_ETH'),
        '◎ Solana (SOL & USDC)': os.getenv('DONATE_SOL'),
        '🔵 Sui (SUI)': os.getenv('DONATE_SUI'),
        '₮ Toncoin (TON & USDT)': os.getenv('DONATE_TON'),
        '🔴 Tron (TRX & USDT)': os.getenv('DONATE_TRX')
    }

    donate_html = t('donate.crypto_title', context)
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
        title = t('donate.stars_title', context)
        payload = "donation-payload"
        currency = "XTR"  # Telegram Stars

        descr_5 = t('donate.stars_5', context)
        prices_5 = [LabeledPrice(t('donate.stars_5_label', context), 5),]
        await send_invoice(context, chat_id, title, descr_5, payload, currency, prices_5)
        descr_50 = t('donate.stars_50', context)
        prices_50 = [LabeledPrice(t('donate.stars_50_label', context), 50),]
        await send_invoice(context, chat_id, title, descr_50, payload, currency, prices_50)
        descr_200 = t('donate.stars_200', context)
        prices_200 = [LabeledPrice(t('donate.stars_200_label', context), 200),]
        await send_invoice(context, chat_id, title, descr_200, payload, currency, prices_200)
        descr_1200 = t('donate.stars_1200', context)
        prices_1200 = [LabeledPrice(t('donate.stars_1200_label', context), 1200),]
        await send_invoice(context, chat_id, title, descr_1200, payload, currency, prices_1200)

    except Exception as e:
        print(f"Ошибка при создании инвойса: {e}")
        await update.message.reply_text(t('donate.error', context))


async def help_cmd(update: Update, context: CallbackContext):
    """Команда помощи со списком всех команд"""
    # Initialize locale (auto-detect if needed)
    get_or_detect_locale(update, context)
    
    help_text = t('help.title', context)

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
    # Initialize locale (auto-detect if needed)
    get_or_detect_locale(update, context)
    
    try:
        stats = DB_BOOKS.get_library_stats()
        last_update = stats['last_update']
        last_update_str = last_update

        # print(f"DEBUG: {last_update}, {last_update_str}")

        reader_recommendations = get_platform_recommendations()

        # Format numbers with spaces
        books_count = f"{stats['books_count']:,}".replace(",", " ")
        authors_count = f"{stats['authors_count']:,}".replace(",", " ")
        series_count = f"{stats['series_count']:,}".replace(",", " ")

        about_text = t('about.title', context,
            books_count=books_count,
            authors_count=authors_count,
            series_count=series_count,
            genres_count=stats['genres_count'],
            languages_count=stats['languages_count'],
            last_update=last_update_str,
            max_filename=stats['max_filename'],
            reader_recommendations=reader_recommendations,
            email=CONTACT_INFO['email'],
            blog=CONTACT_INFO['blog'],
            blog_name=CONTACT_INFO['blog_name'],
            tg_channel=CONTACT_INFO['tg_channel'],
            tg_channel_name=CONTACT_INFO['tg_channel_name']
        )

        await update.message.reply_text(
            about_text,
            parse_mode=ParseMode.HTML,
            disable_web_page_preview=True
        )

    except Exception as e:
        print(f"Error in about command: {e}")
        await update.message.reply_text(
            t('about.error', context),
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
    # Initialize locale (auto-detect if needed)
    get_or_detect_locale(update, context)
    
    try:
        # Загружаем новости из файла
        latest_news = await get_latest_news(BOT_NEWS_FILE_PATH, count=3)

        if not latest_news:
            await update.message.reply_text(
                t('news.empty', context),
                parse_mode=ParseMode.HTML
            )
            return

        news_text = t('news.title', context)

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
            t('news.error', context),
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
