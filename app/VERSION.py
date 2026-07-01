"""
Версия проекта
"""

__version__ = "1.7.3"
__version_info__ = (1, 7, 3)

# История версий:
# 1.7.3 (2026-07-01) - Fix: fix TypeError in get_parent_genres_count
# 1.7.2 (2026-06-30) - Maintenance release
# 1.7.1 (2026-06-29) - Imp: improve caching of genres
# 1.7.0 (2026-06-11) - Feat: add genre filtering in search, author and series views
# 1.6.0 (2026-06-03) - Docs: update README and spec with recent improvements
# 1.5.1 (2026-06-02) - Feat: log date of user received broadcast message
# 1.5.0 (2026-06-02) - Feat: display person_type (author/translator) in UI, fix author/translator info view from book info
# 1.4.0 (2026-05-31) - Feat: add translator search, DB update scripts config, reduce resource consumption
# 1.3.3 (2026-05-25) - Fix: add book_title to BOOK_INFO_VIEW log event for admin panel display
# 1.3.2 (2026-05-24) - Fix: use real book title from Content-Disposition header in download logging
# 1.3.1 (2026-05-24) - Fix: correct search query logging in structured_logger
# 1.3.0 (2026-05-21) - Feat: admin broadcast feature with test mode and structured logging
# 1.2.0 (2026-05-05) - Feat: add i18n support for ru/en locales
# 1.1.11 (2026-04-28) - Fix: correct the queries for searching novelties and popular books
# 1.1.10 (2026-04-10) - Fix: remove error nested query limitations for pop/nov book search
# 1.1.9 (2026-03-19) - Feat: show current bot version in admin panel
# 1.1.8 (2026-03-09) - Fix: resolve log_payment error
# 1.1.7 (2026-03-05) - Fix: correct number of authors calculation
# 1.1.6 (2026-02-15) - Hotfix: remove cache repopulation
# 1.1.5 (2026-02-15) - Hotfix cleanup interval to 3600 secs
# 1.1.4 (2026-02-07) - Invalidate cache if DB updated and hotfix cleanup inactive sessions
# 1.1.0 (2025-12-14) - Migration to cb_ tables for safe updates
# 1.0.0 (2025-01-15) - Initial production version