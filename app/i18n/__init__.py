"""
Internationalization (i18n) module for Flibusta Telegram Bot.

This module provides multi-language support with:
- Russian (ru) and English (en) as initial languages
- CLDR-compliant plural rules
- Lazy loading of translation files
- Auto-detection of user locale from Telegram

Public API:
    init_i18n: Initialize the i18n system
    t: Get a translated string
    tp: Get a translated string with plural form
    get_user_locale: Get user's locale from context
    get_or_detect_locale: Get or auto-detect user's locale
    set_user_locale: Set user's locale preference

Usage:
    from app.i18n import init_i18n, t, get_or_detect_locale
    
    # Initialize at startup
    init_i18n(Path(__file__).parent / "i18n" / "translations")
    
    # In command handler
    async def start_cmd(update, context):
        # Initialize locale (auto-detect if needed)
        get_or_detect_locale(update, context)
        
        # Get translated string
        welcome = t('welcome.title', context)
"""

from pathlib import Path
from typing import Any

from telegram import Update
from telegram.ext import CallbackContext

from .i18n import I18n, init_i18n_engine, get_i18n
from .locale_manager import LocaleManager, get_locale_manager
from .plural_rules import get_plural_form, PluralForm


def init_i18n(translations_dir: Path) -> None:
    """
    Initialize the i18n system.
    
    Must be called once at bot startup before any translation functions are used.
    
    Args:
        translations_dir: Path to the directory containing YAML translation files.
        
    Example:
        from pathlib import Path
        from app.i18n import init_i18n
        
        translations_dir = Path(__file__).parent / "i18n" / "translations"
        init_i18n(translations_dir)
    """
    init_i18n_engine(translations_dir)
    # Initialize locale manager
    get_locale_manager()


def t(key: str, context: CallbackContext, **kwargs: Any) -> str:
    """
    Get a translated string for the given key.
    
    Uses the locale stored in context (set via get_or_detect_locale).
    
    Args:
        key: The translation key (dot notation, e.g., 'settings.menu.title').
        context: The Telegram callback context.
        **kwargs: Variables to interpolate into the string.
        
    Returns:
        The translated and interpolated string.
        
    Example:
        # With ru.yaml: welcome.title: "Привет, {name}!"
        text = t('welcome.title', context, name="Иван")
        # Returns: "Привет, Иван!"
    """
    i18n = get_i18n()
    locale_manager = get_locale_manager()
    locale = locale_manager.get_locale(context)
    return i18n.get(key, locale, **kwargs)


def tp(
    key: str, 
    context: CallbackContext, 
    count: int, 
    **kwargs: Any
) -> str:
    """
    Get a translated string with plural form selection.
    
    Automatically selects the correct plural form based on count and locale.
    
    Args:
        key: The base translation key (plural forms are sub-keys).
        context: The Telegram callback context.
        count: The count for plural form selection.
        **kwargs: Additional variables to interpolate (count is included automatically).
        
    Returns:
        The translated string with correct plural form.
        
    Example:
        # With ru.yaml:
        # search:
        #   results:
        #     books:
        #       one: "Найдена {count} книга"
        #       few: "Найдено {count} книги"
        #       many: "Найдено {count} книг"
        
        text = tp('search.results.books', context, 5)
        # Returns: "Найдено 5 книг"
    """
    i18n = get_i18n()
    locale_manager = get_locale_manager()
    locale = locale_manager.get_locale(context)
    return i18n.get_plural(key, locale, count, **kwargs)


def get_user_locale(context: CallbackContext) -> str:
    """
    Get the user's locale from context.
    
    Returns the cached locale value. Use get_or_detect_locale for initial
    locale detection.
    
    Args:
        context: The Telegram callback context.
        
    Returns:
        The user's locale code (e.g., 'ru', 'en').
    """
    locale_manager = get_locale_manager()
    return locale_manager.get_locale(context)


def get_or_detect_locale(
    update: Update, 
    context: CallbackContext
) -> str:
    """
    Get or detect the user's locale, saving to DB if auto-detected.
    
    This is the main entry point for locale initialization. Call this once
    at the start of command handlers to ensure locale is resolved.
    
    Detection flow:
    1. Check if locale is already resolved in context
    2. Check UserSettings.Locale from database
    3. If empty, auto-detect from Telegram language_code
    4. Save detected locale to database
    5. Cache in context for future use
    
    Args:
        update: The Telegram update object.
        context: The Telegram callback context.
        
    Returns:
        The resolved locale code (e.g., 'ru', 'en').
        
    Example:
        async def start_cmd(update, context):
            # Initialize locale (auto-detect if needed)
            locale = get_or_detect_locale(update, context)
            
            # Now t() will use the resolved locale
            welcome = t('welcome.title', context)
    """
    locale_manager = get_locale_manager()
    return locale_manager.get_or_detect_locale(update, context)


def set_user_locale(
    context: CallbackContext, 
    user_id: int, 
    locale: str
) -> None:
    """
    Set the user's locale preference.
    
    Saves the locale to both database and context cache.
    
    Args:
        context: The Telegram callback context.
        user_id: The user's Telegram ID.
        locale: The locale code to set (e.g., 'ru', 'en').
        
    Example:
        # User selected English in settings
        set_user_locale(context, user.id, 'en')
    """
    locale_manager = get_locale_manager()
    locale_manager.set_locale(context, user_id, locale)


# Export public API
__all__ = [
    'init_i18n',
    't',
    'tp',
    'get_user_locale',
    'get_or_detect_locale',
    'set_user_locale',
    'I18n',
    'get_i18n',
    'LocaleManager',
    'get_locale_manager',
    'get_plural_form',
    'PluralForm',
]
