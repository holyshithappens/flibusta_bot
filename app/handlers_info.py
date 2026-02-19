from typing import List, Any

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, CallbackQuery
from telegram.constants import ParseMode
from telegram.ext import CallbackContext

from .database import DB_BOOKS
from .tools import format_book_reviews, format_author_info, format_book_details, format_book_info
from .core.logging_schema import EventType
from .core.structured_logger import structured_logger
from .i18n import t, get_or_detect_locale

# ===== ИНФОРМАЦИЯ О КНИГАХ И АВТОРАХ =====
async def handle_book_info(update, context, action, params):
    """Показывает информацию о книге с дополнительными кнопками"""
    query = update.callback_query
    try:
        user = query.from_user
        file_name = params[0]
        book_id = int(file_name)
        
        # Initialize locale on first access
        get_or_detect_locale(update, context)

        processing_msg = await query.message.reply_text(
            t('search.loading', context),
            parse_mode=ParseMode.HTML,
            disable_notification=True
        )

        # Получаем информацию о книге из БД
        book_info = await DB_BOOKS.get_book_info(book_id)

        if not book_info:
            await query.answer(t('errors.not_found', context))
            return

        # Формируем сообщение с информацией о книге
        message_text = format_book_info(book_info)

        # print(f"DEBUG: book_info = {book_info}")
        # print(f"DEBUG: len = {len(message_text)} message_text = {message_text}")

        # Отправляем сообщение без кнопок сначала
        # Если есть обложка, отправляем фото
        if book_info.get('cover_url'):
            info_message = await query.message.reply_photo(
                photo=book_info['cover_url'],
                caption=message_text,
                parse_mode=ParseMode.HTML
            )
        else:
            info_message = await query.message.reply_text(
                message_text,
                parse_mode=ParseMode.HTML
            )

        author_ids = await DB_BOOKS.get_authors_id(book_id)

        # print(f"DEBUG: authors_ids = {author_ids}")

        # Создаем клавиатуру с дополнительными кнопками
        keyboard = [
            [InlineKeyboardButton(t('book.download', context), callback_data=f"send_file:{file_name}")],
            [InlineKeyboardButton(t('book.info', context), callback_data=f"book_details:{book_id}"),
            InlineKeyboardButton(t('book.author', context), callback_data=f"author_info:{author_ids[0]}")],
            [InlineKeyboardButton(t('book.rating', context), callback_data=f"book_reviews:{book_id}"),
            InlineKeyboardButton(t('common.close', context), callback_data=f"close_info:{info_message.message_id}")],
        ]

        reply_markup = InlineKeyboardMarkup(keyboard)

        await processing_msg.delete()

        await info_message.edit_reply_markup(reply_markup)

        structured_logger.log_user_action(
            event_type=EventType.BOOK_INFO_VIEW,
            user_id=user.id,
            username=user.username or user.first_name or "Unknown",
            data={"book_id": book_id},
            chat_type="private",
            chat_id=user.id
        )

    except Exception as e:
        print(f"Error in handle_book_info: {e}")
        await query.answer(t('errors.general', context))

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

        message_text = format_book_details(book_details)

        # Отправляем сообщение без кнопок сначала
        info_message = await query.message.reply_text(
            message_text,
            parse_mode=ParseMode.HTML
        )

        # Добавляем кнопку закрытия с ID сообщения
        await add_close_button_to_message(info_message,[info_message.message_id], context)

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
    """Показывает информацию об авторе"""
    query = update.callback_query
    try:
        author_id = int(params[0])
        # print(f"DEBUG: params = {params}")
        # Initialize locale on first access
        get_or_detect_locale(update, context)
        author_info = await DB_BOOKS.get_author_info(author_id)
        # print(f"DEBUG: author_info = {author_info}")

        if not author_info:
            await query.message.reply_text(t('errors.not_found', context))
            return

        message_ids = []  # Храним ID всех сообщений
        message_text = format_author_info(author_info)

        # Сообщение 1: Фото без подписи (если есть)
        if author_info.get('photo_url'):
            photo_message = await query.message.reply_photo(photo=author_info['photo_url'])
            message_ids.append(photo_message.message_id)

        # Сообщение 2: Аннотация с заголовком
        bio_message = await query.message.reply_text(message_text, parse_mode=ParseMode.HTML)
        message_ids.append(bio_message.message_id)

        # Кнопка закрытия с передачей всех message_id
        await add_close_button_to_message(bio_message,message_ids, context)

    except Exception as e:
        print(f"Error in handle_author_info: {e}")
        await query.answer(t('errors.general', context))
    else:
        # Логируем успешный просмотр информации об авторе
        structured_logger.log_author_info_view(
            user_id=query.from_user.id,
            username=query.from_user.username or query.from_user.first_name or "Unknown",
            author_id=author_id,
            author_name=author_info.get('name'),
            chat_type="private",
            chat_id=query.from_user.id
        )


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
            message_text = format_book_reviews(reviews)
            info_message = await query.message.reply_text(
                message_text,
                parse_mode=ParseMode.HTML
            )
        else:
            info_message = await query.message.reply_text(
                t('book.rating', context),
                parse_mode=ParseMode.HTML
            )

        # Добавляем кнопку закрытия с ID сообщения
        await add_close_button_to_message(info_message,[info_message.message_id], context)

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
