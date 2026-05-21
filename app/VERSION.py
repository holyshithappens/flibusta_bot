"""
Версия проекта
"""

__version__ = "1.3.0"
__version_info__ = (1, 3, 0)

# История версий:
# 1.3.0 (2026-05-21) - Feat: admin broadcast feature with test mode and structured logging
# 1.2.0 (2026-05-05) - Feat: add i18n support for ru/en locales
# 1.1.11 (2026-04-28) - Fix: correct the queries for searching novelties and popular books
# 1.1.10 (2026-04-10) - Fix: remove error nested query limitations for pop/nov book search
# 1.1.9 (2026-03-19) - Feat: show current bot version in admin panel
# 1.1.8 (2026-03-09) - Fix: resolve log_payment error
# 1.1.7 (2026-03-05) - Fix: correct number of authors calculation
# 1.1.6 (2026-02-15) - Hotfix: remove cache repopulation
# 1.1.5 (2026-02-07) - Hotfix cleanup interval to 3600 secs
# 1.1.4 (2026-02-07) - Invalidate cache if DB updated and hotfix cleanup inactive sessions
# 1.1.0 (2025-12-14) - Migration to cb_ tables for safe updates
# 1.0.0 (2025-01-15) - Initial production version