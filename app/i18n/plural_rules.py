"""
CLDR Plural Rules for supported locales.

This module implements plural form selection based on CLDR (Common Locale Data Repository)
rules for each supported language.

Russian plural rules:
    - one: 1, 21, 31, 41, ... (numbers ending in 1, except 11)
    - few: 2-4, 22-24, 32-34, ... (numbers ending in 2-4, except 12-14)
    - many: 0, 5-20, 25-30, 35-40, ... (all others)
    - other: decimals (not used for integer counts)

English plural rules:
    - one: 1
    - other: 0, 2, 3, 4, ...
"""

from typing import Literal

PluralForm = Literal['one', 'few', 'many', 'other']


def get_plural_form_ru(count: int) -> PluralForm:
    """
    Get the plural form for Russian language based on count.
    
    Russian has complex plural rules based on the last digit(s) of the count.
    
    Args:
        count: The number of items.
        
    Returns:
        The plural form: 'one', 'few', 'many', or 'other'.
        
    Examples:
        >>> get_plural_form_ru(1)
        'one'   # 1 книга
        >>> get_plural_form_ru(2)
        'few'   # 2 книги
        >>> get_plural_form_ru(5)
        'many'  # 5 книг
        >>> get_plural_form_ru(21)
        'one'   # 21 книга
        >>> get_plural_form_ru(22)
        'few'   # 22 книги
        >>> get_plural_form_ru(25)
        'many'  # 25 книг
    """
    if count < 0:
        count = abs(count)
    
    # Handle the special case for decimals (if needed in future)
    # For now, we only handle integers
    
    # Get the last two digits for the "teen" exception
    last_two = count % 100
    # Get the last digit
    last_one = count % 10
    
    # Numbers ending in 11-14 use 'many' (e.g., 11 книг, 12 книг, 13 книг, 14 книг)
    if 11 <= last_two <= 14:
        return 'many'
    
    # Numbers ending in 1 use 'one' (e.g., 1 книга, 21 книга, 31 книга)
    if last_one == 1:
        return 'one'
    
    # Numbers ending in 2-4 use 'few' (e.g., 2 книги, 3 книги, 4 книги, 22 книги)
    if 2 <= last_one <= 4:
        return 'few'
    
    # All others use 'many' (e.g., 0 книг, 5 книг, 10 книг, 20 книг)
    return 'many'


def get_plural_form_en(count: int) -> PluralForm:
    """
    Get the plural form for English language based on count.
    
    English has simple plural rules: 'one' for 1, 'other' for everything else.
    
    Args:
        count: The number of items.
        
    Returns:
        The plural form: 'one' or 'other'.
        
    Examples:
        >>> get_plural_form_en(1)
        'one'    # 1 book
        >>> get_plural_form_en(0)
        'other'  # 0 books
        >>> get_plural_form_en(2)
        'other'  # 2 books
    """
    if count == 1:
        return 'one'
    return 'other'


# Mapping of locale codes to their plural rule functions
PLURAL_RULES: dict[str, callable] = {
    'ru': get_plural_form_ru,
    'en': get_plural_form_en,
}


def get_plural_form(locale: str, count: int) -> PluralForm:
    """
    Get the plural form for a given locale and count.
    
    Args:
        locale: The locale code (e.g., 'ru', 'en').
        count: The number of items.
        
    Returns:
        The plural form for the given locale and count.
        
    Raises:
        ValueError: If the locale is not supported.
    """
    if locale not in PLURAL_RULES:
        raise ValueError(f"Unsupported locale for plural rules: {locale}")
    
    return PLURAL_RULES[locale](count)
