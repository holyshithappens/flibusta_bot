"""
Locale Manager for detecting and persisting user locale preferences.

This module handles:
- Detecting locale from Telegram user language_code
- Persisting locale preference in database
- Managing locale fallback chain
"""

from typing import Optional

from telegram import Update
from telegram.ext import CallbackContext

from .i18n import I18n, get_i18n


class LocaleManager:
    """
    Manages user locale detection and persistence.
    
    The locale detection follows this priority:
    1. User's stored preference in UserSettings.Locale (if not empty)
    2. Telegram's language_code from user profile (auto-saved if valid)
    3. Default fallback 'ru' (auto-saved if detection fails)
    
    The default value in DB is empty string '', which triggers auto-detection.
    First access always saves the detected locale to the database.
    """
    
    # Key for storing locale in context user_data
    CONTEXT_LOCALE_KEY = '_resolved_locale'
    
    def __init__(self) -> None:
        """Initialize the LocaleManager."""
        pass
    
    def get_locale(self, context: CallbackContext) -> str:
        """
        Get the user's locale from context (already resolved).
        
        This method assumes the locale has already been resolved via
        get_or_detect_locale(). It returns the cached locale value.
        
        Args:
            context: The Telegram callback context.
            
        Returns:
            The resolved locale code (e.g., 'ru', 'en').
            
        Raises:
            RuntimeError: If locale has not been resolved yet.
        """
        # Try to get from context user_data
        if hasattr(context, 'user_data') and context.user_data:
            locale = context.user_data.get(self.CONTEXT_LOCALE_KEY)
            if locale:
                return locale
        
        # Fallback to default
        i18n = get_i18n()
        return i18n.DEFAULT_LOCALE
    
    def get_or_detect_locale(
        self, 
        update: Update, 
        context: CallbackContext
    ) -> str:
        """
        Get or detect the user's locale, saving to DB if auto-detected.
        
        This is the main entry point for locale initialization. It should be
        called once at the start of command handlers.
        
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
        """
        i18n = get_i18n()
        
        # Step 1: Check if already resolved in context
        if hasattr(context, 'user_data') and context.user_data:
            cached_locale = context.user_data.get(self.CONTEXT_LOCALE_KEY)
            if cached_locale:
                return cached_locale
        
        # Step 2: Check user settings from database
        user_params = self._get_user_params(context)
        stored_locale = getattr(user_params, 'Locale', '') if user_params else ''
        
        # If stored locale is not empty, use it
        if stored_locale:
            # Cache in context
            self._cache_locale(context, stored_locale)
            return stored_locale
        
        # Step 3: Auto-detect from Telegram
        detected_locale = self._detect_from_telegram(update)
        
        # Step 4: Save to database
        user_id = self._get_user_id(update)
        if user_id:
            self._save_locale_to_db(context, user_id, detected_locale)
        
        # Step 5: Cache in context
        self._cache_locale(context, detected_locale)
        
        return detected_locale
    
    def set_locale(
        self, 
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
        """
        i18n = get_i18n()
        
        # Validate locale
        if not i18n.is_locale_supported(locale):
            locale = i18n.DEFAULT_LOCALE
        
        # Save to database
        self._save_locale_to_db(context, user_id, locale)
        
        # Update context cache
        self._cache_locale(context, locale)
    
    def _detect_from_telegram(self, update: Update) -> str:
        """
        Detect locale from Telegram user's language_code.
        
        Args:
            update: The Telegram update object.
            
        Returns:
            The detected locale code, or default if unsupported.
        """
        i18n = get_i18n()
        
        # Get language_code from Telegram user
        user = update.effective_user
        if not user or not user.language_code:
            return i18n.DEFAULT_LOCALE
        
        language_code = user.language_code.lower()
        
        # Extract primary language tag (e.g., 'ru' from 'ru-RU')
        primary_lang = language_code.split('-')[0]
        
        # Check if it's a supported locale
        if i18n.is_locale_supported(primary_lang):
            return primary_lang
        
        # Special handling for language variants
        # e.g., 'en-US', 'en-GB' -> 'en'
        for supported in i18n.SUPPORTED_LOCALES:
            if primary_lang == supported:
                return supported
        
        # Fallback to default
        return i18n.DEFAULT_LOCALE
    
    def _get_user_params(self, context: CallbackContext):
        """
        Get user params from context manager.
        
        Args:
            context: The Telegram callback context.
            
        Returns:
            UserSettingsType or None.
        """
        # Import here to avoid circular imports
        from ..context import get_user_params
        return get_user_params(context)
    
    def _get_user_id(self, update: Update) -> Optional[int]:
        """
        Get user ID from update.
        
        Args:
            update: The Telegram update object.
            
        Returns:
            The user ID or None.
        """
        user = update.effective_user
        return user.id if user else None
    
    def _save_locale_to_db(
        self, 
        context: CallbackContext, 
        user_id: int, 
        locale: str
    ) -> None:
        """
        Save locale to database.
        
        Args:
            context: The Telegram callback context.
            user_id: The user's Telegram ID.
            locale: The locale code to save.
        """
        # Import here to avoid circular imports
        from ..context import update_user_params
        update_user_params(context, Locale=locale)
    
    def _cache_locale(
        self, 
        context: CallbackContext, 
        locale: str
    ) -> None:
        """
        Cache locale in context user_data.
        
        Args:
            context: The Telegram callback context.
            locale: The locale code to cache.
        """
        if hasattr(context, 'user_data') and context.user_data is not None:
            context.user_data[self.CONTEXT_LOCALE_KEY] = locale


# Global instance
_locale_manager: Optional[LocaleManager] = None


def get_locale_manager() -> LocaleManager:
    """
    Get the global LocaleManager instance.
    
    Returns:
        The global LocaleManager instance.
    """
    global _locale_manager
    if _locale_manager is None:
        _locale_manager = LocaleManager()
    return _locale_manager
