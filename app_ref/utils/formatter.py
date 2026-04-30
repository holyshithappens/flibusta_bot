"""
Formatter module for Flibusta Bot (New Architecture)

This module contains formatting utilities that are completely independent
from the old FlibustaClient. It uses FlibustaService for URL generation
and integrates with StructuredLogger.

Functions:
    - format_book_info: Format book information with links
    - format_book_details: Format book annotation/details
    - format_author_info: Format author biography
    - format_book_reviews: Format book reviews
    - format_links_from_flat_string: Format comma-separated links
    - clean_html_tags: Clean HTML tags from text
    - truncate_text: Truncate text to specified length
    - format_size: Format file size in human-readable format
"""

import html
import re
from typing import Optional, Tuple, Dict, Any, Callable


def format_size(size_in_bytes: int) -> str:
    """
    Format file size in human-readable format
    
    Args:
        size_in_bytes: Size in bytes
        
    Returns:
        Formatted size string (e.g., "1.5 MB")
    """
    units = ["B", "K", "M", "G", "T"]
    unit_index = 0
    size = float(size_in_bytes)
    
    while size >= 1024 and unit_index < len(units) - 1:
        size /= 1024
        unit_index += 1
    
    return f"{size:.1f}{units[unit_index]}"


def truncate_text(text: str, max_length: int, stop_sep: str = ".") -> str:
    """
    Truncate text to maximum length, trying to stop at sentence boundary
    
    Args:
        text: Text to truncate
        max_length: Maximum length
        stop_sep: Sentence separator (default: ".")
        
    Returns:
        Truncated text with "..." if needed
    """
    if len(text) <= max_length:
        return text
    
    # Try to find a good stopping point
    truncated = text[:max_length]
    last_stop = truncated.rfind(stop_sep)
    
    if last_stop != -1:
        return truncated[:last_stop] + "..."
    else:
        # No good stopping point found
        return truncated + "..."


def clean_html_tags(text: str) -> str:
    """
    Clean HTML tags from text, preserving basic formatting
    
    Args:
        text: Text with HTML tags
        
    Returns:
        Cleaned text
    """
    if not text:
        return ""
    
    clean_text = text
    
    # Replace line breaks
    clean_text = re.sub(r"<br\s*/?>", "\n", clean_text)
    
    # Replace paragraphs
    clean_text = re.sub(r"</?p[^>]*>", "\n", clean_text)
    
    # Remove all other HTML tags
    clean_text = re.sub(r"<[^<]+?>", "", clean_text)
    
    # Remove square brackets content
    clean_text = re.sub(r"\[[^\]]*?\]", "", clean_text)
    
    # Remove excessive newlines
    clean_text = re.sub(r"\n\s*\n", "\n\n", clean_text)
    
    # Escape HTML entities
    clean_text = html.escape(clean_text)
    
    return clean_text.strip()


def format_links_from_flat_string(
    url_generator: Callable[[int], str],
    flat_str: str,
    max_elements: int
) -> Tuple[str, bool]:
    """
    Format links from comma-separated string of ID-name pairs
    
    Args:
        url_generator: Function to generate URLs from IDs
        flat_str: Comma-separated string (id1,name1,id2,name2,...)
        max_elements: Maximum number of elements to process
        
    Returns:
        Tuple of (formatted_links, was_truncated)
    """
    if not flat_str:
        return "", False
    
    # Split and clean parts
    parts = [part.strip() for part in flat_str.split(",") if part.strip()]
    original_count = len(parts)
    
    # Limit to max_elements
    parts = parts[:max_elements]
    was_truncated = original_count != len(parts)
    
    # If odd number, drop the last unpaired element
    if len(parts) % 2 != 0:
        parts = parts[:-1]
    
    # Build links
    links = []
    for i in range(0, len(parts), 2):
        try:
            elem_id = int(parts[i])
            elem_name = parts[i + 1]
            url = url_generator(elem_id)
            links.append(f"<a href='{url}'>{elem_name}</a>")
        except (ValueError, IndexError):
            # Skip invalid pairs
            continue
    
    return ", ".join(links), was_truncated


def format_book_info(
    book_info: Dict[str, Any],
    flibusta_service: Any
) -> str:
    """
    Format book information for display
    
    Args:
        book_info: Dictionary with book details
        flibusta_service: FlibustaService instance for URL generation
        
    Returns:
        Formatted HTML text
    """
    book_id = book_info.get('bookid', 0)
    title = book_info.get('title', 'Unknown Title')
    
    # Start with title
    book_url = flibusta_service.get_book_url(book_id) if flibusta_service else ""
    text = f"📚 <b><a href='{book_url}'>{title}</a></b>\n"
    
    # Authors
    authors = book_info.get('authors', '')
    if authors:
        author_links, author_truncated = format_links_from_flat_string(
            flibusta_service.get_author_url if flibusta_service else (lambda x: ""),
            authors,
            20
        )
        text += f"\n👤 <b>Автор(ы):</b> {(author_links + (',...' if author_truncated else '')) or 'Не указаны'}"
    
    # Genres
    genres = book_info.get('genres', '')
    if genres:
        genre_links, genre_truncated = format_links_from_flat_string(
            flibusta_service.get_genre_url if flibusta_service else (lambda x: ""),
            genres,
            10
        )
        text += f"\n📑 <b>Жанр(ы):</b> {(genre_links + (',...' if genre_truncated else '')) or 'Не указаны'}"
    
    # Series
    series = book_info.get('series', '')
    series_id = book_info.get('seqid', 0)
    if series:
        series_url = flibusta_service.get_series_url(series_id) if flibusta_service else ""
        text += f"\n📖 <b>Серия:</b> <a href='{series_url}'>{series}</a>"
    
    # Year
    year = book_info.get('year', 0)
    if year and year != 0:
        text += f"\n📅 <b>Год:</b> {year}"
    
    # Language
    lang = book_info.get('lang', '')
    if lang:
        text += f"\n🗣️ <b>Язык:</b> {lang}"
    
    # Pages
    pages = book_info.get('pages', 0)
    if pages:
        text += f"\n📃 <b>Страниц:</b> {pages}"
    
    # Size
    size = book_info.get('size', 0)
    if size:
        text += f"\n📦 <b>Размер:</b> {format_size(size)}"
    
    # Rating
    rate = book_info.get('rate', 0.0)
    if rate:
        text += f"\n⭐ <b>Рейтинг:</b> {rate:.1f}"
    
    return text


def format_book_details(book_details: Dict[str, Any]) -> str:
    """
    Format book annotation/details
    
    Args:
        book_details: Dictionary with book details including annotation
        
    Returns:
        Formatted text (truncated to 4000 chars)
    """
    title = book_details.get('title', 'Неизвестно')
    text = f"📖 <b>Аннотация о книге:</b> {title}\n\n"
    
    annotation = book_details.get('annotation', '')
    if annotation:
        clean_annotation = clean_html_tags(annotation)
        text += clean_annotation
    
    return truncate_text(text, 4000, ".")


def format_author_info(
    author_info: Dict[str, Any],
    flibusta_service: Any
) -> str:
    """
    Format author biography information
    
    Args:
        author_info: Dictionary with author details
        flibusta_service: FlibustaService instance for URL generation
        
    Returns:
        Formatted text (truncated to 4000 chars)
    """
    author_id = author_info.get('author_id', 0)
    name = author_info.get('name', 'Неизвестный автор')
    
    author_url = flibusta_service.get_author_url(author_id) if flibusta_service else ""
    text = f"👤 <b>Об авторе:</b> <a href='{author_url}'>{name}</a>\n\n"
    
    biography = author_info.get('biography', '')
    if biography:
        clean_bio = clean_html_tags(biography)
        text += clean_bio
    
    return truncate_text(text, 4000, ".")


def format_book_reviews(reviews: list) -> str:
    """
    Format book reviews
    
    Args:
        reviews: List of review tuples (name, time, text)
        
    Returns:
        Formatted text (truncated to 4000 chars)
    """
    text = "💬 <b>Отзывы о книге:</b>\n\n"
    
    for name, time, review_text in reviews[:50]:
        reviewer = f"👤 <b>{name}</b> ({time})\n"
        clean_review = clean_html_tags(review_text)
        clean_review_trunc = truncate_text(clean_review, 1000) + "\n"
        
        # Check if we would exceed 4000 chars
        if len(text + reviewer + clean_review_trunc) > 4000:
            break
        
        text += reviewer + clean_review_trunc
    
    return text