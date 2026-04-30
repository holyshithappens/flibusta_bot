"""
User Service - Сервис для работы с пользователями
"""
from ..core.custom_types import UserSettings
from ..repositories.user_repository import UserRepository


class UserService:
    """
    Сервис для работы с пользователями
    
    Отвечает за:
    - Получение и обновление настроек
    - Блокировку/разблокировку пользователей
    - Управление датой новостей
    """
    
    def __init__(self, user_repo: UserRepository):
        """
        Инициализация сервиса
        
        Args:
            user_repo: Репозиторий для работы с пользователями
        """
        self.user_repo = user_repo
    
    def get_user_settings(self, user_id: int) -> UserSettings:
        """
        Получить настройки пользователя
        
        Args:
            user_id: ID пользователя
        
        Returns:
            UserSettings
        """
        return self.user_repo.get_settings(user_id)
    
    def update_setting(self, user_id: int, setting: str, value: str) -> None:
        """
        Обновить одну настройку
        
        Args:
            user_id: ID пользователя
            setting: Название настройки
            value: Значение
        """
        self.user_repo.update_setting(user_id, setting, value)
    
    def update_settings(self, user_id: int, **kwargs) -> None:
        """
        Обновить несколько настроек
        
        Args:
            user_id: ID пользователя
            **kwargs: Параметры для обновления
        """
        self.user_repo.update_settings(user_id, **kwargs)
    
    def is_user_blocked(self, user_id: int) -> bool:
        """
        Проверить, заблокирован ли пользователь
        
        Args:
            user_id: ID пользователя
        
        Returns:
            True если заблокирован
        """
        return self.user_repo.is_blocked(user_id)
    
    def block_user(self, user_id: int) -> None:
        """
        Заблокировать пользователя
        
        Args:
            user_id: ID пользователя
        """
        self.user_repo.block_user(user_id)
    
    def unblock_user(self, user_id: int) -> None:
        """
        Разблокировать пользователя
        
        Args:
            user_id: ID пользователя
        """
        self.user_repo.unblock_user(user_id)
    
    def update_last_news_date(self, user_id: int, date: str) -> None:
        """
        Обновить дату последних новостей
        
        Args:
            user_id: ID пользователя
            date: Дата в формате 'YYYY-MM-DD'
        """
        self.user_repo.update_last_news_date(user_id, date)
    
    def get_last_news_date(self, user_id: int) -> str:
        """
        Получить дату последних новостей
        
        Args:
            user_id: ID пользователя
        
        Returns:
            Дата в формате 'YYYY-MM-DD'
        """
        return self.user_repo.get_last_news_date(user_id)
    
    def has_new_news(self, user_id: int, current_news_date: str) -> bool:
        """
        Проверить, есть ли новые новости
        
        Args:
            user_id: ID пользователя
            current_news_date: Дата текущих новостей
        
        Returns:
            True если есть новые новости
        """
        last_news_date = self.get_last_news_date(user_id)
        return current_news_date > last_news_date
    
    def get_all_users(self) -> list:
        """
        Получить список всех пользователей
        
        Returns:
            Список кортежей (user_id, is_blocked, last_news_date)
        """
        return self.user_repo.get_all_users()
    
    def get_blocked_users(self) -> list:
        """
        Получить список заблокированных пользователей
        
        Returns:
            Список ID заблокированных пользователей
        """
        return self.user_repo.get_blocked_users()
    
    def get_user_count(self) -> int:
        """
        Получить количество пользователей
        
        Returns:
            Количество пользователей
        """
        return self.user_repo.get_user_count()
    
    def format_settings(self, settings: UserSettings) -> str:
        """
        Форматирует настройки в текст
        
        Args:
            settings: Настройки пользователя
        
        Returns:
            Отформатированный текст
        """
        lines = ["⚙️ <b>Ваши настройки:</b>"]
        
        # Количество книг на странице
        lines.append(f"📚 Книг на странице: {settings.max_books}")
        
        # Язык
        lang_display = settings.lang if settings.lang else "все языки"
        lines.append(f"🌐 Язык: {lang_display}")
        
        # Формат книг
        lines.append(f"📄 Формат: {settings.book_format.upper()}")
        
        # Тип группировки
        search_types = {
            'books': 'Книги',
            'series': 'Серии',
            'authors': 'Авторы'
        }
        lines.append(f"🔍 Группировка: {search_types.get(settings.search_type, settings.search_type)}")
        
        # Рейтинг
        if settings.rating:
            lines.append(f"⭐ Рейтинг: от {settings.rating}")
        
        # Размер
        size_display = {
            'less800': '< 800 КБ',
            'more800': '> 800 КБ',
            '': 'все'
        }.get(settings.book_size, settings.book_size)
        lines.append(f"💾 Размер: {size_display}")
        
        # Область поиска
        search_areas = {
            'b': 'Основной',
            'ba': 'По аннотациям книг',
            'aa': 'По аннотациям авторов'
        }
        lines.append(f"🔎 Поиск: {search_areas.get(settings.search_area, settings.search_area)}")
        
        # Статус блокировки
        if settings.is_blocked:
            lines.append("\n❌ <b>ВЫ ЗАБЛОКИРОВАНЫ!</b>")
            lines.append("Вы не можете использовать бота.")
        
        return "\n".join(lines)
    
    def format_settings_change(
        self, 
        setting: str, 
        old_value: str, 
        new_value: str
    ) -> str:
        """
        Форматирует сообщение об изменении настроек
        
        Args:
            setting: Название настройки
            old_value: Старое значение
            new_value: Новое значение
        
        Returns:
            Отформатированный текст
        """
        setting_titles = {
            'max_books': 'Книг на странице',
            'lang': 'Язык',
            'book_format': 'Формат',
            'search_type': 'Группировка',
            'rating': 'Рейтинг',
            'book_size': 'Размер',
            'search_area': 'Область поиска'
        }
        
        title = setting_titles.get(setting, setting)
        return f"✅ Настройка '{title}' изменена:\nБыло: {old_value or 'нет'}\nСтало: {new_value or 'нет'}"