import html

# from bs4 import BeautifulSoup
import importlib.util
import os
import re
import sys
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional, Tuple
import aiohttp

# from urllib.parse import unquote
from .constants import (
    HEADING_POP,
    SEARCH_TYPE_AUTHORS,
    SEARCH_TYPE_BOOKS,
    SEARCH_TYPE_SERIES,
    SETTING_SEARCH_AREA_AA,
    SETTING_SEARCH_AREA_B,
    SETTING_SEARCH_AREA_BA,
)
from .flibusta_client import FlibustaClient
from .core.structured_logger import structured_logger
from .i18n import t, tp

# Пространство имен FB2
FB2_NAMESPACE = "http://www.gribuser.ru/xml/fictionbook/2.0"
XLINK_NAMESPACE = "http://www.w3.org/1999/xlink"

# Словарь с пространствами имен для использования в XPath
NAMESPACES = {
    "fb": FB2_NAMESPACE,
    "xlink": XLINK_NAMESPACE,
}

# Имя бота из переменной окружения
BOT_USERNAME = os.getenv("BOT_USERNAME", "")


def format_size(size_in_bytes: int) -> str:
    units = ["B", "K", "M", "G", "T"]
    unit_index = 0
    while size_in_bytes >= 1024 and unit_index < len(units) - 1:
        size_in_bytes /= 1024
        unit_index += 1
    return f"{size_in_bytes:.1f}{units[unit_index]}"


def form_header_books(
    context,
    page,
    max_books,
    found_count,
    search_type=SEARCH_TYPE_BOOKS,
    series_name=None,
    author_name=None,
    search_area=SETTING_SEARCH_AREA_B,
    show_pop=None,
):
    """Оформление заголовка сообщения с результатом поиска книг"""
    start = max_books * page + 1
    end = min(max_books * (page + 1), found_count)

    pop = t(HEADING_POP.get(show_pop), context) if show_pop else ""
    object = tp(f"search.results.{search_type}",context,found_count)
    filter = t("search.results.filter_series",context,series=series_name) if series_name else ""
    filter += t("search.results.filter_author",context,author=author_name) if author_name else ""
    in_str = f" {t(f"common.search_areas.{search_area}",context)}" if search_area != SETTING_SEARCH_AREA_B and not show_pop else ""

    return t("search.results.header",context,start=start,end=end,total=found_count,pop=pop,object=object,filter=filter,in_str=in_str)

    # text = f"{HEADING_POP.get(show_pop)} " if show_pop else ""
    #
    # if search_type == SEARCH_TYPE_BOOKS or show_pop:
    #     text += "книг"
    # elif search_type == SEARCH_TYPE_SERIES:
    #     text += "серий"
    # elif search_type == SEARCH_TYPE_AUTHORS:
    #     text += "авторов"
    #
    # header = f"Показываю с {start} по {end} из {found_count} найденных {text}"
    #
    # header += f" в серии '{series_name}'" if series_name else ""
    # header += f" автора '{author_name}'" if author_name else ""
    # header += " по аннотации книги" if search_area == SETTING_SEARCH_AREA_BA and not show_pop else ""
    # header += " по аннотации автора" if search_area == SETTING_SEARCH_AREA_AA and not show_pop else ""
    #
    # return header


# def get_platform_recommendations() -> str:
#     """
#     Возвращает рекомендации для всех платформ
#     (универсальный подход, так как определить платформу сложно)
#     """
#     return """
# 📱 <b>Рекомендуемые читалки для всех платформ:</b>
# <u>Для Android:</u>
# • 📖 <a href="https://play.google.com/store/apps/details?id=org.readera">ReadEra</a> - лучшая бесплатная
# • 📚 <a href="https://play.google.com/store/apps/details?id=com.flyersoft.moonreader">Moon+ Reader</a>
# • 🔥 <a href="https://play.google.com/store/apps/details?id=com.amazon.kindle">Kindle</a>
#
# <u>Для iOS:</u>
# • 📖 <a href="https://apps.apple.com/ru/app/readera-читалка-книг-pdf/id1441824222">ReadEra</a>
# • 📚 <a href="https://apps.apple.com/ru/app/kybook-3-ebook-reader/id1259787028">KyBook 3</a>
# • 🔥 <a href="https://apps.apple.com/ru/app/amazon-kindle/id302584613">Kindle</a>
#
# <u>Для компьютера:</u>
# • 📚 <a href="https://www.calibre-ebook.com/">Calibre</a> (Windows/Mac/Linux)
# • 📘 <a href="https://apps.apple.com/ru/app/apple-books/id364709193">Apple Books</a> (Mac)
# • 📖 <a href="https://www.amazon.com/b?node=16571048011">Kindle</a> (все платформы)
# """


# ===== СЛУЖЕБНЫЕ ФУНКЦИИ =====


async def upload_to_tmpfiles(file, file_name: str) -> Optional[str]:
    """Загружает файл на tmpfiles.org и возвращает URL для скачивания"""
    try:
        async with aiohttp.ClientSession() as session:
            form_data = aiohttp.FormData()
            form_data.add_field("file", file, filename=file_name)
            params = {"duration": "15m"}

            async with session.post("https://tmpfiles.org/api/v1/upload", data=form_data, params=params) as response:
                if response.status == 200:
                    result = await response.json()
                    return result["data"]["url"]
                return None
    except Exception as e:
        print(f"Ошибка загрузки: {e}")
        return None


# ===== ВСПОМОГАТЕЛЬНЫЕ ОБРАБОТЧИКИ ДЛЯ ГРУППОВОГО ЧАТА =====


def is_message_for_bot(message_text, bot_username):
    """Проверяет, обращается ли пользователь к боту"""
    if not bot_username:
        return False

    # Проверяем упоминание бота в начале сообщения
    return message_text.startswith(f"@{bot_username}")


def extract_clean_query(message_text, bot_username):
    """Извлекает чистый поисковый запрос из сообщения"""
    if not bot_username:
        return message_text.strip()

    # Убираем упоминание бота
    clean_text = message_text.replace(f"@{bot_username}", "").strip()

    return clean_text


# ===== ЗАГРУЗКА НОВОСТЕЙ ИЗ PYTHON ФАЙЛА =====


async def load_bot_news(file_path: str) -> List[Dict[str, Any]]:
    """Загружает новости бота из Python файла"""
    try:
        # Принудительно удаляем модуль из кэша, если он уже был загружен
        if "bot_news" in sys.modules:
            del sys.modules["bot_news"]

        # Динамически импортируем модуль с новостями
        spec = importlib.util.spec_from_file_location("bot_news", file_path)
        if spec is None or spec.loader is None:
            structured_logger.log_error(
                error_type="news_load_failed",
                error_message="Error loading bot_news.py: spec is None"
            )
            return []
        news_module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(news_module)

        news = getattr(news_module, "BOT_NEWS", [])
        print(f"Загружено {len(news)} новостей из {file_path}")
        return news

    except FileNotFoundError:
        print(f"Файл новостей {file_path} не найден")
        return []
    except Exception as e:
        print(f"Ошибка загрузки новостей из {file_path}: {e}")
        return []


async def get_latest_news(file_path: str, count: int = 3) -> List[Dict[str, Any]]:
    """Возвращает последние count новостей"""
    all_news = await load_bot_news(file_path)
    return all_news[-count:] if all_news else []


# ===== ФОРМАТИРОВАНИЕ ВЫВОДА =====
def truncate_text(text: str, no_more_len: int, stop_sep: str) -> str:
    if len(text) <= no_more_len:
        return text
    else:
        # Обрезаем до no_more_len символов и ищем последний stop символ
        truncated = text[:no_more_len]
        last_stop_char = truncated.rfind(stop_sep)
        if last_stop_char != -1:
            return truncated[:last_stop_char] + "..."
        else:
            # Если запятых нет — значит, один очень длинный текст
            return truncated + "..."


def format_links_from_flat_string(url_routine, flat_str: str, max_num_elem: int) -> Tuple[str, bool]:
    if not flat_str:
        return "", False

    parts = [part.strip() for part in flat_str.split(",") if part.strip()]
    orig_len = len(parts)
    parts = parts[:max_num_elem]
    trunc_len = len(parts)

    # Если нечётное количество — отбрасываем последний непарный элемент
    if len(parts) % 2 != 0:
        parts = parts[:-1]

    links = []
    for i in range(0, len(parts), 2):
        try:
            elem_id = int(parts[i])
            elem_name = parts[i + 1]
            url = url_routine(elem_id)
            links.append(f"<a href='{url}'>{elem_name}</a>")
        except (ValueError, IndexError):
            # Пропускаем некорректные пары
            continue

    return ", ".join(links), orig_len != trunc_len


def format_book_info(book_info, context):
    """Форматирует информацию о книге для сообщения"""
    text = f"📚 <b><a href='{FlibustaClient.get_book_url(book_info['bookid'])}'>{book_info['title']}</a></b>\n"
    # authors = book_info['authors'][:300] + ("..." if len(book_info['authors']) > 300 else "")
    author_links, is_truncated = format_links_from_flat_string(FlibustaClient.get_author_url, book_info["authors"], 20)
    text += f"\n{t("book.authors",context)} {(author_links + (',...' if is_truncated else '')) or t("book.not_specified", context)}"
    year = book_info["year"]
    series = book_info["series"]
    genre_links, is_truncated = format_links_from_flat_string(FlibustaClient.get_genre_url, book_info["genres"], 10)
    lang = book_info["lang"]
    pages = book_info["pages"]
    rate = book_info["rate"]
    # book_id = book_info['bookid']
    series_id = book_info["seqid"]
    if genre_links:
        text += f"\n{t("book.genres",context)} {(genre_links + (',...' if is_truncated else '')) or t("book.not_specified", context)}"
    if series:
        text += f"\n{t("book.series",context)} <a href='{FlibustaClient.get_series_url(series_id)}'>{series}</a>"
    if year and year != 0:
        text += f"\n{t("book.year",context)} {year}"
    if lang:
        text += f"\n{t("book.language",context)} {lang}"
    if pages:
        text += f"\n{t("book.pages",context)} {pages}"
    size = format_size(book_info["size"])
    text += f"\n{t("book.size",context)} {size}"
    if rate:
        text += f"\n{t("book.rating",context)} {rate:.1f}"
    # if book_id:
    #     text += f"\n🔑 <b>ID:</b> <a href='{FlibustaClient.get_book_url(book_id)}'>{book_id}</a>"
    return text


def format_book_details(book_details, context):
    """Форматирует детальную информацию о книге"""
    text = f"{t("book.annotation_title",context)} {book_details.get('title', t("book.unknown",context))}\n\n"
    if book_details.get("annotation"):
        # Очищаем HTML теги для телеграма
        clean_annotation = clean_html_tags(book_details["annotation"])
        # text += f"{clean_annotation[:4000]}" + ("..." if len(clean_annotation) > 4000 else "")
        text += clean_annotation

    return truncate_text(text, 4000, ".")


def format_author_info(author_info, context):
    """Форматирует информацию об авторе"""
    text = f"{t("author.about_title",context)} <a href='{FlibustaClient.get_author_url(author_info['author_id'])}'>{author_info['name']}</a>\n\n"
    if author_info.get("biography"):
        clean_bio = clean_html_tags(author_info["biography"])
        # text += f"{clean_bio[:4000]}" + ("..." if len(clean_bio) > 4000 else "")
        text += clean_bio

    return truncate_text(text, 4000, ".")


def format_book_reviews(reviews, context):
    """Форматирует отзывы о книге"""
    text = f"{t("book.reviews_title",context)}\n\n"

    for name, time, review_text in reviews[:50]:
        reviewer = f"👤 <b>{name}</b> ({time})\n"
        clean_review = clean_html_tags(review_text)
        clean_review_trunc = f"{clean_review[:1000]}" + ("..." if len(clean_review) > 1000 else "") + "\n"
        if len(text + reviewer + clean_review_trunc) > 4000:
            break
        text += reviewer
        text += clean_review_trunc

    return text


def clean_html_tags(text: str) -> str:
    """Удаляем html-теги и очищаем от лишнего мусора"""
    clean_text = text
    clean_text = re.sub(r"<br\s*/?>", "\n", clean_text)  # <br> → перенос
    clean_text = re.sub(r"</?p[^>]*>", "\n", clean_text)  # <p> → перенос
    clean_text = re.sub(r"<[^<]+?>", "", clean_text)
    clean_text = re.sub(r"\[[^\]]*?\]", "", clean_text)  # Квадратные скобки
    # Убираем множественные переносы
    clean_text = re.sub(r"\n\s*\n", "\n\n", clean_text)
    clean_text = html.escape(clean_text)
    clean_text = clean_text.strip()
    return clean_text


def get_short_donation_notice(context):
    # Получаем дату окончания из переменных окружения
    end_date_str = os.getenv("VPS_EXPIRY_DATE", "2026-03-26")
    end_date = datetime.strptime(end_date_str, "%Y-%m-%d")
    days_left = (end_date - datetime.now()).days

    return (
        t("donate.vps_expiry", context, days_left=days_left, end_date_str=end_date_str)
        + t("donate.vps_appeal", context)
    )
