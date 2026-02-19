from datetime import datetime

from telegram import Update, InlineKeyboardMarkup
from telegram.constants import ParseMode
from telegram.ext import CallbackContext

from .database import DB_BOOKS
from .handlers_info import handle_book_info, handle_book_details, handle_author_info, handle_book_reviews, \
    handle_close_info
from .handlers_utils import create_books_keyboard, handle_send_file
from .constants import SEARCH_TYPE_BOOKS
from .context import set_last_activity, get_pages_of_books, get_found_books_count, set_last_search_query, \
    set_last_bot_message_id, get_user_params, update_user_params, set_books, get_last_bot_message_id
from .tools import is_message_for_bot, extract_clean_query, form_header_books
from .health import log_stats
from .core.structured_logger import structured_logger
from .i18n import t, get_or_detect_locale

# ===== РАБОТА В ГРУППЕ =====
async def handle_group_message(update: Update, context: CallbackContext):
    """Обрабатывает сообщения из группы"""
    try:
        # Initialize locale on first access
        get_or_detect_locale(update, context)
        # Проверяем, обращается ли пользователь к боту
        if not is_message_for_bot(update.effective_message.text, context.bot.username):
            # Сообщение НЕ для бота - пропускаем обработку
            return

        # Обрабатываем поиск от имени пользователя
        await handle_group_search(update, context)

    except Exception as e:
        print(f"Ошибка при обработке сообщения из группы: {e}")
        # Отправляем сообщение об ошибке через context.bot
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=t('errors.general', context),
            reply_to_message_id=update.effective_message.message_id
        )

    await log_stats(context)


async def handle_group_search(update: Update, context: CallbackContext):
    """Обрабатывает поисковые запросы из группы"""
    try:
        # ОПРЕДЕЛЯЕМ ТИП СООБЩЕНИЯ
        is_edited = update.edited_message is not None
        message = update.edited_message if is_edited else update.message
        user = message.from_user
        chat = update.effective_chat

        # Извлекаем чистый запрос (убираем упоминание бота)
        clean_query_text = extract_clean_query(message.text, context.bot.username)

        if not clean_query_text:
            await message.reply_text(
                t('errors.general', context),
                reply_to_message_id=message.message_id
            )
            return

        search_context_key = f"group_search_{chat.id}"
        # ЕСЛИ СООБЩЕНИЕ ОТРЕДАКТИРОВАНО - УДАЛЯЕМ ПРЕДЫДУЩИЙ РЕЗУЛЬТАТ
        if is_edited:
            last_bot_message_id = get_last_bot_message_id(context)
            if last_bot_message_id:
                try:
                    await context.bot.delete_message(
                        chat_id=message.chat_id,
                        message_id=last_bot_message_id
                    )
                except Exception as e:
                    print(f"Не удалось удалить старое сообщение: {e}")

        # Отправляем сообщение о начале поиска
        processing_msg = await message.reply_text(
            t('search.loading', context),
            parse_mode=ParseMode.HTML,
            reply_to_message_id=message.message_id
        )

        # Получаем или создаем настройки пользователя
        user_params = get_user_params(context)

        print(f"DEBUG: clean_query_text = {clean_query_text}")

        # Выполняем поиск книг
        books = DB_BOOKS.search_books(
            clean_query_text, user_params.Lang, user_params.BookSize, user_params.Rating,
            search_area=user_params.SearchArea
        )
        found_books_count = len(books)

        # Удаляем сообщение "Ищу книги..."
        await processing_msg.delete()

        if books and found_books_count > 0:
            pages_of_books = [books[i:i + user_params.MaxBooks] for i in range(0, len(books), user_params.MaxBooks)]
            page = 0

            keyboard = create_books_keyboard(page, pages_of_books)
            reply_markup = InlineKeyboardMarkup(keyboard)

            if reply_markup:
                user_name = (user.first_name if user.first_name else "") #+ (f" @{user.username}" if user.username else "")
                header_found_text = f"📚 Результаты поиска" + (f" для {user_name}" if user_name else "") + ":\n\n"
                header_found_text += form_header_books(
                    page, user_params.MaxBooks, found_books_count,
                    search_area=user_params.SearchArea
                )

                # Отправляем результаты поиска
                result_message = await context.bot.send_message(
                    chat_id=chat.id,
                    text=header_found_text,
                    reply_markup=reply_markup
                )

                # Сохраняем контекст поиска в bot_data (доступно всем пользователям группы)
                set_books(context, pages_of_books, found_books_count)
                set_last_search_query(context, clean_query_text)
                set_last_activity(context, datetime.now())
                set_last_bot_message_id(context, result_message.message_id)

                # Обновляем настройки пользователя - преобразуем в словарь
                user_params_dict = user_params._asdict()  # namedtuple в словарь
                update_user_params(context, **user_params_dict)

        else:
            # Отправляем сообщение о том, что книги не найдены
            result_message = await context.bot.send_message(
                chat_id=chat.id,
                text=t('search.no_results', context),
                reply_to_message_id=message.message_id
            )
            # Сохраняем контекст поиска в bot_data (доступно всем пользователям группы)
            set_last_bot_message_id(context, result_message.message_id)

        structured_logger.log_search(
            user_id=user.id,
            username=user.username or user.first_name or "Unknown",
            query=clean_query_text,
            search_type="books",
            search_area=user_params.SearchArea,
            results_count=found_books_count,
            duration_ms=0,
            chat_type="group",
            chat_id=chat.id
        )

    except Exception as e:
        print(f"Ошибка при обработке поиска из группы: {e}")
        # Используем context.bot вместо update.message
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=t('errors.general', context),
            reply_to_message_id=update.effective_message.message_id
        )


async def handle_group_callback(update, context, action, params, user):
    """Обрабатывает callback-запросы из групп"""
    query = update.callback_query
    # Initialize locale on first access
    get_or_detect_locale(update, context)
    # Восстанавливаем контекст поиска пользователя
    search_context_user_params = get_user_params(context)

    if not search_context_user_params:
        await query.edit_message_text(t('search.session_expired', context))
        return

    action_handlers = {
        'book_info': handle_book_info,
        'book_details': handle_book_details,
        'author_info': handle_author_info,
        'book_reviews': handle_book_reviews,
        'close_info': handle_close_info,
    }

    # Обрабатываем действия
    if action.startswith(f"{SEARCH_TYPE_BOOKS}_page_"):
        await handle_group_page_change(update, context, action, params, user)
    elif action == 'send_file':
        await handle_send_file(query, context, action, params, user)
    # Прямой поиск обработчика в словаре
    elif action in action_handlers:
        handler = action_handlers[action]
        await handler(update, context, action, params)
    else:
        await query.edit_message_text(t('callback.unknown_action', context))

    await log_stats(context)


async def handle_group_page_change(update, context, action, params, user):
    """Обрабатывает смену страницы в группе"""
    query = update.callback_query
    # Initialize locale on first access
    get_or_detect_locale(update, context)
    # Восстанавливаем контекст поиска пользователя
    search_context_user_params = get_user_params(context)

    if not search_context_user_params:
        await query.edit_message_text(t('search.session_expired', context))
        return

    pages_of_books = get_pages_of_books(context)
    page = int(action.removeprefix(f"{SEARCH_TYPE_BOOKS}_page_"))

    if not pages_of_books or page >= len(pages_of_books):
        await query.edit_message_text(t('search.page_error', context))
        return

    keyboard = create_books_keyboard(page, pages_of_books)
    reply_markup = InlineKeyboardMarkup(keyboard)

    if reply_markup:
        found_books_count = get_found_books_count(context)
        user_params = get_user_params(context)
        search_area = user_params.SearchArea

        user_name = (user.first_name if user.first_name else "")
        header_text = f"📚 Результаты поиска" + (f" для {user_name}" if user_name else "") + ":\n\n"
        header_text += form_header_books(
            page, user_params.MaxBooks, found_books_count,
            search_area=search_area
        )

        await query.edit_message_text(header_text, reply_markup=reply_markup)