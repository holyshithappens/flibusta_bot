"""
Utils package for Flibusta Bot New Architecture
"""

# Import key utilities for easy access
from .formatter import clean_html_tags, format_size, truncate_text, format_book_info, format_author_info, format_book_details, format_book_reviews, format_links_from_flat_string


__all__ = [
    'clean_html_tags',
    'format_size',
    'truncate_text',
    'format_book_info',
    'format_author_info',
    'format_book_details',
    'format_book_reviews',
    'format_links_from_flat_string'
]
