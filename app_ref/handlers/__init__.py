"""
Telegram Handlers - Обработчики команд и callback'ов
"""
from .command_handlers import CommandHandlers
from .search_handlers import SearchHandlers
from .callback_handlers import CallbackHandlers
from .settings_handlers import SettingsHandlers
from .group_handlers import GroupHandlers
from .payment_handlers import PaymentHandlers
from .admin_handlers import AdminHandlers

__all__ = [
    'CommandHandlers',
    'SearchHandlers',
    'CallbackHandlers',
    'SettingsHandlers',
    'GroupHandlers',
    'PaymentHandlers',
    'AdminHandlers',
]