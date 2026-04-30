"""
Simple Cache - Простой in-memory кеш с TTL
"""
from typing import Optional, Any, Dict
from datetime import datetime, timedelta


class SimpleCache:
    """
    Простой in-memory кеш с TTL (Time To Live)
    
    Использование:
        cache = SimpleCache(default_ttl=300)  # 5 минут
        
        # Сохранить
        cache.set("key", value)
        cache.set("key", value, ttl=600)  # 10 минут
        
        # Получить
        value = cache.get("key")
        
        # Очистка просроченного
        expired_count = cache.cleanup_expired()
    """
    
    def __init__(self, default_ttl: int = 3600):
        """
        Инициализация кеша
        
        Args:
            default_ttl: Время жизни по умолчанию в секундах
        """
        self._cache: Dict[str, tuple[Any, datetime]] = {}
        self.default_ttl = timedelta(seconds=default_ttl)
    
    def get(self, key: str) -> Optional[Any]:
        """
        Получить значение из кеша
        
        Args:
            key: Ключ
        
        Returns:
            Значение или None если не найдено или просрочено
        """
        if key in self._cache:
            value, expires_at = self._cache[key]
            if datetime.now() < expires_at:
                return value
            else:
                # Удаляем просроченное
                del self._cache[key]
        return None
    
    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        """
        Сохранить значение в кеш
        
        Args:
            key: Ключ
            value: Значение
            ttl: Время жизни в секундах (None = default_ttl)
        """
        expires_at = datetime.now() + timedelta(seconds=ttl or self.default_ttl.total_seconds())
        self._cache[key] = (value, expires_at)
    
    def clear(self) -> None:
        """Очистить весь кеш"""
        self._cache.clear()
    
    def cleanup_expired(self) -> int:
        """
        Удалить просроченные записи
        
        Returns:
            Количество удаленных записей
        """
        now = datetime.now()
        expired_keys = [
            key for key, (_, expires_at) in self._cache.items()
            if now >= expires_at
        ]
        for key in expired_keys:
            del self._cache[key]
        return len(expired_keys)
    
    def delete(self, key: str) -> bool:
        """
        Удалить конкретный ключ
        
        Args:
            key: Ключ
        
        Returns:
            True если ключ был удален
        """
        if key in self._cache:
            del self._cache[key]
            return True
        return False
    
    def size(self) -> int:
        """Текущий размер кеша"""
        return len(self._cache)