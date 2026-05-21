# Flibusta Bot

Telegram bot for searching and downloading books from the Flibusta digital library.

- **Language**: Python 3.11
- **Framework**: python-telegram-bot (async)
- **Databases**: MariaDB (books), SQLite (users/logs)
- **Deployment**: Docker + docker-compose
- **Version**: 1.3.0

## Features

- Full-text search by title, author, genre, series, year
- Annotation search, series/author grouping, rating filtering
- Popular books and new releases
- Group chat support
- User search preferences
- Admin panel with statistics
- Telegram Stars donations
- **Internationalization (RU/EN)** — language switchable in menu
- **Structured logging** — JSON format with analytical views
- **Admin broadcast** — mass messaging to all users with test mode

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
├── handlers_*.py           # Command, callback, search, settings handlers
├── admin.py                # Admin panel & broadcast
├── database.py             # Database abstraction layer
├── context.py              # User context management
├── flibusta_client.py      # HTTP client for Flibusta
├── constants.py            # Application constants
├── health.py               # Health checks & cleanup
├── VERSION.py              # Version info
├── core/                   # Structured logging (JSON)
├── i18n/                   # RU/EN translations (YAML)
└── repositories/           # SQLite data access layer
db_init/                    # DB migration & management scripts
config/                     # MySQL configuration
docs/                       # Specification & guides
```

## Environment

Key variables (see `.env.example` for full list):

| Variable | Description |
|----------|-------------|
| `BOT_TOKEN` | Telegram bot token |
| `DB_HOST`, `DB_PORT`, `DB_NAME`, `DB_USER`, `DB_PASSWORD` | MariaDB connection |
| `ADMIN_PASSWORD` | Admin panel password |
| `BROADCAST_TEST_ONLY` | Restrict broadcasts to test users |
| `BROADCAST_TEST_USER_IDS` | Comma-separated tester user IDs |

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
