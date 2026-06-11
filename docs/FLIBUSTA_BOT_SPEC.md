# Flibusta Telegram Bot — Specification

## Overview

Telegram bot for searching and downloading books from the Flibusta digital library.

- **Language**: Python 3.11
- **Framework**: python-telegram-bot v20+ (async)
- **Databases**: MariaDB 12.0 (books) + SQLite (users, logs, settings)
- **Deployment**: Docker + docker-compose
- **Version**: 1.6.0

---

## Architecture

```
Telegram Bot API
       │
       ▼
┌──────────────────────────────────────────────────┐
│              Python Application                  │
│                                                  │
│  Handlers  ──►  Database Layer  ──►  MariaDB     │
│  (commands,      (repositories,      (cb_lib*)   │
│   callbacks)      services)                      │
│       │                                          │
│       ├──►  i18n Module (RU/EN translations)     │
│       ├──►  Structured Logging (JSON)            │
│       └──►  Flibusta Client (HTTP, aiohttp)      │
└──────────────────────────────────────────────────┘
```

### Module Map

| Module | Purpose | Key Files |
|--------|---------|-----------|
| **Core** | Entry point, handler registration | `main.py` |
| **Handlers** | Command/callback processing | `handlers_basic.py`, `handlers_search.py`, `handlers_callback.py`, `handlers_group.py`, `handlers_info.py`, `handlers_settings.py`, `handlers_utils.py`, `handlers_payments.py` |
| **Database** | DB abstraction | `database.py` |
| **Context** | User session state | `context.py` |
| **Admin** | Admin panel & broadcast | `admin.py` |
| **i18n** | Localization (RU/EN) | `i18n/i18n.py`, `i18n/locale_manager.py`, `i18n/translations/` |
| **Logging** | Structured JSON logging | `core/logging_schema.py`, `core/structured_logger.py` |
| **Repositories** | SQLite data access | `repositories/base_sqlite.py`, `repositories/logs_repository.py` |
| **Client** | Flibusta HTTP client | `flibusta_client.py` |
| **Health** | Monitoring & cleanup | `health.py` |
| **Tools** | Utility functions (formatting, FB2 parsing) | `tools.py` |

---

## Features

### User Commands
- `/start` — Welcome and onboarding
- `/help` — Search query guide
- `/about` — Bot info and library statistics
- `/news` — Latest bot updates
- `/genres` — Browse genres
- `/pop` — Popular books and new releases
- `/set` — Search preferences
- `/donate` — Support via Telegram Stars

### Search
- Full-text search across title, author, **translator**, genre, series, year
- Annotation search (books and authors)
- Series/author grouping
- Pagination, rating filtering
- Popular books and novelties
- **Translator search** — dedicated search mode for finding books by translator name

### Internationalization (i18n)
- RU/EN locale support via YAML translation files
- Per-user language setting stored in `UserSettings.Locale`
- Locale detection, pluralization rules
- Language switchable in the settings menu

### Admin Panel
- Password authentication with 30-min session timeout
- User statistics and activity logs
- User blocking
- Database backup
- **Broadcast** — mass message to all users with:
  - ConversationHandler flow (entry → receive message → confirm/cancel)
  - Test mode via `BROADCAST_TEST_ONLY` / `BROADCAST_TEST_USER_IDS` env vars
  - Skip list via `BROADCAST_SKIP_USER_IDS` env var
  - Per-user delivery logging via structured log
  - `LastNewsDate` update in UserSettings upon successful delivery

### Structured Logging
- JSON format logs in `StructuredLog` SQLite table
- Event types: `bot.start`, `search.*`, `book.*`, `broadcast.*`, `payment.*`, `error.*`, `system.*`
- Analytical views for statistics
- Log parser for migrating old logs

---

## Database Schema

### MariaDB — `cb_lib*` tables (production)

| Table | Purpose |
|-------|---------|
| `cb_libbook` | Book metadata |
| `cb_libavtor` | Book-author relationships |
| `cb_libavtorname` | Author info |
| `cb_libgenre` | Book-genre relationships |
| `cb_libgenrelist` | Genre classification (RU) |
| `cb_libgenrelist_en` | Genre classification (EN) |
| `cb_libseq` | Book-series relationships |
| `cb_libseqname` | Series info |
| `cblibrate` | Book ratings |
| `cb_librecs` | Recommendations |
| `cb_libreviews` | Reviews |
| `cb_libbannotations` | Book annotations (FULLTEXT) |
| `cb_libaannotations` | Author annotations (FULLTEXT) |
| `cb_libbook_fts` | Full-text search index |

### SQLite — FlibustaSettings.sqlite

```sql
CREATE TABLE UserSettings (
    User_ID INTEGER PRIMARY KEY,
    MaxBooks INTEGER DEFAULT 20,
    Lang VARCHAR(2) DEFAULT '',
    BookFormat VARCHAR(5) DEFAULT 'fb2',
    SearchType TEXT DEFAULT 'books',
    Rating TEXT DEFAULT '',
    BookSize TEXT DEFAULT '',
    SearchArea TEXT DEFAULT 'b',
    Locale VARCHAR(5) DEFAULT 'ru',
    IsBlocked BOOLEAN DEFAULT FALSE,
    LastNewsDate VARCHAR(10) DEFAULT '2000-01-01'
);
```

### SQLite — FlibustaLogs.sqlite

```sql
CREATE TABLE StructuredLog (
    Timestamp TEXT NOT NULL,
    Category TEXT NOT NULL,
    EventType TEXT NOT NULL,
    UserID INTEGER,
    UserName TEXT,
    ChatType TEXT,
    ChatID INTEGER,
    DataJson TEXT,
    DurationMs INTEGER,
    ErrorMessage TEXT,
    ErrorType TEXT
);

CREATE TABLE UserPayment (
    PaymentID TEXT PRIMARY KEY,
    UserID INTEGER NOT NULL,
    Amount INTEGER NOT NULL,
    Currency TEXT NOT NULL,
    PaymentDate TEXT NOT NULL,
    PaymentStatus TEXT NOT NULL
);
```

---

## i18n Module

```
app/i18n/
├── i18n.py              # Translation helper (t() function)
├── locale_manager.py    # Locale detection and switching
├── plural_rules.py      # Pluralization rules (RU/EN)
└── translations/
    ├── ru.yaml          # Russian strings
    └── en.yaml          # English strings
```

- Translations loaded from YAML files at startup
- `t(locale, key, **kwargs)` returns translated string with interpolation
- Plural forms handled per locale rules
- User locale stored in `UserSettings.Locale`

---

## Structured Logging

```
app/core/
├── logging_schema.py    # EventCategory, EventType, LogEvent dataclasses
└── structured_logger.py # StructuredLogger with convenience methods
```

### Event Categories
- `user_action` — user interactions
- `system` — system events
- `error` — errors
- `payment` — payment events

### Key Event Types
```
search.books, search.series, search.authors, search.translators, search.popular
book.info.view, book.details.view, book.download, book.reviews.view
author.info.view, translator.info.view, genres.view, settings.change
broadcast.started, broadcast.sent, broadcast.failed
payment.received, payment.refund
system.startup, system.shutdown
error.book.download, error.search, error.telegram
```

### Convenience Methods
```python
structured_logger.log_search(user_id, username, query, search_type, results_count, filters, chat_type, chat_id)
structured_logger.log_download(user_id, username, book_id, book_title, format, file_size, success, chat_type, chat_id)
structured_logger.log_broadcast_started(admin_user_id, admin_username, total_recipients, is_test)
structured_logger.log_broadcast_result(user_id, username, success, error_message)
```

---

## Broadcast Feature

### Flow
```
Admin clicks "📢 Рассылка"
    │
    ▼
admin_broadcast_start() — asks admin to send the message
    │
    ▼
broadcast_receive_message() — stores message, shows preview + confirm/cancel buttons
    │
    ▼
handle_broadcast_callback()
    ├─ cancel → abort
    └─ confirm → broadcast_send()
        │
        ▼
    Iterate over user IDs from UserSettings
    Skip blocked users, skip non-testers in test mode
        │
        ▼
    Send via bot.copy_message()
    Log each attempt (broadcast.sent / broadcast.failed)
        │
        ▼
    Report summary to admin
```

### Environment Variables
| Variable | Description |
|----------|-------------|
| `BROADCAST_TEST_ONLY` | If `"true"`, only send to test users |
| `BROADCAST_TEST_USER_IDS` | Comma-separated tester user IDs |
| `BROADCAST_SKIP_USER_IDS` | Comma-separated user IDs to skip in broadcast |

### Logging Queries
```sql
-- All broadcast results
SELECT * FROM StructuredLog
WHERE EventType LIKE 'broadcast.%'
ORDER BY Timestamp DESC;

-- Failed deliveries
SELECT UserID, Timestamp, ErrorMessage FROM StructuredLog
WHERE EventType = 'broadcast.failed';
```

---

## Search System

### Search Areas
| Area | Constant | Table |
|------|----------|-------|
| Books (title, author, genre, series, year) | `SETTING_SEARCH_AREA_B` | `cb_libbook_fts` |
| Book annotations | `SETTING_SEARCH_AREA_BA` | `cb_libbannotations` |
| Author annotations | `SETTING_SEARCH_AREA_AA` | `cb_libaannotations` |

### Search Algorithm
1. Get user params (lang, size, rating, search area) from context
2. Build SQL with `MATCH(...) AGAINST(? IN BOOLEAN MODE)`
3. Execute asynchronously via `asyncio.create_task()`
4. Paginate results (MaxBooks per page)
5. Format response with inline keyboards

### User Settings
| Setting | Options |
|---------|---------|
| MaxBooks | 20 / 40 |
| Lang | ru / en / etc. |
| BookFormat | fb2 / epub / mobi |
| SearchType | books / series / authors / translators |
| Rating | 0–5 |
| BookSize | less800 / more800 |
| SearchArea | b / ba / aa |
| Locale | ru / en |

---

## Configuration (.env)

```env
# Telegram
BOT_TOKEN=<token>
BOT_USERNAME=<username>
TZ=Europe/Moscow

# MariaDB
DB_HOST=localhost
DB_PORT=3306
DB_NAME=flibusta
DB_USER=flibusta
DB_PASSWORD=<password>

# Admin
ADMIN_PASSWORD=<password>

# Broadcast
BROADCAST_TEST_ONLY=true
BROADCAST_TEST_USER_IDS=123456789,987654321
BROADCAST_SKIP_USER_IDS=543210987

# Feedback
FEEDBACK_EMAIL=<email>
FEEDBACK_TELEGRAM=<link>
FEEDBACK_PIKABU=<link>
FEEDBACK_PIKABU_USERNAME=<username>

# Donations (Crypto)
DONATE_SOL=<address>
DONATE_BTC=<address>
DONATE_ETH=<address>
DONATE_POL=<address>
DONATE_SUI=<address>
DONATE_TON=<address>
DONATE_TRX=<address>

# VPS
VPS_EXPIRY_DATE=2026-07-25
```

---

## Deployment

```bash
# Local development
docker-compose up -d

# Production deployment
./deploy.sh          # Full deploy (build + push + deploy)
./deploy.sh -u       # Quick update (pull + restart)
./deploy.sh -n       # Update news file
./deploy.sh -s       # Update SQL scripts
```

### Docker Services
- **mariadb:12.0** — `cb_lib*` tables, full-text indexes
- **bot** — Python app, depends on db healthcheck

---

## DB Update Strategy

Uses `lib*` → `cb_lib*` copy/rename pattern for zero-downtime updates:

1. Restore backup into `lib_*` tables (staging)
2. Create indexes and full-text indexes on `lib_*`
3. Copy/rename `lib_*` → `cb_lib_*` (atomic)
4. Bot continues serving from `cb_lib_*` throughout

---

## Development Guidelines

- All async handlers must have type hints
- Use `StructuredLogger` for all logging (no raw `print` in production)
- Store credentials in `.env`, never hardcode
- Follow existing naming and formatting conventions
- Use `ContextManager` for state management (not raw `context.user_data`)
- Handle `Forbidden`, `BadRequest`, `TimedOut` Telegram errors
