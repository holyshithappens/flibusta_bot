# Flibusta Bot

Telegram bot for searching and downloading books from the Flibusta digital library.

- **Language**: Python 3.11
- **Framework**: python-telegram-bot (async)
- **Databases**: MariaDB (books), SQLite (users/logs)
- **Deployment**: Docker + docker-compose
- **Version**: 1.7.0

## Features

- Full-text search by title, author, **translator**, genre, series, year
- Annotation search, series/author grouping, rating filtering
- Popular books and new releases
- Group chat support with dedicated handlers
- User search preferences
- Admin panel with statistics
- Telegram Stars donations
- **Internationalization (RU/EN)** — language switchable in menu
- **Structured logging** — JSON format with analytical views
- **Admin broadcast** — mass messaging to all users with test mode and skip list
- **Person type display** — shows author/translator type in UI buttons and headers
<<<<<<< HEAD
- **Genre filtering** — persistent genre-based filter applied to all searches
>>>>>>> develop
- **Crypto donations** — SOL, BTC, ETH, POL, SUI, TON, TRX support

## Quick Start

```bash
cp .env.example .env
# Edit .env with your credentials
docker-compose up -d
```

## Project Structure

```
app/
├── main.py                 # Entry point & handler registration
├── handlers_basic.py       # Basic command handlers (start, help, etc.)
├── handlers_callback.py    # Callback query handlers
├── handlers_group.py       # Group chat handlers
├── handlers_info.py        # Book info & author/translator display
├── handlers_payments.py    # Payment & donation handlers
├── handlers_search.py      # Search functionality (books, authors, translators)
├── handlers_settings.py    # User settings & preferences
├── handlers_utils.py       # Utility handlers
├── admin.py                # Admin panel & broadcast
├── database.py             # Database abstraction layer
├── context.py              # User context management
├── flibusta_client.py      # HTTP client for Flibusta
├── constants.py            # Application constants
├── health.py               # Health checks & cleanup
├── tools.py                # Utility functions (formatting, FB2 parsing)
├── VERSION.py              # Version info
├── core/                   # Structured logging (JSON)
├── i18n/                   # RU/EN translations (YAML)
└── repositories/           # SQLite data access layer
data/                       # News files & SQLite databases
db_init/                    # DB migration & management scripts
config/                     # MySQL configuration
docs/                       # Specification & guides
```

## Environment

Key variables (see `.env.example` for full list):

| Variable | Description |
|----------|-------------|
| `BOT_TOKEN` | Telegram bot token |
| `BOT_USERNAME` | Bot username (without @) |
| `DB_HOST`, `DB_PORT`, `DB_NAME`, `DB_USER`, `DB_PASSWORD` | MariaDB connection |
| `ADMIN_PASSWORD` | Admin panel password |
| `BROADCAST_TEST_ONLY` | Restrict broadcasts to test users |
| `BROADCAST_TEST_USER_IDS` | Comma-separated tester user IDs |
| `BROADCAST_SKIP_USER_IDS` | Comma-separated user IDs to skip in broadcast |
| `DONATE_*` | Crypto donation addresses (SOL, BTC, ETH, POL, SUI, TON, TRX) |
| `FEEDBACK_*` | Feedback contacts (email, Telegram, Pikabu) |
| `VPS_EXPIRY_DATE` | VPS expiration date for monitoring |

## Database

- **MariaDB** — `cb_lib*` tables (books, authors, genres, series, ratings, annotations, full-text indexes)
- **SQLite** — user settings, structured logs, payment logs

## Deployment

```bash
./deploy.sh          # Full deployment
./deploy.sh -u       # Quick update (pull + restart)
./deploy.sh -n       # Update news file
./deploy.sh -s       # Update SQL scripts
```

## Documentation

- [`docs/FLIBUSTA_BOT_SPEC.md`](docs/FLIBUSTA_BOT_SPEC.md) — Detailed specification
- [`docs/USER_GUIDE.md`](docs/USER_GUIDE.md) — User guide
- [`CHANGELOG.md`](CHANGELOG.md) — Version history
