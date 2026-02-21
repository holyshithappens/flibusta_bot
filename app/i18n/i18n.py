"""
Core i18n (internationalization) engine.

This module provides the I18n singleton class for loading translations,
interpolating variables, and handling plural forms.

Uses class-level caching for efficient translation storage with many users.
"""

from pathlib import Path
from typing import Any, Optional

import yaml

from .plural_rules import get_plural_form, PluralForm


class I18n:
    """
    Singleton internationalization engine with class-level caching.
    
    Handles loading YAML translation files, key lookup with fallback,
    variable interpolation, and plural form selection.
    
    Translations are cached at the class level, so all instances share
    the same translation data for efficiency.
    
    Attributes:
        SUPPORTED_LOCALES: Set of supported locale codes.
        DEFAULT_LOCALE: The default locale to use.
        FALLBACK_LOCALE: The fallback locale when translations are missing.
    """
    
    # Class-level constants
    SUPPORTED_LOCALES: set[str] = {'ru', 'en'}
    DEFAULT_LOCALE: str = 'ru'
    FALLBACK_LOCALE: str = 'ru'
    
    # Class-level translation cache (shared across all instances)
    _translations: dict[str, dict[str, Any]] = {}
    _loaded_locales: set[str] = set()
    _translations_dir: Optional[Path] = None
    _initialized: bool = False
    
    # Singleton instance
    _instance: Optional['I18n'] = None
    
    def __new__(cls, translations_dir: Optional[Path] = None) -> 'I18n':
        """
        Create or return the singleton instance.
        
        Args:
            translations_dir: Path to translations directory (only used on first call).
            
        Returns:
            The singleton I18n instance.
        """
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self, translations_dir: Optional[Path] = None) -> None:
        """
        Initialize the I18n engine.
        
        Args:
            translations_dir: Path to the directory containing YAML translation files.
                             Only used on first initialization.
        """
        # Only initialize once
        if I18n._initialized:
            return
        
        if translations_dir is not None:
            I18n._translations_dir = translations_dir
            I18n._initialized = True
    
    @classmethod
    def _load_translations(cls, locale: str) -> None:
        """
        Load translations for a specific locale from YAML file.
        
        Uses lazy loading - translations are only loaded when first needed.
        Cached at class level for all instances to share.
        
        Args:
            locale: The locale code to load (e.g., 'ru', 'en').
        """
        if locale in cls._loaded_locales:
            return
        
        if locale not in cls.SUPPORTED_LOCALES:
            locale = cls.FALLBACK_LOCALE
        
        if cls._translations_dir is None:
            raise RuntimeError("I18n not initialized. Call init_i18n_engine() first.")
        
        translation_file = cls._translations_dir / f"{locale}.yaml"
        
        if translation_file.exists():
            with open(translation_file, 'r', encoding='utf-8') as f:
                cls._translations[locale] = yaml.safe_load(f) or {}
        else:
            cls._translations[locale] = {}
        
        cls._loaded_locales.add(locale)
    
    @classmethod
    def _get_nested_value(cls, data: dict[str, Any], key: str) -> Optional[Any]:
        """
        Get a nested value from a dictionary using dot notation.
        
        Args:
            data: The dictionary to search.
            key: The dot-notation key (e.g., 'settings.menu.title').
            
        Returns:
            The value if found, None otherwise.
        """
        keys = key.split('.')
        current = data
        for k in keys:
            if isinstance(current, dict) and k in current:
                current = current[k]
                print(f"DEBUG: true k={k}")
                if k == 'ratings':
                    print(f"DEBUG: true current={current}")
            else:
                print(f"DEBUG: false k={k}")
                if k == 'ratings':
                    print(f"DEBUG: false current={current}")
                return None

        return current
    
    @classmethod
    def _interpolate(cls, template: str, **kwargs: Any) -> str:
        """
        Interpolate variables into a template string.
        
        Supports {variable} syntax for variable substitution.
        
        Args:
            template: The template string with {variable} placeholders.
            **kwargs: Variable values to substitute.
            
        Returns:
            The interpolated string.
        """
        if not kwargs:
            return template
        
        try:
            return template.format(**kwargs)
        except KeyError:
            # If a variable is missing, leave the placeholder as-is
            return template
    
    @classmethod
    def get(cls, key: str, locale: str, **kwargs: Any) -> str:
        """
        Get a translated string for the given key and locale.
        
        Implements a fallback chain:
        1. Try the requested locale
        2. Try the fallback locale
        3. Return the key itself as a last resort
        
        Args:
            key: The translation key (dot notation, e.g., 'settings.menu.title').
            locale: The locale code (e.g., 'ru', 'en').
            **kwargs: Variables to interpolate into the string.
            
        Returns:
            The translated and interpolated string.
        """
        # Ensure locale is valid
        if locale not in cls.SUPPORTED_LOCALES:
            locale = cls.FALLBACK_LOCALE
        
        # Try to get translation in requested locale
        cls._load_translations(locale)
        value = cls._get_nested_value(cls._translations.get(locale, {}), key)
        
        # Fallback to default locale if not found
        if value is None and locale != cls.FALLBACK_LOCALE:
            cls._load_translations(cls.FALLBACK_LOCALE)
            value = cls._get_nested_value(
                cls._translations.get(cls.FALLBACK_LOCALE, {}), key
            )
        
        # If still not found, return the key itself
        if value is None:
            return key
        
        # Handle non-string values (e.g., if key points to a dict)
        if not isinstance(value, str):
            return str(value)
        
        return cls._interpolate(value, **kwargs)
    
    @classmethod
    def get_plural(
        cls, 
        key: str, 
        locale: str, 
        count: int, 
        **kwargs: Any
    ) -> str:
        """
        Get a translated string with plural form selection.
        
        Selects the appropriate plural form based on the count and locale,
        then interpolates the count and any additional variables.
        
        Args:
            key: The base translation key (plural forms are stored as sub-keys).
            locale: The locale code (e.g., 'ru', 'en').
            count: The count for plural form selection.
            **kwargs: Additional variables to interpolate.
            
        Returns:
            The translated string with correct plural form.
            
        Example:
            For ru.yaml:
            search:
              results:
                books:
                  one: "Найдена {count} книга"
                  few: "Найдено {count} книги"
                  many: "Найдено {count} книг"
            
            Usage:
                I18n.get_plural('search.results.books', 'ru', 5, count=5)
                # Returns: "Найдено 5 книг"
        """
        # Ensure count is included in interpolation
        kwargs['count'] = count
        
        # Get the plural form for this locale and count
        plural_form = get_plural_form(locale, count)
        
        # Try to get the specific plural form
        plural_key = f"{key}.{plural_form}"
        translation = cls.get(plural_key, locale, **kwargs)
        
        # If the plural form key wasn't found, try 'other' as fallback
        if translation == plural_key and plural_form != 'other':
            other_key = f"{key}.other"
            translation = cls.get(other_key, locale, **kwargs)
        
        return translation
    
    @classmethod
    def is_locale_supported(cls, locale: str) -> bool:
        """
        Check if a locale is supported.
        
        Args:
            locale: The locale code to check.
            
        Returns:
            True if the locale is supported, False otherwise.
        """
        return locale in cls.SUPPORTED_LOCALES
    
    @classmethod
    def get_supported_locales(cls) -> set[str]:
        """
        Get the set of supported locales.
        
        Returns:
            Set of supported locale codes.
        """
        return cls.SUPPORTED_LOCALES.copy()
    
    @classmethod
    def clear_cache(cls) -> None:
        """
        Clear the translation cache.
        
        Useful for development or when translation files are updated.
        """
        cls._translations.clear()
        cls._loaded_locales.clear()
    
    @classmethod
    def is_initialized(cls) -> bool:
        """
        Check if the I18n engine has been initialized.
        
        Returns:
            True if initialized, False otherwise.
        """
        return cls._initialized


def get_i18n() -> I18n:
    """
    Get the global I18n singleton instance.
    
    Raises:
        RuntimeError: If i18n has not been initialized.
        
    Returns:
        The global I18n instance.
    """
    if not I18n.is_initialized():
        raise RuntimeError("i18n not initialized. Call init_i18n_engine() first.")
    return I18n()


def init_i18n_engine(translations_dir: Path) -> I18n:
    """
    Initialize the global I18n instance.
    
    Args:
        translations_dir: Path to the directory containing YAML translation files.
        
    Returns:
        The initialized I18n instance.
    """
    # Clear any previous state (for testing/reinitialization)
    I18n.clear_cache()
    I18n._translations_dir = translations_dir
    I18n._initialized = True
    return I18n()
