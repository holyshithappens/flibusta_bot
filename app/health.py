import psutil
import gc
from datetime import datetime

from telegram.ext import CallbackContext

from context import ContextManager
from constants import CLEANUP_INTERVAL
from logger import logger
from database import DB_BOOKS

def get_memory_usage():
    """Возвращает использование памяти в MB"""
    process = psutil.Process()
    return process.memory_info().rss / 1024 / 1024


def get_system_stats():
    """Возвращает системную статистику"""
    return {
        'memory_used': f"{get_memory_usage():.1f}",
        'memory_percent': f"{psutil.virtual_memory().percent:.1f}",
        'cpu_percent': f"{psutil.cpu_percent(interval=1):.1f}",
        'open_files': len(psutil.Process().open_files()),
        'threads': psutil.Process().num_threads(),
        'timestamp': datetime.now().isoformat()
    }


def log_system_stats():
    """Логирует системную статистику"""
    stats = get_system_stats()
    logger.log_system_action("System stats", str(stats))
    return stats


def cleanup_memory():
    """Принудительная очистка памяти"""
    before = get_memory_usage()
    gc.collect()
    after = get_memory_usage()
    # logger.log_system_action("Memory cleanup", f"{before:.1f}MB -> {after:.1f}MB")

# ===== ОБРАБОТЧИКИ ТРИГГЕРОВ В job_queue =====

async def log_stats(context: CallbackContext):
    """Только логирование статистики"""
    stats = log_system_stats()
    # print(f"Memory used: {stats['memory_used']:.1f}MB")


# async def perform_cleanup(context: CallbackContext):
#     """Периодическая очистка и мониторинг"""
#     try:
#         cleanup_memory()
#     except Exception as e:
#         print(f"Error in periodic cleanup: {e}")


async def cleanup_old_sessions(context: CallbackContext):
    """Очистка данных поиска у неактивных пользователей"""
    await log_stats(context)

    try:
        cleaned_private, cleaned_group = ContextManager.cleanup_inactive_sessions(
            context.application,
            CLEANUP_INTERVAL
        )

        if cleaned_private > 0:
            print(f"🧹 Cleaned datasets of {cleaned_private} user(s)")
        if cleaned_group > 0:
            print(f"🧹 Cleaned datasets of {cleaned_group} group(s)")

        if cleaned_private > 0 or cleaned_group > 0:
            cleanup_memory()
            await log_stats(context)

        # Check for database updates and invalidate cache if needed
        DB_BOOKS.invalidate_db_cache()

    except Exception as e:
        print(f"❌ Cleanup error: {e}")