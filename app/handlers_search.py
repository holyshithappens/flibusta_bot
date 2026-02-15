import asyncio
from datetime import datetime
from time import time

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import CallbackContext
from telegram.constants import ParseMode
from telegram.error import Forbidden

from .context import ContextManager

from .handlers_utils import create_books_keyboard, create_series_keyboard, create_authors_keyboard
from .tools import form_header_books
from .database import DB_BOOKS
from .constants import SEARCH_TYPE_BOOKS, SEARCH_TYPE_SERIES, SEARCH_TYPE_AUTHORS, SETTING_SEARCH_AREA_B, \
    SETTING_SEARCH_AREA_BA
from .context import get_user_params, get_last_bot_message_id, set_books, set_last_activity, set_last_bot_message_id, \
    set_last_search_query, set_series, set_last_series_page, get_last_search_query, set_current_series_name, \
    set_authors, set_last_authors_page, set_current_author_id, set_current_author_name, get_pages_of_books, \
    get_current_author_id, get_found_books_count, get_current_series_name, get_current_author_name, get_pages_of_series, \
    get_found_series_count, get_pages_of_authors, get_found_authors_count, get_switch_search, set_switch_search
from .health import log_stats
from .core.structured_logger import structured_logger
from .i18n import t

# ===== ПОИСК И НАВИГАЦИЯ =====
async def handle_message(update: Update, context: CallbackContext):
    """Обрабатывает текстовые сообщения (поиск книг или серий)"""
    # print(f"DEBUG: {context._user_id} {context._chat_id}")
    # for attr_name in dir(context):
    #     attr_value = getattr(context, attr_name)
    #     print(f"{attr_name}: {type(attr_value).__name__}")

    try:
        # Обрабатываем новый запрос
        user_params = get_user_params(context)
        search_type = user_params.SearchType
        # Сбрасываем переключатель показа новинок/популярных
        set_switch_search(context, None)

        if search_type == SEARCH_TYPE_BOOKS:
            await handle_search_books(update, context)
        elif search_type == SEARCH_TYPE_SERIES:
            await handle_search_series(update, context)
        elif search_type == SEARCH_TYPE_AUTHORS:  # Добавляем обработку поиска по авторам
            await handle_search_authors(update, context)

    except Forbidden as e:
        if "bot was blocked by the user" in str(e):
            print(f"Пользователь {update.effective_user.id} заблокировал бота")
            return
        raise e
    except Exception as e:
        print(f"Error in handle_message: {e}")
        await update.message.reply_text(t('search.error', context))

    await log_stats(context)


async def handle_search_books(update: Update, context: CallbackContext):
    """Обрабатывает текстовые сообщения (поиск книг)"""
    # ОПРЕДЕЛЯЕМ ТИП СООБЩЕНИЯ
    is_edited = update.edited_message is not None
    message = update.edited_message if is_edited else update.message if update.message else update.callback_query.message
    # print(f"DEBUG: {update}")
    if message.from_user.is_bot:
        # Последнее сообщение от бота, не поисковый запрос
        query_text = ''
        user = update.callback_query.from_user
    else:
        query_text = message.text
        user = message.from_user

    # ЕСЛИ СООБЩЕНИЕ ОТРЕДАКТИРОВАНО - УДАЛЯЕМ ПРЕДЫДУЩИЙ РЕЗУЛЬТАТ
    if is_edited:
        # last_bot_message_id = context.user_data.get('last_bot_message_id')
        last_bot_message_id = get_last_bot_message_id(context)
        if last_bot_message_id:
            try:
                await context.bot.delete_message(
                    chat_id=message.chat_id,
                    message_id=last_bot_message_id
                )
            except Exception as e:
                print(f"Не удалось удалить старое сообщение: {e}")

    processing_msg = await message.reply_text(
        t('search.loading', context),
        parse_mode=ParseMode.HTML,
        disable_notification=True
    )

    # Запускаем асинхронный поиск
    asyncio.create_task(
        async_search_books(context, query_text, processing_msg, user)
    )


async def async_search_books(context: CallbackContext, query_text: str, processing_msg, user, series_id=0, author_id=0):
    """Асинхронная задача поиска книг"""
    try:
        start_time = time()
        # Извлекаем из контекста или БД настройки пользователя
        user_params = get_user_params(context)

        # Сбрасываем переключатель в handle_message, т.к. он вызывается только по поисковому запросу
        switch_search = get_switch_search(context)

        # print(f"DEBUG: {switch_search}")

        if switch_search:
            days = int(switch_search.removeprefix('show_pop_'))
            books = await asyncio.get_event_loop().run_in_executor(
                None,  # Используем стандартный ThreadPoolExecutor
                lambda: DB_BOOKS.search_pop_books(
                    user_params.Lang, user_params.BookSize, user_params.Rating,
                    days
                )
            )
        else:
            books = await asyncio.get_event_loop().run_in_executor(
                None,  # Используем стандартный ThreadPoolExecutor
                lambda: DB_BOOKS.search_books(
                    query_text, user_params.Lang, user_params.BookSize, user_params.Rating,
                    search_area=user_params.SearchArea,
                    series_id=series_id,
                    author_id=author_id
                )
            )
        found_books_count = len(books)

        duration_ms = int((time() - start_time) * 1000)

        # Структурированное логирование
        user_id, chat_id = ContextManager._get_ids_from_context(context)
        # Логгируем поиск популярных книг тут
        search_type = SEARCH_TYPE_BOOKS if switch_search else user_params.SearchType
        search_area = switch_search if switch_search else user_params.SearchArea

        structured_logger.log_search(
            user_id=user_id,
            username=user.username or user.first_name or "Unknown",
            query=query_text,
            search_type=search_type,
            search_area=search_area,
            results_count=len(books),
            duration_ms=duration_ms,
            chat_type="private" if user_id == chat_id else "group",  # или определить из context
            chat_id=chat_id,
            # Фильтры
            lang=user_params.Lang,
            rating_filter=user_params.Rating,
            size_limit=user_params.BookSize,
            series_id=series_id,
            author_id=author_id
        )

        # Обрабатываем результаты
        await process_search_books(context, books, found_books_count, processing_msg, query_text, user, author_id)

    except Exception as e:
        # Обработка ошибок
        await processing_msg.edit_text(f"❌ Ошибка при поиске: {str(e)}")


async def process_search_books(context: CallbackContext, books, found_books_count: int, processing_msg, query_text: str,
                               user, author_id=0):
    """Обработка и отображение результатов поиска"""
    series_name = None
    author_name = None
    user_params = get_user_params(context)
    # Популярные
    show_pop = get_switch_search(context)
    # Группировка выдачи только не для новинок и популярных! Для них только по книгам
    search_type = user_params.SearchType if not show_pop else SEARCH_TYPE_BOOKS
    # Область поиска
    search_area = user_params.SearchArea
    # Проверяем, найдены ли книги
    if books:
        # Извлекаем из контекста или БД настройки пользователя
        pages_of_result = [books[i:i + user_params.MaxBooks] for i in range(0, len(books), user_params.MaxBooks)]
        page = 0

        # Собираем кнопки с книгами для настроенного вывода
        keyboard = create_books_keyboard(page, pages_of_result, search_type)

        if search_type == SEARCH_TYPE_SERIES:
            # Извлекаем имя серии из данных первой книги
            series_name = books[0].SeriesTitle
            set_current_series_name(context, series_name)
        elif search_type == SEARCH_TYPE_AUTHORS:
            # Имя автора из первой книги
            author_name = f"{books[0].LastName} {books[0].FirstName} {books[0].MiddleName}"
            set_current_author_name(context, author_name)
            # Сохраняем id автора для перелистывания страниц книг автора
            set_current_author_id(context, author_id)
            # Добавляем кнопку "Об авторе"
            keyboard.append([InlineKeyboardButton("👤 Об авторе", callback_data=f"author_info:{author_id}")])

        # формируем клавиатуру
        reply_markup = InlineKeyboardMarkup(keyboard)

        if reply_markup:

            header_found_text = form_header_books(
                page, user_params.MaxBooks, found_books_count,
                search_type=SEARCH_TYPE_BOOKS,  # Здесь всегда найденных книг
                series_name=series_name,
                author_name=author_name,
                search_area=search_area,
                show_pop=show_pop
            )
            # Заменяем сообщение об ожидании на результаты
            await processing_msg.edit_text(header_found_text, reply_markup=reply_markup)

            set_books(context, pages_of_result, found_books_count)
            set_last_activity(context, datetime.now())  # Сохраняем время поиска
            # СОХРАНЯЕМ ID СООБЩЕНИЯ С РЕЗУЛЬТАТАМИ И ЗАПРОС
            set_last_bot_message_id(context, processing_msg.message_id)
            set_last_search_query(context, query_text)
    else:
        await processing_msg.edit_text(
            t('search.no_results', context),
            parse_mode=ParseMode.HTML
        )

    # if show_pop:
    #     by = ' popular'
    # elif search_type == SEARCH_TYPE_SERIES:
    #     by = f' in series {series_name}'
    # elif search_type == SEARCH_TYPE_AUTHORS:
    #     by = f' for author {author_name}'
    # elif search_area == SETTING_SEARCH_AREA_B:
    #     by = ' by book info'
    # elif search_area == SETTING_SEARCH_AREA_BA:
    #     by = ' by book annotation'
    # else:
    #     by = ''
    #
    # logger.log_user_action(user, "searched for books" + by, f"{query_text}; count:{found_books_count}")


async def handle_search_series(update: Update, context: CallbackContext):
    """Обрабатывает текстовые сообщения (поиск книг)"""
    # ОПРЕДЕЛЯЕМ ТИП СООБЩЕНИЯ
    is_edited = update.edited_message is not None
    message = update.edited_message if is_edited else update.message  # if update.message else update.callback_query.message
    query_text = message.text
    user = message.from_user

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

    processing_msg = await message.reply_text(
        t('search.loading_series', context),
        parse_mode=ParseMode.HTML,
        disable_notification=True
    )

    # Запускаем асинхронный поиск
    asyncio.create_task(
        async_search_series(context, query_text, processing_msg, user)
    )


async def async_search_series(context: CallbackContext, query_text: str, processing_msg, user):
    try:
        start_time = time()
        # Извлекаем настройки пользователя из контекста или БД
        user_params = get_user_params(context)

        # Ищем серии
        series = await asyncio.get_event_loop().run_in_executor(
            None,  # Используем стандартный ThreadPoolExecutor
            lambda: DB_BOOKS.search_series(
                query_text, user_params.Lang, user_params.BookSize, user_params.Rating,
                search_area=user_params.SearchArea
            )
        )
        found_series_count = len(series)

        duration_ms = int((time() - start_time) * 1000)

        # Структурированное логирование
        user_id, chat_id = ContextManager._get_ids_from_context(context)
        structured_logger.log_search(
            user_id=user_id,
            username=user.username or user.first_name or "Unknown",
            query=query_text,
            search_type=user_params.SearchType,
            search_area=user_params.SearchArea,
            results_count=len(series),
            duration_ms=duration_ms,
            chat_type="private" if user_id == chat_id else "group",  # или определить из context
            chat_id=chat_id,
            # Фильтры
            lang=user_params.Lang,
            rating_filter=user_params.Rating,
            size_limit=user_params.BookSize
        )

        # Обрабатываем результаты
        await process_search_series(context, series, found_series_count, processing_msg, query_text, user)

    except Exception as e:
        # Обработка ошибок
        await processing_msg.edit_text(f"❌ Ошибка при поиске: {str(e)}")


async def process_search_series(context: CallbackContext, series, found_series_count: int, processing_msg,
                                query_text: str, user):
    """Поиск книг с группировкой по сериям"""
    user_params = get_user_params(context)
    search_area = user_params.SearchArea
    if series:
        # Извлекаем из контекста или БД настройки пользователя

        pages_of_series = [series[i:i + user_params.MaxBooks] for i in range(0, len(series), user_params.MaxBooks)]
        page = 0
        keyboard = create_series_keyboard(page, pages_of_series)
        reply_markup = InlineKeyboardMarkup(keyboard)

        if reply_markup:
            header_found_text = form_header_books(
                page, user_params.MaxBooks, found_series_count, SEARCH_TYPE_SERIES,
                search_area=search_area
            )
            await processing_msg.edit_text(header_found_text, reply_markup=reply_markup)

            set_series(context, pages_of_series, found_series_count)
            set_last_series_page(context, page)  # Сохраняем текущую страницу
            set_last_activity(context, datetime.now())  # Сохраняем время поиска
            # СОХРАНЯЕМ ID СООБЩЕНИЯ С РЕЗУЛЬТАТАМИ И ЗАПРОС
            set_last_bot_message_id(context, processing_msg.message_id)
            set_last_search_query(context, query_text)
    else:
        await processing_msg.edit_text(
            t('search.no_results_series', context),
            parse_mode=ParseMode.HTML
        )

    # by = ''
    # if search_area == SETTING_SEARCH_AREA_B:
    #     by = ' by book info'
    # elif search_area == SETTING_SEARCH_AREA_BA:
    #     by = ' by book annotation'
    #
    # logger.log_user_action(user, "searched for series" + by, f"{query_text}; count:{found_series_count}")


async def handle_search_series_books(query, context, action, params):
    """Показывает книги выбранной серии"""
    try:
        series_id = int(params[0])
        user = query.from_user
        # Ищем книги серии в комбинации с предыдущим запросом
        query_text = get_last_search_query(context)

        # Запускаем асинхронный поиск
        asyncio.create_task(
            async_search_books(context, query_text, query.message if query.message else query, user, series_id=series_id)
        )

        # # Извлекаем настройки пользователя из контекста или БД
        # user_params = get_user_params(context)
        #
        # # print(f"DEBUG: query_text = {query_text}")
        #
        # books = DB_BOOKS.search_books(
        #     query_text, user_params.Lang, user_params.BookSize, user_params.Rating,
        #     search_area=user_params.SearchArea,
        #     series_id=series_id  # Добавляем ограничение по выбранной серии
        # )
        # found_books_count = len(books)
        #
        # if books:
        #     pages_of_books = [books[i:i + user_params.MaxBooks] for i in range(0, len(books), user_params.MaxBooks)]
        #     set_books(context, pages_of_books, found_books_count)
        #     set_last_activity(context, datetime.now())  # Сохраняем время поиска
        #     # Извлекаем имя серии из данных первой книги
        #     series_name = books[0].SeriesTitle
        #     set_current_series_name(context, series_name)
        #
        #     page = 0
        #     keyboard = create_books_keyboard(page, pages_of_books, SEARCH_TYPE_SERIES)
        #
        #     if keyboard:
        #         reply_markup = InlineKeyboardMarkup(keyboard)
        #
        #         header_text = form_header_books(
        #             page, user_params.MaxBooks, found_books_count, SEARCH_TYPE_BOOKS,
        #             series_name=series_name,
        #             search_area=user_params.SearchArea
        #         )
        #         await query.edit_message_text(header_text, reply_markup=reply_markup)
        # else:
        #     await query.edit_message_text(f"Не найдено книг в серии '{series_id}'")

    except (ValueError, IndexError) as e:
        print(f"Ошибка при обработке серии: {e}")
        await query.edit_message_text(t('search.series_error', context))


async def handle_search_authors(update: Update, context: CallbackContext):
    """Обрабатывает текстовые сообщения (поиск авторов)"""
    is_edited = update.edited_message is not None
    message = update.edited_message if is_edited else update.message  # if update.message else update.callback_query.message
    query_text = message.text
    user = message.from_user

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

    processing_msg = await message.reply_text(
        t('search.loading_authors', context),
        parse_mode=ParseMode.HTML,
        disable_notification=True
    )
    # Запускаем асинхронный поиск
    asyncio.create_task(
        async_search_authors(context, query_text, processing_msg, user)
    )


async def async_search_authors(context: CallbackContext, query_text: str, processing_msg, user):
    try:
        start_time = time()
        # Извлекаем настройки пользователя из контекста или БД
        user_params = get_user_params(context)

        # Ищем авторов
        authors = await asyncio.get_event_loop().run_in_executor(
            None,  # Используем стандартный ThreadPoolExecutor
            lambda: DB_BOOKS.search_authors(
                query_text, user_params.Lang, user_params.BookSize, user_params.Rating,
                search_area=user_params.SearchArea
            )
        )
        found_authors_count = len(authors)

        duration_ms = int((time() - start_time) * 1000)

        # Структурированное логирование
        user_id, chat_id = ContextManager._get_ids_from_context(context)
        structured_logger.log_search(
            user_id=user_id,
            username=user.username or user.first_name or "Unknown",
            query=query_text,
            search_type=user_params.SearchType,
            search_area=user_params.SearchArea,
            results_count=len(authors),
            duration_ms=duration_ms,
            chat_type="private" if user_id == chat_id else "group",  # или определить из context
            chat_id=chat_id,
            # Фильтры
            lang=user_params.Lang,
            rating_filter=user_params.Rating,
            size_limit=user_params.BookSize
        )

        # Обрабатываем результаты
        await process_search_authors(context, authors, found_authors_count, processing_msg, query_text, user)

    except Exception as e:
        # Обработка ошибок
        await processing_msg.edit_text(f"❌ Ошибка при поиске: {str(e)}")


async def process_search_authors(context: CallbackContext, authors, found_authors_count: int, processing_msg,
                                 query_text: str, user):
    # Обрабатываем результаты
    user_params = get_user_params(context)
    search_area = user_params.SearchArea
    if authors:
        # Извлекаем из контекста или БД настройки пользователя
        pages_of_authors = [authors[i:i + user_params.MaxBooks] for i in range(0, len(authors), user_params.MaxBooks)]
        page = 0
        keyboard = create_authors_keyboard(page, pages_of_authors)
        reply_markup = InlineKeyboardMarkup(keyboard)

        if reply_markup:
            header_found_text = form_header_books(
                page, user_params.MaxBooks, found_authors_count, SEARCH_TYPE_AUTHORS,
                search_area=search_area
            )
            await processing_msg.edit_text(header_found_text, reply_markup=reply_markup)

            set_authors(context, pages_of_authors, found_authors_count)
            set_last_authors_page(context, page)  # Сохраняем текущую страницу
            set_last_activity(context, datetime.now())  # Сохраняем время поиска
            # СОХРАНЯЕМ ID СООБЩЕНИЯ С РЕЗУЛЬТАТАМИ И ЗАПРОС
            set_last_bot_message_id(context, processing_msg.message_id)
            set_last_search_query(context, query_text)
    else:
        await processing_msg.edit_text(
            t('search.no_results_authors', context),
            parse_mode=ParseMode.HTML
        )

    # if search_area == SETTING_SEARCH_AREA_B:
    #     by = ' by book info'
    # elif search_area == SETTING_SEARCH_AREA_BA:
    #     by = ' by book annotation'
    # else:
    #     by = ''
    #
    # logger.log_user_action(user, "searched for authors" + by, f"{query_text}; count:{found_authors_count}")


async def handle_search_author_books(query, context, action, params):
    """Показывает книги выбранного автора"""
    try:
        author_id = int(params[0])
        user = query.from_user
        # Ищем книги автора в комбинации с предыдущим запросом
        query_text = get_last_search_query(context)

        # Запускаем асинхронный поиск
        asyncio.create_task(
            async_search_books(context, query_text, query.message if query.message else query, user, author_id=author_id)
        )

        # # user_params = DB_SETTINGS.get_user_settings(user.id)
        # user_params = get_user_params(context)
        #
        # books = DB_BOOKS.search_books(
        #     query_text, user_params.Lang, user_params.BookSize, user_params.Rating,
        #     search_area=user_params.SearchArea,
        #     author_id=author_id  # Добавляем ограничение по автору для поиска книг выбранного автора
        # )
        # found_books_count = len(books)
        #
        # if books:
        #     pages_of_books = [books[i:i + user_params.MaxBooks] for i in range(0, len(books), user_params.MaxBooks)]
        #     set_books(context, pages_of_books, found_books_count)
        #     set_last_activity(context, datetime.now())
        #     set_current_author_id(context, author_id)
        #
        #     # Имя автора из первой книги
        #     author_name = f"{books[0].LastName} {books[0].FirstName} {books[0].MiddleName}"
        #     set_current_author_name(context, author_name)
        #
        #     page = 0
        #     keyboard = create_books_keyboard(page, pages_of_books, SEARCH_TYPE_AUTHORS)
        #     keyboard.append([InlineKeyboardButton("👤 Об авторе", callback_data=f"author_info:{author_id}")])
        #
        #     if keyboard:
        #         reply_markup = InlineKeyboardMarkup(keyboard)
        #         header_text = form_header_books(
        #             page, user_params.MaxBooks, found_books_count, SEARCH_TYPE_BOOKS,
        #             author_name=author_name,
        #             search_area=user_params.SearchArea
        #         )
        #         await query.edit_message_text(header_text, reply_markup=reply_markup)
        # else:
        #     await query.edit_message_text(f"Не найдено книг автора '{author_id}'")
        #
        # logger.log_user_action(user, "searched for books", f"{query_text}; count:{found_books_count}")

    except (ValueError, IndexError) as e:
        print(f"Ошибка при обработке автора: {e}")
        await query.edit_message_text(t('search.author_error', context))


async def handle_books_page_change(query, context, action, params):
    """Обрабатывает смену страницы с проверкой данных"""
    try:
        # Проверяем, что данные поиска еще существуют
        pages_of_books = get_pages_of_books(context)
        if not pages_of_books:
            await query.edit_message_text(t('search.session_expired', context))
            return

        page = int(action.removeprefix(f"{SEARCH_TYPE_BOOKS}_page_"))
        # Определяем контекст поиска
        user_params = get_user_params(context)
        # если показ новинок/популярных, то клавиатура только по книгам
        show_pop = get_switch_search(context)
        search_context = user_params.SearchType if not show_pop else SEARCH_TYPE_BOOKS
        # print(f"DEBUG: {show_pop}, {search_context}")
        keyboard = create_books_keyboard(page, pages_of_books, search_context)
        if search_context == SEARCH_TYPE_AUTHORS:
            author_id = get_current_author_id(context)
            keyboard.append([InlineKeyboardButton(t('search.author_about', context), callback_data=f"author_info:{author_id}")])

        reply_markup = InlineKeyboardMarkup(keyboard)

        if reply_markup:
            found_books_count = get_found_books_count(context)
            # Формируем заголовок в зависимости от контекста
            series_name = None
            author_name = None
            if search_context == SEARCH_TYPE_SERIES:
                series_name = get_current_series_name(context)
            elif search_context == SEARCH_TYPE_AUTHORS:
                author_name = get_current_author_name(context)
            show_pop = get_switch_search(context)
            header_text = form_header_books(
                page, user_params.MaxBooks, found_books_count, SEARCH_TYPE_BOOKS,
                series_name=series_name,
                author_name=author_name,
                search_area=user_params.SearchArea,
                show_pop=show_pop
            )
            await query.edit_message_text(header_text, reply_markup=reply_markup)

    except ValueError:
        await query.answer(t('search.page_error', context))
    except Exception as e:
        print(f"Error in page change: {e}")
        await query.answer(t('search.page_change_error', context))

    # logger.log_user_action(query.from_user, "changed page of books", page)


async def handle_series_page_change(query, context, action, params):
    try:
        # Проверяем, что данные серий еще существуют
        pages_of_series = get_pages_of_series(context)
        if not pages_of_series:
            await query.answer(t('search.results_expired', context))
            await query.edit_message_text(
                t('search.results_expired_title', context),
                parse_mode=ParseMode.HTML
            )
            return

        page = int(action.removeprefix(f"{SEARCH_TYPE_SERIES}_page_"))
        keyboard = create_series_keyboard(page, pages_of_series)
        reply_markup = InlineKeyboardMarkup(keyboard)

        if reply_markup:
            found_series_count = get_found_series_count(context)
            user_params = get_user_params(context)
            search_area = user_params.SearchArea
            header_found_text = form_header_books(
                page, user_params.MaxBooks, found_series_count, SEARCH_TYPE_SERIES,
                search_area=search_area
            )
            await query.edit_message_text(header_found_text, reply_markup=reply_markup)

        set_last_series_page(context, page)  # Сохраняем текущую страницу

    except ValueError:
        await query.answer(t('search.page_error', context))
    except Exception as e:
        print(f"Error in series page change: {e}")
        await query.answer(t('search.page_change_error', context))

    # logger.log_user_action(query.from_user, "changed page of series", page)


async def handle_authors_page_change(query, context, action, params):
    """ Обновляем обработчик смены страниц для авторов """
    try:
        # Проверяем, что данные авторов еще существуют
        pages_of_authors = get_pages_of_authors(context)
        if not pages_of_authors:
            await query.answer(t('search.results_expired', context))
            await query.edit_message_text(
                t('search.results_expired_title', context),
                parse_mode=ParseMode.HTML
            )
            return

        page = int(action.removeprefix(f"{SEARCH_TYPE_AUTHORS}_page_"))
        keyboard = create_authors_keyboard(page, pages_of_authors)
        reply_markup = InlineKeyboardMarkup(keyboard)

        if reply_markup:
            found_authors_count = get_found_authors_count(context)
            user_params = get_user_params(context)
            search_area = user_params.SearchArea
            header_found_text = form_header_books(
                page, user_params.MaxBooks, found_authors_count, SEARCH_TYPE_AUTHORS,
                search_area=search_area
            )
            await query.edit_message_text(header_found_text, reply_markup=reply_markup)

        set_last_authors_page(context, page)

    except ValueError:
        await query.answer(t('search.page_error', context))
    except Exception as e:
        print(f"Error in authors page change: {e}")
        await query.answer(t('search.page_change_error', context))

    # logger.log_user_action(query.from_user, "changed page of authors", page)
