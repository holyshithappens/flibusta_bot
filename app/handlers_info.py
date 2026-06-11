from typing import List, Any

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, CallbackQuery, Update
from telegram.constants import ParseMode
from telegram.ext import CallbackContext

from .database import DB_BOOKS
from .tools import format_book_reviews, format_author_info, format_book_details, format_book_info
from .core.logging_schema import EventType
from .core.structured_logger import structured_logger
from .i18n import t, get_or_detect_locale
from .context import get_current_person_type


# ===== ИНФОРМАЦИЯ О КНИГАХ И АВТОРАХ =====

def _get_user_and_message(update):
    """Extract user and message from either callback query or direct command."""
    if update.callback_query:
        return update.callback_query.from_user, update.callback_query.message
    else:
        return update.effective_user, update.message


async def handle_book_info(update, context, action, params):
    """Показывает информацию о книге с дополнительными кнопками"""
    try:
        user, message = _get_user_and_message(update)
        file_name = params[0]
        book_id = int(file_name)

        # Initialize locale on first access
        get_or_detect_locale(update, context)

        processing_msg = await message.reply_text(
            t('search.loading_book_info', context),
            parse_mode=ParseMode.HTML,
            disable_notification=True
        )

        # Получаем информацию о книге из БД
        locale = get_or_detect_locale(update, context)
        book_info = await DB_BOOKS.get_book_info(book_id, locale)

        if not book_info:
            if update.callback_query:
                await update.callback_query.answer(t('errors.not_found', context))
            else:
                await message.reply_text(t('errors.not_found', context))
            return

        # Формируем сообщение с информацией о книге
        message_text = format_book_info(book_info, context)

        # print(f"DEBUG: book_info = {book_info}")
        # print(f"DEBUG: len = {len(message_text)} message_text = {message_text}")

        # Отправляем сообщение без кнопок сначала
        # Если есть обложка, отправляем фото
        if book_info.get('cover_url'):
            info_message = await message.reply_photo(
                photo=book_info['cover_url'],
                caption=message_text,
                parse_mode=ParseMode.HTML
            )
        else:
            info_message = await message.reply_text(
                message_text,
                parse_mode=ParseMode.HTML
            )

        author_ids = await DB_BOOKS.get_authors_id(book_id)
        translator_ids = await DB_BOOKS.get_translators_id(book_id)

        # print(f"DEBUG: authors_ids = {author_ids}")
        # print(f"DEBUG: translator_ids = {translator_ids}")

        # Создаем клавиатуру с дополнительными кнопками
        keyboard = [
            [InlineKeyboardButton(t('book.download', context), callback_data=f"send_file:{file_name}")],
        ]

        # Author/Translator buttons row - use author_info for both
        author_translator_row = []
        if author_ids:
            author_translator_row.append(
                InlineKeyboardButton(t('book.author', context), callback_data=f"author_info:{author_ids[0]}:author"))
        if translator_ids:
            author_translator_row.append(InlineKeyboardButton(t('book.translator', context),
                                                              callback_data=f"author_info:{translator_ids[0]}:translator"))
        if author_translator_row:
            keyboard.append(author_translator_row)

        keyboard.append(
            [InlineKeyboardButton(t('book.info', context), callback_data=f"book_details:{book_id}"),
             InlineKeyboardButton(t('book.reviews', context), callback_data=f"book_reviews:{book_id}"),
             InlineKeyboardButton(t('common.close', context), callback_data=f"close_info:{info_message.message_id}")],
        )

        reply_markup = InlineKeyboardMarkup(keyboard)

        await processing_msg.delete()

        await info_message.edit_reply_markup(reply_markup)

        structured_logger.log_user_action(
            event_type=EventType.BOOK_INFO_VIEW,
            user_id=user.id,
            username=user.username or user.first_name or "Unknown",
            data={"book_id": book_id, "book_title": book_info['title']},
            chat_type="private",
            chat_id=user.id
        )

    except Exception as e:
        print(f"Error in handle_book_info: {e}")
        if update.callback_query:
            await update.callback_query.answer(t('errors.general', context))
        else:
            await message.reply_text(t('errors.general', context))


async def handle_book_details(update, context, action, params):
    """Показывает детальную информацию о книге с обложкой и аннотацией"""
    query = update.callback_query
    try:
        book_id = int(params[0])
        # Initialize locale on first access
        get_or_detect_locale(update, context)
        book_details = await DB_BOOKS.get_book_details(book_id)

        # print(f"DEBUG: book_details = {book_details}")

        if not book_details:
            await query.message.reply_text(t('errors.not_found', context))
            return

        message_text = format_book_details(book_details, context)

        # Отправляем сообщение без кнопок сначала
        info_message = await query.message.reply_text(
            message_text,
            parse_mode=ParseMode.HTML
        )

        # Добавляем кнопку закрытия с ID сообщения
        await add_close_button_to_message(info_message, [info_message.message_id], context)

    except Exception as e:
        print(f"Error in handle_book_details: {e}")
        await query.answer(t('errors.general', context))
    else:
        # Логируем успешный просмотр детальной информации о книге
        structured_logger.log_book_details_view(
            user_id=query.from_user.id,
            username=query.from_user.username or query.from_user.first_name or "Unknown",
            book_id=book_id,
            book_title=book_details.get('title'),
            chat_type="private",
            chat_id=query.from_user.id
        )


async def handle_author_info(update, context: CallbackContext, action, params):
    """Показывает информацию об авторе/переводчике"""
    user, message = _get_user_and_message(update)
    try:
        person_id = int(params[0])
        # Получаем тип персоны из callback_data или контекста
        person_type = params[1] if len(params) > 1 else get_current_person_type(context)
        get_or_detect_locale(update, context)

        # Try to get as author first, then as translator
        person_info = await DB_BOOKS.get_author_info(person_id)
        # print(f"DEBUG: person_id={person_id}, person_info={person_info}")

        if not person_info:
            await message.reply_text(t('errors.not_found', context))
            return

        message_ids = []
        # Use common format function for both authors and translators
        message_text = format_author_info(person_info, context, person_type)

        # Сообщение 1: Фото без подписи (если есть)
        if person_info.get('photo_url'):
            photo_message = await message.reply_photo(photo=person_info['photo_url'])
            message_ids.append(photo_message.message_id)

        # Сообщение 2: Аннотация с заголовком
        bio_message = await message.reply_text(message_text, parse_mode=ParseMode.HTML)
        message_ids.append(bio_message.message_id)

        # Кнопка "Книги автора" и кнопка закрытия
        await add_author_buttons(bio_message, message_ids, person_id, person_type, context)

    except Exception as e:
        print(f"Error in handle_author_info: {e}")
        if update.callback_query:
            await update.callback_query.answer(t('errors.general', context))
        else:
            await message.reply_text(t('errors.general', context))
    else:
        # Логируем успешный просмотр информации об авторе/переводчике
        structured_logger.log_author_info_view(
            user_id=user.id,
            username=user.username or user.first_name or "Unknown",
            author_id=person_id,
            author_name=person_info.get('name'),
            chat_type="private",
            chat_id=user.id
        )


async def handle_book_by_id(update: Update, context: CallbackContext):
    """Handle /b <book_id> command to show book info directly by ID"""
    # Extract and validate book ID from command arguments
    try:
        if not context.args:
            await update.message.reply_text(
                t('direct_id.book_usage', context),
                parse_mode=ParseMode.HTML
            )
            return
        # print(f"DEBUG: context.args[0]={context.args[0]}")
        book_id = int(context.args[0])
        if book_id <= 0:
            raise ValueError("ID must be positive")
    except (ValueError, IndexError):
        await update.message.reply_text(
            t('direct_id.invalid_id', context),
            parse_mode=ParseMode.HTML
        )
        return

    # Call existing handler with appropriate action and params
    await handle_book_info(update, context, 'book_info', [str(book_id)])


async def handle_author_by_id(update: Update, context: CallbackContext):
    """Handle /a <author_id> command to show author info directly by ID"""
    # Extract and validate author ID from command arguments
    try:
        if not context.args:
            await update.message.reply_text(
                t('direct_id.author_usage', context),
                parse_mode=ParseMode.HTML
            )
            return

        author_id = int(context.args[0])
        if author_id <= 0:
            raise ValueError("ID must be positive")
    except (ValueError, IndexError):
        await update.message.reply_text(
            t('direct_id.invalid_id', context),
            parse_mode=ParseMode.HTML
        )
        return

    # Call existing handler with appropriate action and params
    await handle_author_info(update, context, 'author_info', [str(author_id), 'author'])


async def handle_book_reviews(update, context, action, params):
    """Показывает отзывы о книге"""
    query = update.callback_query
    try:
        book_id = params[0]
        # Initialize locale on first access
        get_or_detect_locale(update, context)
        reviews = await DB_BOOKS.get_book_reviews(book_id)

        # if not reviews:
        #     await query.message.reply_text("📝 Отзывов пока нет")
        #     return

        if reviews:
            message_text = format_book_reviews(reviews, context)
            info_message = await query.message.reply_text(
                message_text,
                parse_mode=ParseMode.HTML
            )
        else:
            info_message = await query.message.reply_text(
                t('book.reviews', context),
                parse_mode=ParseMode.HTML
            )

        # Добавляем кнопку закрытия с ID сообщения
        await add_close_button_to_message(info_message, [info_message.message_id], context)

    except Exception as e:
        print(f"Error in handle_book_reviews: {e}")
        await query.answer(t('errors.general', context))
    else:
        # Логируем успешный просмотр отзывов о книге
        structured_logger.log_book_reviews_view(
            user_id=query.from_user.id,
            username=query.from_user.username or query.from_user.first_name or "Unknown",
            book_id=book_id,
            chat_type="private",
            chat_id=query.from_user.id
        )


async def add_close_button_to_message(to_message, close_message_ids: List[Any], context: CallbackContext):
    """Add a close button to a message.
    
    Args:
        to_message: The message to add the button to
        close_message_ids: List of message IDs to close
        context: The Telegram callback context (required for i18n)
    """
    # Добавляем кнопку закрытия с ID сообщения
    close_data = ':'.join(map(str, close_message_ids))
    # print(f"DEBUG: {close_data}")
    close_text = t('common.close', context)
    keyboard = [[InlineKeyboardButton(close_text, callback_data=f"close_info:{close_data}")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await to_message.edit_reply_markup(reply_markup)


async def add_author_buttons(to_message, close_message_ids: List[Any], author_id: int, person_type: str, context: CallbackContext):
    """Add 'Author's books' and close buttons to author info message.
    
    Args:
        to_message: The message to add the button to
        close_message_ids: List of message IDs to close
        author_id: The author ID for the 'Author's books' button
        context: The Telegram callback context (required for i18n)
    """
    close_data = ':'.join(map(str, close_message_ids))
    close_text = t('common.close', context)
    author_books_text = t('author.books_translator' if person_type == 'translator' else 'author.books', context)

    keyboard = [
        [InlineKeyboardButton(author_books_text, callback_data=f"show_author:{author_id}:{person_type}:msg")],
        [InlineKeyboardButton(close_text, callback_data=f"close_info:{close_data}")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await to_message.edit_reply_markup(reply_markup)


async def handle_close_info(update, context, action, params):
    """Универсальный обработчик закрытия информационных сообщений по ID"""
    query = update.callback_query
    try:
        # Удаляем все переданные message_id
        for msg_id in params:
            # print(f"DEBUG: {msg_id}")
            await context.bot.delete_message(query.message.chat_id, int(msg_id))
    except Exception as e:
        print(f"Error in handle_close_info: {e}")
        await query.answer(t('errors.general', context))
