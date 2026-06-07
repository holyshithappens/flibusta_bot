import asyncio

from telegram import Update, InlineKeyboardMarkup
from telegram.constants import ParseMode
from telegram.error import BadRequest
from telegram.ext import CallbackContext

from .database import DB_BOOKS
from .handlers_group import handle_group_callback
from .handlers_info import handle_close_info, handle_book_reviews, handle_book_info, handle_book_details, \
    handle_author_info, add_close_button_to_message
from .handlers_search import handle_authors_page_change, handle_series_page_change, handle_books_page_change, \
    handle_search_series_books, handle_search_author_books, handle_search_books
from .handlers_settings import create_rating_filter_keyboard, show_settings_menu, handle_set_actions, \
    handle_set_max_books, handle_set_lang_search, handle_set_size_limit, handle_set_book_format, \
    handle_set_search_type, handle_set_rating_filter, handle_set_search_area, handle_set_locale, \
    handle_set_genre_filter, create_genre_filter_parent_keyboard
from .handlers_utils import create_authors_keyboard, create_series_keyboard, handle_send_file, generate_books_csv, \
    create_genre_filter_keyboard
from .constants import SETTING_MAX_BOOKS, SETTING_LANG_SEARCH, \
    SETTING_BOOK_FORMAT, SETTING_SEARCH_TYPE, SETTING_OPTIONS, SETTING_TITLES, SETTING_RATING_FILTER, \
    SETTING_SEARCH_AREA, SEARCH_TYPE_BOOKS, SEARCH_TYPE_SERIES, SEARCH_TYPE_AUTHORS, SETTING_SIZE_LIMIT, \
    SETTING_LOCALE, SETTING_GENRE_FILTER
from .context import get_pages_of_series, get_found_series_count, get_pages_of_authors, get_found_authors_count, \
    get_pages_of_books, get_user_params, update_user_params, get_last_series_page, \
    get_last_authors_page, set_switch_search, get_switch_search
from .flibusta_client import FlibustaClient
from .tools import form_header_books
from .health import log_stats
from .core.structured_logger import structured_logger
from .core.logging_schema import EventType
from .i18n import t, get_or_detect_locale

# ===== CALLBACK ОБРАБОТЧИКИ =====
async def button_callback(update: Update, context: CallbackContext):
    """УНИВЕРСАЛЬНЫЙ обработчик callback-запросов"""
    # print(f"DEBUG: {context._user_id} {context._chat_id}")
    # for attr_name in dir(context):
    #     attr_value = getattr(context, attr_name)
    #     print(f"{attr_name}: {type(attr_value).__name__}")

    query = update.callback_query
    user = query.from_user

    try:
        await query.answer()
    except BadRequest as e:
        if "Query is too old" in str(e):
            # Игнорируем устаревшие callback'ы
            return
        raise e

    data = query.data.split(':')
    action, *params = data

    # Определяем контекст (личный чат или группа)
    is_group = query.message.chat.type in ['group', 'supergroup']

    if is_group:
        # Для групп используем отдельную логику с привязкой к пользователю
        await handle_group_callback(update, context, action, params, user)
    else:
        # Сначала проверяем АДМИНСКИЕ действия
        if action in ['users_list', 'user_detail', 'toggle_block', 'recent_searches',
                       'recent_downloads', 'top_downloads', 'top_searches', 'back_to_stats',
                       'refresh_stats', 'payments_list']:
            # Перенаправляем в админский обработчик
            from .admin import handle_admin_callback
            await handle_admin_callback(update, context)
            return
        # Существующая логика для личных сообщений
        await handle_private_callback(update, context, action, params)

    await log_stats(context)


async def handle_private_callback(update, context, action, params):
    query = update.callback_query
    # Затем проверяем ПОЛЬЗОВАТЕЛЬСКИЕ действия
    action_handlers = {
        'send_file': handle_send_file,
        'show_genres': handle_show_genres,
        'back_to_settings': handle_back_to_settings,
        f'set_{SETTING_MAX_BOOKS}': handle_set_max_books,
        f'set_{SETTING_LANG_SEARCH}': handle_set_lang_search,
        # f'set_{SETTING_SORT_ORDER}': handle_set_sort_order,
        f'set_{SETTING_SIZE_LIMIT}': handle_set_size_limit,
        f'set_{SETTING_BOOK_FORMAT}': handle_set_book_format,
        f'set_{SETTING_SEARCH_TYPE}': handle_set_search_type,
        f'set_{SETTING_RATING_FILTER}': handle_set_rating_filter,
        f'set_{SETTING_SEARCH_AREA}': handle_set_search_area,
        f'set_{SETTING_LOCALE}': handle_set_locale,
        f'set_{SETTING_GENRE_FILTER}': handle_set_genre_filter,
        'show_series': handle_search_series_books,
        'back_to_series': handle_back_to_series,
        'show_author': handle_search_author_books,  # Добавляем обработчик для авторов
        'back_to_authors': handle_back_to_authors,  # Добавляем обработчик возврата к авторам
        'reset_ratings': handle_reset_ratings,
        'book_info': handle_book_info,
        'book_details': handle_book_details,
        'author_info': handle_author_info,
        'book_reviews': handle_book_reviews,
        'close_info': handle_close_info,
        'close_message': handle_close_message,
        'download_books_csv': handle_download_books_csv,  # CSV export handler
    }

    # Добавим обработку toggle рейтингов
    if action.startswith('toggle_rating_'):
        await handle_toggle_rating(update, context, action, params)
        return

    # Genre filter handlers
    if action.startswith('toggle_genre_'):
        await handle_toggle_genre(update, context, action, params)
        return

    if action.startswith('switch_genre_group_'):
        await handle_switch_genre_group(update, context, action, params)
        return

    if action == 'clear_all_genres':
        await handle_clear_all_genres(update, context, action, params)
        return

    if action == 'show_genre_filter':
        await handle_show_genre_filter_children(update, context, action, params)
        return

    if action == 'back_to_genre_filter':
        await handle_back_to_genre_filter(update, context, action, params)
        return

    # Прямой поиск обработчика в словаре
    if action in action_handlers:
        handler = action_handlers[action]
        # Запускаем асинхронный обработчик с update параметром
        asyncio.create_task(
            handler(update, context, action, params)
        )
        return

    # Затем проверяем префиксы
    if action.startswith(f"{SEARCH_TYPE_BOOKS}_page_"):
        await handle_books_page_change(update, context, action, params)
        return

    if action.startswith(f"{SEARCH_TYPE_SERIES}_page_"):
        await handle_series_page_change(update, context, action, params)
        return

    if action.startswith(f"{SEARCH_TYPE_AUTHORS}_page_"):
        await handle_authors_page_change(update, context, action, params)
        return

    # Обработка set_ действий
    if action.startswith('set_'):
        await handle_set_actions(update, context, action, params)
        return

    # Обработка просмотра популярных книг и новинок
    if action.startswith('show_pop_'):
        await handle_show_pops(update, context, action, params)
        return

    # Если ничего не найдено
    print(f"Unknown action: {action}")
    await update.callback_query.edit_message_text(t('callback.unknown_action', context))


async def handle_show_genres(update, context, action, params):
    """Показывает жанры выбранной категории"""
    query = update.callback_query
    try:
        # Initialize locale (auto-detect if needed)
        locale = get_or_detect_locale(update, context)
        
        genre_index = int(params[0])  # Получаем genre index

        # Получаем полный список жанров с учётом локали
        results = DB_BOOKS.get_parent_genres_count(locale)

        parent_genre = results[genre_index][0]  # Получаем название по индексу
        # print(f"DEBUG: {genre_id}")
        genres = DB_BOOKS.get_genres_with_counts(parent_genre, locale)
        # print(f"DEBUG: {genres}")

        if genres:
            genres_html = f"<b>{parent_genre}</b>\n\n"
            for genre_name,count,genre_id in genres:
               count_text = f" ({count:,})".replace(",", " ")  if count else " (0)"
               genre_link = FlibustaClient.get_genre_url(genre_id)
               genres_html += f"<a href='{genre_link}'>{genre_name}</a>{count_text}\n"
            genres_message = await query.message.reply_text(genres_html, parse_mode=ParseMode.HTML)
            await add_close_button_to_message(genres_message, [genres_message.message_id], context)
        else:
           await query.message.reply_text(t('genres.not_found', context), parse_mode=ParseMode.HTML)

        structured_logger.log_user_action(
            event_type=EventType.GENRES_VIEW,
            user_id=query.from_user.id,
            username=query.from_user.username or query.from_user.first_name or "Unknown",
            data={"parent_genre": parent_genre},
            chat_type=query.message.chat.type,
            chat_id=query.message.chat.id
        )

    except Exception as e:
        print(f"Error in handle_show_genres: {e}")
        await query.message.reply_text(t('genres.error', context))

    await log_stats(context)


async def handle_back_to_settings(update, context, action, params):
    """Возвращает в главное меню настроек"""
    query = update.callback_query
    await show_settings_menu(query, context, from_callback=True)


async def handle_back_to_series(update, context, action, params):
    """Возвращает к результатам поиска серий"""
    query = update.callback_query
    try:
        # Восстанавливаем последнюю позицию
        page_num = get_last_series_page(context)
        pages_of_series = get_pages_of_series(context)
        if not pages_of_series:
            await query.edit_message_text(t('callback.restore_error', context))
            return

        keyboard = create_series_keyboard(page_num, pages_of_series, context)
        reply_markup = InlineKeyboardMarkup(keyboard)

        if reply_markup:
            found_series_count = get_found_series_count(context)
            user_params = get_user_params(context)
            search_area = user_params.SearchArea
            show_pop = get_switch_search(context)

            header_found_text = form_header_books(
                context,
                page_num, user_params.MaxBooks, found_series_count, SEARCH_TYPE_SERIES,
                search_area=search_area,
                show_pop=show_pop
            )
            await query.edit_message_text(header_found_text, reply_markup=reply_markup)
        else:
            await query.edit_message_text(t('callback.restore_error', context))

    except Exception as e:
        print(f"Ошибка при возврате к сериям: {e}")
        await query.edit_message_text(t('callback.back_error', context))


async def handle_back_to_authors(update, context, action, params):
    """Возвращает к результатам поиска авторов"""
    query = update.callback_query
    try:
        # Восстанавливаем последнюю позицию
        page_num = get_last_authors_page(context)
        pages_of_authors = get_pages_of_authors(context)
        if not pages_of_authors:
            await query.edit_message_text(t("callback.restore_error", context))
            return

        keyboard = create_authors_keyboard(page_num, pages_of_authors, context)
        reply_markup = InlineKeyboardMarkup(keyboard)

        if reply_markup:
            found_authors_count = get_found_authors_count(context)
            user_params = get_user_params(context)
            search_area = user_params.SearchArea
            show_pop = get_switch_search(context)

            header_found_text = form_header_books(
                context,
                page_num, user_params.MaxBooks, found_authors_count, SEARCH_TYPE_AUTHORS,
                search_area=search_area,
                show_pop=show_pop
            )
            await query.edit_message_text(header_found_text, reply_markup=reply_markup)

    except Exception as e:
        print(f"Ошибка при возврате к авторам: {e}")
        await query.edit_message_text(t("callback.back_error", context))


async def handle_close_message(update, context, action, params):
    """Закрывает меню настроек"""
    query = update.callback_query
    await query.delete_message()


async def handle_toggle_rating(update, context, action, params):
    """Обрабатывает переключение рейтинга в фильтре"""
    query = update.callback_query
    rating_value = action.removeprefix('toggle_rating_')
    current_filter = get_user_params(context).Rating
    current_ratings = current_filter.split(',') if current_filter else []

    if rating_value in current_ratings:
        # Убираем рейтинг из фильтра
        current_ratings.remove(rating_value)
    else:
        # Добавляем рейтинг в фильтр
        current_ratings.append(rating_value)

    # Обновляем фильтр
    new_filter = ','.join(current_ratings)
    update_user_params(context, Rating=new_filter)

    # Обновляем клавиатуру
    options = [
        (value, t(label, context))
        for value, label in SETTING_OPTIONS[SETTING_RATING_FILTER]
    ]
    reply_markup = create_rating_filter_keyboard(current_ratings, options, context)

    try:
        await query.edit_message_text(t(SETTING_TITLES[SETTING_RATING_FILTER],context), reply_markup=reply_markup)
    except BadRequest as e:
        if "Message is not modified" not in str(e):
            raise e

    structured_logger.log_settings_change(
        user_id=query.from_user.id,
        username=query.from_user.username or query.from_user.first_name or "Unknown",
        setting_name="rating_filter",
        old_value=current_filter,
        new_value=new_filter,
        chat_type=query.message.chat.type,
        chat_id=query.message.chat.id
    )


async def handle_reset_ratings(update, context, action, params):
    """Сбрасывает все выбранные рейтинги"""
    query = update.callback_query
    update_user_params(context, Rating='')

    # Обновляем клавиатуру
    options = [
        (value, t(label, context))
        for value, label in SETTING_OPTIONS[SETTING_RATING_FILTER]
    ]
    reply_markup = create_rating_filter_keyboard([], options, context)

    await query.edit_message_text(t(SETTING_TITLES[SETTING_RATING_FILTER],context), reply_markup=reply_markup)
    structured_logger.log_settings_change(
        user_id=query.from_user.id,
        username=query.from_user.username or query.from_user.first_name or "Unknown",
        setting_name="rating_filter",
        old_value="reset",
        new_value="",
        chat_type=query.message.chat.type,
        chat_id=query.message.chat.id
    )


async def handle_show_pops(update, context, action, params):
    """Запуск поиска популярных книг и новинок"""
    try:
        set_switch_search(context, action)
        # await handle_message(update, context)
        await handle_search_books(update, context)

    except Exception as e:
        print(f"Error in handle_show_pops: {e}")
        await update.callback_query.message.reply_text(t("callback.popular_error", context))

    await log_stats(context)


async def handle_download_books_csv(update, context, action, params):
    """Handle CSV download request for found books."""
    query = update.callback_query
    processing_msg = None
    try:
        # Get books from context
        pages_of_books = get_pages_of_books(context)

        if not pages_of_books:
            await query.answer(t("callback.results_expired"))
            return

        # Send immediate waiting message
        processing_msg = await query.message.reply_text(
            t("csv.generating", context),
            parse_mode=ParseMode.HTML,
            disable_notification=True
        )

        # Generate CSV
        filename, csv_buffer = generate_books_csv(pages_of_books)

        # Prepare buffer for sending
        csv_buffer.seek(0)

        # Count total books
        total_books = sum(len(page) for page in pages_of_books)

        # Send as document
        await query.message.reply_document(
            document=csv_buffer,
            filename=filename,
            caption=t("csv.books_found", context, count=total_books),
            disable_notification=True
        )

        # Delete the waiting message
        if processing_msg:
            await processing_msg.delete()

        # Log action
        structured_logger.log_user_action(
            event_type=EventType.CSV_DOWNLOAD,
            user_id=query.from_user.id,
            username=query.from_user.username or query.from_user.first_name or "Unknown",
            data={"book_count": total_books, "filename": filename},
            chat_type=query.message.chat.type,
            chat_id=query.message.chat.id
        )

    except Exception as e:
        print(f"Error generating CSV: {e}")
        # Delete the waiting message if it exists
        if processing_msg:
            await processing_msg.delete()
        await query.message.reply_text(t("csv.error", context))
        structured_logger.log_error(
            error_type="csv_generation_failed",
            error_message=str(e),
            context={},
            user_id=query.from_user.id,
            username=query.from_user.username or query.from_user.first_name or "Unknown"
        )


async def handle_show_genre_filter_children(update, context, action, params):
    """
    Shows child genres for a parent category in the filter context.

    Pattern: show_genre_filter:{parent_genre_index}
    """
    query = update.callback_query
    try:
        locale = get_or_detect_locale(update, context)
        genre_index = int(params[0])

        results = DB_BOOKS.get_parent_genres_count(locale)
        parent_genre = results[genre_index][0]

        genres = DB_BOOKS.get_genres_with_counts(parent_genre, locale)

        if genres:
            user_params = get_user_params(context)
            current_filter = user_params.GenreFilter if user_params else ''
            # Filter out empty strings: ''.split(',') returns ['']
            current_genre_ids = [g for g in current_filter.split(',') if g] if current_filter else []

            reply_markup = create_genre_filter_keyboard(parent_genre, current_genre_ids, genres, context,
                                                         back_callback="back_to_genre_filter")

            await query.edit_message_text(
                f"<b>{parent_genre}</b>\n\n{t('genres.select_genres', context)}",
                reply_markup=reply_markup,
                parse_mode=ParseMode.HTML
            )
    except Exception as e:
        import traceback
        print(f"Error in handle_show_genre_filter_children: {e}")
        traceback.print_exc()
        await query.message.reply_text(t('genres.error', context))


async def handle_back_to_genre_filter(update, context, action, params):
    """
    Returns to parent genres filter keyboard from child genres.
    Pattern: back_to_genre_filter
    """
    query = update.callback_query
    user_params = get_user_params(context)
    locale = user_params.Locale or 'ru'

    # Get parent genres
    parent_genres = DB_BOOKS.get_parent_genres_count(locale)

    # Get current active genre IDs
    current_filter = user_params.GenreFilter
    active_genre_ids = set(g for g in current_filter.split(',') if g) if current_filter else set()

    # Pre-fetch child genres for 3-state indicators
    all_child_genres = {}
    for genre_name, _ in parent_genres:
        all_child_genres[genre_name] = DB_BOOKS.get_genres_with_counts(genre_name, locale)

    keyboard = create_genre_filter_parent_keyboard(
        context, parent_genres, active_genre_ids, locale, all_child_genres
    )
    reply_markup = InlineKeyboardMarkup(keyboard)

    try:
        await query.edit_message_text(
            t('settings.menu.genre_filter', context),
            reply_markup=reply_markup
        )
    except BadRequest as e:
        if "Message is not modified" not in str(e):
            raise e


async def handle_toggle_genre(update, context, action, params):
    """
    Handles toggling individual genre selection.

    Pattern: toggle_genre_{genre_id}
    """
    query = update.callback_query
    genre_id = action.removeprefix('toggle_genre_')

    # Get current filter
    current_filter = get_user_params(context).GenreFilter
    # Filter out empty strings: ''.split(',') returns ['']
    current_genres = [g for g in current_filter.split(',') if g] if current_filter else []

    # Toggle genre
    if genre_id in current_genres:
        current_genres.remove(genre_id)
    else:
        current_genres.append(genre_id)

    # Update filter using partial update (same pattern as rating toggle)
    new_filter = ','.join(current_genres)
    update_user_params(context, GenreFilter=new_filter)

    # Refresh keyboard — rebuild and show genre keyboard
    locale = get_or_detect_locale(update, context)
    # Find the parent genre from the current genres list
    # We need to re-fetch the parent genre name from the callback data context
    # Since we don't have parent_genre directly, we need to find it
    parent_genre = None
    for pg_name in DB_BOOKS.get_parent_genres_count(locale):
        pg_name_str = pg_name[0]
        child_genres = DB_BOOKS.get_genres_with_counts(pg_name_str, locale)
        if any(str(g[2]) == genre_id for g in child_genres):
            parent_genres = child_genres
            parent_genre = pg_name_str
            break

    if parent_genre:
        current_genre_ids = [g for g in new_filter.split(',') if g] if new_filter else []
        reply_markup = create_genre_filter_keyboard(parent_genre, current_genre_ids, parent_genres, context,
                                                     back_callback="back_to_genre_filter")
        try:
            await query.edit_message_text(
                f"<b>{parent_genre}</b>\n\n{t('genres.select_genres', context)}",
                reply_markup=reply_markup,
                parse_mode=ParseMode.HTML
            )
        except BadRequest as e:
            if "Message is not modified" not in str(e):
                raise e

    # Log the change (same pattern as rating toggle)
    structured_logger.log_settings_change(
        user_id=query.from_user.id,
        username=query.from_user.username or query.from_user.first_name or "Unknown",
        setting_name="genre_filter",
        old_value=current_filter,
        new_value=new_filter,
        chat_type=query.message.chat.type,
        chat_id=query.message.chat.id
    )


async def handle_switch_genre_group(update, context, action, params):
    """
    Handles Select All / Clear All for a genre group.

    Pattern: switch_genre_group_{parent_genre}
    """
    query = update.callback_query
    parent_genre = action.removeprefix('switch_genre_group_')

    # Get all child genre IDs for this parent
    locale = get_or_detect_locale(update, context)
    child_genres = DB_BOOKS.get_genres_with_counts(parent_genre, locale)
    child_ids = [str(g[2]) for g in child_genres]

    # Get current filter (filter out empty strings)
    current_filter = get_user_params(context).GenreFilter
    current_genres = set(g for g in current_filter.split(',') if g) if current_filter else set()

    # Check if all are selected
    all_selected = all(gid in current_genres for gid in child_ids)

    if all_selected:
        # Clear all in this group
        new_genres = current_genres - set(child_ids)
    else:
        # Select all in this group
        new_genres = current_genres | set(child_ids)

    # Update filter using partial update
    new_filter = ','.join(new_genres)
    update_user_params(context, GenreFilter=new_filter)

    # Refresh keyboard — rebuild and show genre keyboard
    current_genre_ids = [g for g in new_filter.split(',') if g] if new_filter else []
    reply_markup = create_genre_filter_keyboard(parent_genre, current_genre_ids, child_genres, context,
                                                 back_callback="back_to_genre_filter")
    try:
        await query.edit_message_text(
            f"<b>{parent_genre}</b>\n\n{t('genres.select_genres', context)}",
            reply_markup=reply_markup,
            parse_mode=ParseMode.HTML
        )
    except BadRequest as e:
        if "Message is not modified" not in str(e):
            raise e

    # Log the change
    structured_logger.log_settings_change(
        user_id=query.from_user.id,
        username=query.from_user.username or query.from_user.first_name or "Unknown",
        setting_name="genre_filter",
        old_value=current_filter,
        new_value=new_filter,
        chat_type=query.message.chat.type,
        chat_id=query.message.chat.id
    )


async def handle_clear_all_genres(update, context, action, params):
    """
    Clears all genre filters.

    Pattern: clear_all_genres
    """
    query = update.callback_query
    old_filter = get_user_params(context).GenreFilter
    update_user_params(context, GenreFilter='')

    # Refresh parent keyboard
    user_params = get_user_params(context)
    locale = user_params.Locale or 'ru'
    parent_genres = DB_BOOKS.get_parent_genres_count(locale)

    # Pre-fetch child genres for 3-state indicators
    all_child_genres = {}
    for genre_name, _ in parent_genres:
        all_child_genres[genre_name] = DB_BOOKS.get_genres_with_counts(genre_name, locale)

    keyboard = create_genre_filter_parent_keyboard(
        context, parent_genres, set(), locale, all_child_genres
    )
    reply_markup = InlineKeyboardMarkup(keyboard)

    await query.edit_message_text(
        t('settings.menu.genre_filter', context),
        reply_markup=reply_markup
    )

    # Log the change
    structured_logger.log_settings_change(
        user_id=query.from_user.id,
        username=query.from_user.username or query.from_user.first_name or "Unknown",
        setting_name="genre_filter",
        old_value=old_filter,
        new_value="",
        chat_type=query.message.chat.type,
        chat_id=query.message.chat.id
    )