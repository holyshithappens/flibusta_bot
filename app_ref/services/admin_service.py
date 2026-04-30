"""
Admin Service - Сервис админ-панели
"""
import os
import shutil
import sqlite3
import zipfile
import time
import glob
import platform
import psutil
from typing import Dict, Any, List, Tuple
from datetime import datetime

from ..repositories.user_repository import UserRepository
from ..repositories.logs_repository import LogsRepository


class AdminService:
    """
    Сервис для админ-панели
    
    Отвечает за:
    - Аутентификацию администратора
    - Получение статистики
    - Управление пользователями
    - Резервное копирование
    - Системную информацию
    """
    
    def __init__(
        self,
        user_repo: UserRepository,
        logs_repo: LogsRepository,
        logger=None
    ):
        """
        Инициализация сервиса
        
        Args:
            user_repo: Репозиторий пользователей
            logs_repo: Репозиторий логов
            logger: Логгер (опционально)
        """
        self.user_repo = user_repo
        self.logs_repo = logs_repo
        self.logger = logger
    
    def authenticate(self, password: str) -> bool:
        """
        Аутентификация администратора
        
        Args:
            password: Пароль
        
        Returns:
            True если пароль верный
        """
        admin_password = os.getenv('ADMIN_PASSWORD', '')
        return password == admin_password
    
    def get_system_stats(self) -> Dict[str, Any]:
        """
        Получение системной статистики
        
        Returns:
            Словарь со статистикой
        """
        stats = {}
        
        # Статистика пользователей
        user_stats = self.logs_repo.get_user_stats_summary()
        stats.update(user_stats)
        
        # Количество пользователей
        stats['total_registered_users'] = self.user_repo.get_user_count()
        
        # Количество заблокированных
        blocked = self.user_repo.get_blocked_users()
        stats['blocked_users'] = len(blocked)
        
        # Статистика платежей (за 30 дней)
        payment_stats = self.logs_repo.get_payment_stats(days=30)
        stats['payments'] = payment_stats
        
        # Топ поисков
        stats['top_searches'] = self.logs_repo.get_top_searches(limit=10)
        
        # Топ скачиваний
        stats['top_downloads'] = self.logs_repo.get_top_downloads(limit=10)
        
        # Последние ошибки
        stats['recent_errors'] = self.logs_repo.get_recent_errors(limit=10)
        
        return stats
    
    def get_daily_stats(self, days: int = 30) -> List[Dict[str, Any]]:
        """
        Получение дневной статистики
        
        Args:
            days: Количество дней
        
        Returns:
            Список дневной статистики
        """
        return self.logs_repo.get_daily_user_stats(days)
    
    def get_user_list(self) -> List[Dict[str, Any]]:
        """
        Получение списка пользователей
        
        Returns:
            Список пользователей с информацией
        """
        users = self.user_repo.get_all_users()
        
        result = []
        for user_id, is_blocked, last_news_date in users:
            # Получаем активность пользователя
            activity = self.logs_repo.get_user_activity(user_id, days=7)
            
            result.append({
                'user_id': user_id,
                'is_blocked': is_blocked,
                'last_news_date': last_news_date,
                'last_activity': activity[0]['timestamp'] if activity else None,
                'total_events': len(activity)
            })
        
        # Сортируем по активности
        result.sort(key=lambda x: x['last_activity'] or '', reverse=True)
        
        return result
    
    def block_user(self, user_id: int) -> bool:
        """
        Заблокировать пользователя
        
        Args:
            user_id: ID пользователя
        
        Returns:
            True если успешно
        """
        try:
            self.user_repo.block_user(user_id)
            return True
        except Exception:
            return False
    
    def unblock_user(self, user_id: int) -> bool:
        """
        Разблокировать пользователя
        
        Args:
            user_id: ID пользователя
        
        Returns:
            True если успешно
        """
        try:
            self.user_repo.unblock_user(user_id)
            return True
        except Exception:
            return False
    
    def get_user_details(self, user_id: int) -> Dict[str, Any]:
        """
        Получение детальной информации о пользователе
        
        Args:
            user_id: ID пользователя
        
        Returns:
            Детальная информация
        """
        settings = self.user_repo.get_settings(user_id)
        activity = self.logs_repo.get_user_activity(user_id, days=30)
        
        # Статистика по типам событий
        event_stats = {}
        for event in activity:
            event_type = event['event_type']
            event_stats[event_type] = event_stats.get(event_type, 0) + 1
        
        return {
            'user_id': user_id,
            'settings': {
                'max_books': settings.max_books,
                'lang': settings.lang,
                'book_format': settings.book_format,
                'search_type': settings.search_type,
                'rating': settings.rating,
                'book_size': settings.book_size,
                'search_area': settings.search_area,
                'is_blocked': settings.is_blocked,
                'last_news_date': settings.last_news_date
            },
            'activity_count': len(activity),
            'event_stats': event_stats,
            'last_activity': activity[0]['timestamp'] if activity else None
        }
    
    def backup_databases(self) -> Dict[str, Any]:
        """
        Создание резервных копий баз данных и логов
        
        Returns:
            Словарь с информацией о бэкапе
        """
        try:
            # Константы из старого кода
            BACKUP_TMP_PATH = "tmp"
            BACKUP_DB_FILES = [
                "data/FlibustaSettings.sqlite",
                "data/FlibustaLogs.sqlite"
            ]
            BACKUP_LOG_PATTERN = "*.log"
            
            # Создаем временную директорию если не существует
            tmp_dir = BACKUP_TMP_PATH
            os.makedirs(tmp_dir, exist_ok=True)

            # Текущая дата для имен файлов
            current_date = datetime.now().strftime("%Y%m%d_%H%M%S")

            # 1. Создаем архив с базами данных
            db_backup_path = os.path.join(tmp_dir, f"databases_backup_{current_date}.zip")

            db_files_exist = []
            for db_file in BACKUP_DB_FILES:
                if os.path.exists(db_file):
                    db_files_exist.append(db_file)

            if db_files_exist:
                with zipfile.ZipFile(db_backup_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
                    for db_file in db_files_exist:
                        zipf.write(db_file, os.path.basename(db_file))
                db_size = os.path.getsize(db_backup_path)
            else:
                db_backup_path = None
                db_size = 0

            # 2. Создаем архив с логами
            logs_backup_path = os.path.join(tmp_dir, f"logs_backup_{current_date}.zip")
            log_files = glob.glob(BACKUP_LOG_PATTERN)

            if log_files:
                with zipfile.ZipFile(logs_backup_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
                    for log_file in log_files:
                        zipf.write(log_file, os.path.basename(log_file))
                logs_size = os.path.getsize(logs_backup_path)
            else:
                logs_backup_path = None
                logs_size = 0

            return {
                'success': True,
                'db_backup_path': db_backup_path,
                'logs_backup_path': logs_backup_path,
                'db_size': db_size,
                'logs_size': logs_size,
                'db_files': [os.path.basename(f) for f in db_files_exist],
                'log_files_count': len(log_files),
                'timestamp': current_date
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }
    
    def get_system_info(self) -> Dict[str, Any]:
        """
        Получение системной информации
        
        Returns:
            Системная информация
        """
        info = {
            'system': {
                'platform': platform.system(),
                'version': platform.version(),
                'processor': platform.processor()
            },
            'python': {
                'version': platform.python_version(),
                'implementation': platform.python_implementation()
            },
            'memory': {
                'total': psutil.virtual_memory().total // (1024**3),
                'available': psutil.virtual_memory().available // (1024**3),
                'percent': psutil.virtual_memory().percent
            },
            'disk': {
                'total': psutil.disk_usage('/').total // (1024**3),
                'used': psutil.disk_usage('/').used // (1024**3),
                'free': psutil.disk_usage('/').free // (1024**3),
                'percent': psutil.disk_usage('/').percent
            },
            'process': {
                'pid': os.getpid(),
                'cpu_percent': psutil.Process().cpu_percent(),
                'memory_mb': psutil.Process().memory_info().rss // (1024**2)
            }
        }
        
        return info
    
    def cleanup_old_logs(self, days: int = 60) -> Tuple[bool, str]:
        """
        Очистка старых логов
        
        Args:
            days: Хранить логи за N дней
        
        Returns:
            (success, message)
        """
        try:
            deleted = self.logs_repo.cleanup_old_logs(days)
            return True, f"✅ Удалено {deleted} записей логов старше {days} дней"
        except Exception as e:
            return False, f"❌ Ошибка очистки логов: {str(e)}"
    
    def format_stats_message(self, stats: Dict[str, Any]) -> str:
        """
        Форматирует статистику в текст для Telegram
        
        Args:
            stats: Статистика
        
        Returns:
            Отформатированный текст
        """
        lines = ["📊 <b>СТАТИСТИКА БОТА</b>"]
        
        # Пользователи
        lines.append("\n👥 <b>Пользователи:</b>")
        lines.append(f"  Всего: {stats.get('total_users', 0)}")
        lines.append(f"  Активных: {stats.get('active_users', 0)}")
        lines.append(f"  Заблокировано: {stats.get('blocked_users', 0)}")
        lines.append(f"  С ошибками: {stats.get('users_with_errors', 0)}")
        
        # События
        lines.append("\n📈 <b>События:</b>")
        lines.append(f"  Всего: {stats.get('total_events', 0)}")
        
        # Платежи
        payments = stats.get('payments', {})
        if payments:
            lines.append("\n💰 <b>Платежи (30 дней):</b>")
            lines.append(f"  Количество: {payments.get('total_payments', 0)}")
            lines.append(f"  Сумма: {payments.get('total_amount', 0)}$")
            lines.append(f"  Средний: {payments.get('avg_amount', 0)}$")
        
        # Топ поисков
        top_searches = stats.get('top_searches', [])
        if top_searches:
            lines.append("\n🔍 <b>Топ-5 поисков:</b>")
            for i, search in enumerate(top_searches[:5], 1):
                lines.append(f"  {i}. {search['query']} ({search['search_count']})")
        
        # Топ скачиваний
        top_downloads = stats.get('top_downloads', [])
        if top_downloads:
            lines.append("\n📥 <b>Топ-5 скачиваний:</b>")
            for i, download in enumerate(top_downloads[:5], 1):
                lines.append(f"  {i}. {download['book_title']} ({download['download_count']})")
        
        # Ошибки
        errors = stats.get('recent_errors', [])
        if errors:
            lines.append("\n❌ <b>Последние ошибки:</b>")
            for i, error in enumerate(errors[:3], 1):
                lines.append(f"  {i}. {error['event_type']}: {error['error_message'][:50]}")
        
        return "\n".join(lines)