from telegram import InlineKeyboardButton
from telegram.constants import ParseMode
from telegram.error import TimedOut
from telegram.ext import CallbackContext

from .context import get_user_params
from .constants import  BOOK_RATINGS, SEARCH_TYPE_BOOKS, SEARCH_TYPE_SERIES, SEARCH_TYPE_AUTHORS, \
    DEFAULT_BOOK_FORMAT #,FLIBUSTA_BASE_URL
from .tools import format_size, upload_to_tmpfiles,  get_short_donation_notice
from .core.structured_logger import structured_logger
from .flibusta_client import flibusta_client, FlibustaClient

# ===== УТИЛИТЫ И ХЕЛПЕРЫ =====
async def handle_send_file(query, context, action, params, for_user = None):
    """Обрабатывает отправку файла"""
    book_id = int(params[0])
    user_params = get_user_params(context)
    book_format = user_params.BookFormat if user_params else DEFAULT_BOOK_FORMAT

    public_filename = await process_book_download(query, context, book_id, book_format, for_user)

    # log_detail = f"{book_id}.{book_format}"
    # log_detail += ":" + public_filename if public_filename else ""
    # logger.log_user_action(query.from_user, "send file", log_detail)


async def process_book_download(query, context, book_id: int, book_format, for_user=None):
    """Обрабатывает скачивание и отправку книги сначала без авторизации на сайте, потом с авторизацией"""
    book_url = FlibustaClient.get_book_url(book_id)
    # book_title = get_book_title_safe(context, book_id)

    try:
        processing_msg = await query.message.reply_text(
            "⏰ <i>Ожидайте, отправляю книгу" + (f" для {for_user.first_name}" if for_user else "") + "...</i>",
            parse_mode=ParseMode.HTML,
            disable_notification=True
        )

        # Первая попытка — без авторизации
        book_data, original_filename = await flibusta_client.download_book(book_id, book_format, auth=False)
        public_filename = original_filename if original_filename else f"{book_id}.{book_format}"

        # Если не удалось — вторая попытка с авторизацией
        if not book_data:
            book_data, original_filename = await flibusta_client.download_book(book_id, book_format, auth=True)
            public_filename = original_filename if original_filename else f"{book_id}.{book_format}"

        if book_data:
            # Сообщение об истечении срока аренды vps
            message = get_short_donation_notice()

            await query.message.reply_document(
                document=book_data,
                filename=public_filename,
                disable_notification=True,
                caption=message,
                parse_mode=ParseMode.MARKDOWN
            )

            # ✅ ЛОГИРОВАНИЕ УСПЕШНОГО СКАЧИВАНИЯ
            structured_logger.log_download(
                user_id=query.from_user.id,
                username=query.from_user.username or query.from_user.first_name or "Unknown",
                book_id=book_id,
                book_title="", # TODO: substitute with book title
                format=book_format,
                file_size=len(book_data) if book_data else 0,
                success=True,
                via_tmpfiles=False,
                chat_type="private",
                chat_id=query.from_user.id
            )

        else:
            await query.message.reply_text(
                "😞 Не удалось скачать книгу в этом формате" + (f" для {for_user.first_name}" if for_user else ""),
                disable_notification=True
            )

        await processing_msg.delete()
        return public_filename

    except TimedOut:
        await handle_timeout_error(processing_msg, book_data, book_id, book_format, query)

        structured_logger.log_download(
            user_id=query.from_user.id,
            username=query.from_user.username or query.from_user.first_name or "Unknown",
            book_id=book_id,
            book_title="",  # TODO: substitute with book title
            format=book_format,
            file_size=len(book_data),
            success=True,
            via_tmpfiles=True,
            chat_type="private",
            chat_id=query.from_user.id
        )

    except Exception as e:
        """Обрабатывает ошибку загрузки"""
        print(f"Общая ошибка при отправке книги: {e}")
        await processing_msg.edit_text(
            f"❌ Произошла ошибка при подготовке книги {book_url}. Возможно она доступна только в локальной базе"
        )
        # logger.log_user_action(query.from_user.id, "error sending book direct", book_url)
        structured_logger.log_error(
            error_type="download_failed",
            error_message=str(e),
            context={
                "book_id": book_id,
                "format": format
            },
            user_id=query.from_user.id,
            username=query.from_user.username or query.from_user.first_name or "Unknown"
        )

    return None


async def handle_timeout_error(processing_msg, book_data, file_name, file_ext, query):
    """Обрабатывает ошибку таймаута"""
    await processing_msg.edit_text(
        "⏳ Книга большая, использую внешний сервис...",
        parse_mode=ParseMode.HTML
    )

    try:
        download_url = await upload_to_tmpfiles(book_data, f"{file_name}.{file_ext}")
        if download_url:
            direct_download_url = download_url.replace(
                "https://tmpfiles.org/",
                "https://tmpfiles.org/dl/",
                1
            )
            message = (
                f"<a href='{direct_download_url}'>📥 Скачать книгу</a>\n"
                "⏳ Ссылка действительна 15 минут"
            )
            await query.message.reply_text(
                text=message,
                parse_mode=ParseMode.HTML,
                disable_web_page_preview=True,
                disable_notification=True
            )
    except Exception as upload_error:
        print(f"Ошибка загрузки на tmpfiles: {upload_error}")
        await processing_msg.edit_text("❌ Не удалось отправить книгу. Попробуйте позже.")
        structured_logger.log_error(
            error_type="upload_failed",
            error_message="Failed to upload book to cloud storage",
            context={
                "file_name": file_name,
                "file_ext": file_ext
            },
            user_id=query.from_user.id,
            username=query.from_user.username or query.from_user.first_name or "Unknown"
        )


async def edit_or_reply_message(query, text, reply_markup=None):
    """Редактирует существующее сообщение или отправляет новое"""
    if hasattr(query.message, 'message_id'):
        await query.edit_message_text(text, reply_markup=reply_markup)
    else:
        await query.message.reply_text(text, reply_markup=reply_markup)


def get_rating_emoji(rating):
    """Возвращает эмодзи для рейтинга"""
    return BOOK_RATINGS.get(rating, ("⚪️", ""))[0]


def create_back_button() -> list:
    """Создает кнопку возврата в настройки"""
    return [[InlineKeyboardButton("⬅ Назад в настройки", callback_data="back_to_settings")]]


def add_close_button(keyboard):
    """Добавляем к клавиатуре кнопку закрытия"""
    return keyboard.append([InlineKeyboardButton("❌ Закрыть", callback_data="close_message")])


# ===== КЛАВИАТУРЫ И ИНТЕРФЕЙС =====
def add_navigation_buttons(keyboard, search_type, page, pages):
    navigation_buttons = []
    if page > 0:
        navigation_buttons.append(InlineKeyboardButton("⬆ В начало", callback_data=f"{search_type}_page_0"))
        navigation_buttons.append(
            InlineKeyboardButton("⬅️ Назад", callback_data=f"{search_type}_page_{page - 1}"))
    if page < len(pages) - 1:
        navigation_buttons.append(
            InlineKeyboardButton("Вперёд ➡️", callback_data=f"{search_type}_page_{page + 1}"))
        navigation_buttons.append(
            InlineKeyboardButton("В конец ⬇️️️", callback_data=f"{search_type}_page_{len(pages) - 1}"))
    if navigation_buttons:
        keyboard.append(navigation_buttons)


def create_books_keyboard(page, pages_of_books, search_context=SEARCH_TYPE_BOOKS):
    """Создание клавиатуры с кнопками книг и кнопками навигации"""
    keyboard = []

    if pages_of_books:
        books_in_page = pages_of_books[page]

        if books_in_page:
            for book in books_in_page:
                # ДОБАВЛЯЕМ ЭМОДЗИ РЕЙТИНГА
                rating_emoji = get_rating_emoji(book.LibRate)
                text = f"{rating_emoji} {book.Title} ({book.LastName} {book.FirstName}) {format_size(book.BookSize)}/{book.Genre}"
                if book.SearchYear != 0:
                    text += f"/{str(book.SearchYear)}"
                keyboard.append([InlineKeyboardButton(
                    text,
                    callback_data = f"book_info:{book.FileName}"
                )])

            # Добавляем кнопки для навигации
            add_navigation_buttons(keyboard, SEARCH_TYPE_BOOKS, page, pages_of_books)

            # Добавляем кнопку "Назад к сериям" только при поиске по сериям
            if search_context == SEARCH_TYPE_SERIES:
                keyboard.append([InlineKeyboardButton("⤴️ Назад к сериям", callback_data="back_to_series")])

            # Добавляем кнопку "Назад к авторам" при поиске по авторам
            elif search_context == SEARCH_TYPE_AUTHORS:
                keyboard.append([InlineKeyboardButton("⤴️ Назад к авторам", callback_data="back_to_authors")])

    return keyboard


def create_series_keyboard(page, pages_of_series):
    """ Создание клавиатуры с кнопками из найденных серий книг """
    keyboard = []

    if pages_of_series:
        series_in_page = pages_of_series[page]

        if series_in_page:
            for idx, (series_name, series_id, book_count) in enumerate(series_in_page):
                text = f"{series_name} ({book_count})"
                keyboard.append([InlineKeyboardButton(
                    text,
                    callback_data = f"show_series:{series_id}"
                )])

            # Добавляем кнопки для навигации
            add_navigation_buttons(keyboard, SEARCH_TYPE_SERIES, page, pages_of_series)

    return keyboard


def create_authors_keyboard(page, pages_of_authors):
    """ создание клавиатуры для авторов """
    keyboard = []

    if pages_of_authors:
        authors_in_page = pages_of_authors[page]

        if authors_in_page:
            for idx, (author_name, book_count, author_id) in enumerate(authors_in_page):
                text = f"{author_name} ({book_count})"
                keyboard.append([InlineKeyboardButton(
                    text,
                    callback_data = f"show_author:{author_id}"
                )])

            # Добавляем кнопки для навигации
            add_navigation_buttons(keyboard, SEARCH_TYPE_AUTHORS, page, pages_of_authors)

    return keyboard


# def get_book_title_safe(context: CallbackContext, book_id: int) -> str:
#     """
#     Получает название книги безопасно (кеш → БД → fallback)
#
#     Args:
#         context: Telegram context
#         book_id: ID книги
#
#     Returns:
#         Название книги или "Book #{book_id}"
#     """
#
#     # 2. Запрашиваем из БД (используем старый DatabaseBooks)
#     try:
#         from database import DB_BOOKS
#
#         # Используем метод connect() старого класса
#         with DB_BOOKS.connect() as conn:
#             cursor = conn.cursor()
#             cursor.execute("SELECT Title FROM cb_libbook WHERE BookID = %s LIMIT 1", (book_id,))
#             result = cursor.fetchone()
#
#             if result and result[0]:
#                 title = str(result[0])
#                 # print(f"DEBUG: get book title from DB")
#                 return title
#     except Exception as e:
#         print(f"Error fetching book title from DB: {e}")
#
#     # 3. Fallback - если всё упало
#     return f"Book #{book_id}"