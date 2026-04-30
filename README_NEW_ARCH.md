# Flibusta Bot - New Architecture

Telegram bot for searching and downloading books from Flibusta digital library, built with modern software architecture principles.

## 📚 Project Status

**Current State**: New architecture in active development, running in parallel with production legacy version.

- **Language**: Python 3.11+
- **Bot Framework**: python-telegram-bot v21.x
- **Architecture**: Clean Architecture with layered design
- **Primary Database**: MariaDB 12.0 (Flibusta native database)
- **Secondary Database**: SQLite (user logs and settings)
- **Deployment**: Docker + docker-compose
- **Status**: Development/Testing

## 🛠️ Tech Stack

### Core Dependencies
- **python-telegram-bot** - Modern Telegram Bot API wrapper with async support
- **aiohttp** - Async HTTP client for Flibusta requests
- **mysql-connector-python** - MariaDB connection handling
- **beautifulsoup4** - HTML parsing
- **dataclasses** - Type-safe data structures
- **typing** - Full type annotations

### Architecture Components
- **Repositories** - Data access layer with TTL-based caching
- **Services** - Business logic layer
- **Handlers** - Presentation layer (Telegram API)
- **Core** - Caching (SimpleCache) and context management

## 🎯 Core Features

### User Commands
- **`/start`** - Bot initialization and user onboarding
- **`/help`** - Search query guidance
- **`/about`** - Bot information and library statistics
- **`/news`** - Latest bot updates
- **`/genres`** - Browse available genres
- **`/pop`** - Popular books and new releases
- **`/set`** - Configure search preferences
- **`/donate`** - Support developer (Telegram Stars)

### Search Capabilities
- **Full-text search** across book database with optimized indexes
- **Multi-field search** - title, author, genre, series, year
- **Annotation search** - book and author annotations
- **Series grouping** - books organized by series
- **Author grouping** - books by specific authors
- **Pagination** - navigate through search results
- **Filtering** - rating-based filtering with caching

### Advanced Features
- **Group chat support** - bot works in group conversations
- **User preferences** - customizable search settings
- **Payment integration** - Telegram Stars support
- **Admin panel** - moderation and statistics
- **Async processing** - efficient concurrent request handling
- **Comprehensive logging** - structured JSON logs + SQLite analytics
- **Caching layer** - TTL-based cache for improved performance
- **User blocking** - security checks at all layers

## 🏗️ Architecture

### System Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                  Telegram Bot API                           │
└─────────────────────┬───────────────────────────────────────┘
                      │
┌─────────────────────▼───────────────────────────────────────┐
│              Python Application (New Architecture)          │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────┐ │
│  │  Handlers    │  │   Services   │  │   Repositories   │ │
│  │  (Telegram   │◄─┤  (Business   │◄─┤  (Data Access)   │ │
│  │   API Layer) │  │   Logic)     │  │                  │ │
│  └──────────────┘  └──────────────┘  └──────────────────┘ │
│         │                 │                    │           │
│         │                 │                    │           │
│  ┌──────▼─────────────────▼────────────────────▼────────┐ │
│  │              Core Layer                              │ │
│  │  ┌──────────────┐  ┌──────────────┐                │ │
│  │  │    Cache     │  │   Context    │                │ │
│  │  │   (TTL)      │  │  Manager     │                │ │
│  │  └──────────────┘  └──────────────┘                │ │
│  └──────────────────────────────────────────────────────┘ │
│                                                            │
│  ┌────────────────────────────────────────────────────┐  │
│  │         Legacy Components (Under Refactoring)       │  │
│  │  ┌──────────────────┐  ┌────────────────────────┐  │  │
│  │  │ structured_      │  │   health.py            │  │  │
│  │  │ logger.py        │  │   (cleanup_old_session)│  │  │
│  │  │ logging_schema.py│  │                        │  │  │
│  │  └──────────────────┘  └────────────────────────┘  │  │
│  └────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
                      │
         ┌────────────┴────────────┐
         ▼                         ▼
┌─────────────────┐    ┌──────────────────┐
│   MariaDB       │    │   SQLite DBs     │
│  (books, authors,    │  (logs, user     │
│   genres, series)    │   settings)      │
└────────────────-┘    └──────────────────┘
```

### Layer Breakdown

**Presentation Layer** (`app_ref/handlers/`)
- [`command_handlers.py`](app/handlers/command_handlers.py:1) - User commands (/start, /help, /about, /genres, etc.)
- [`search_handlers.py`](app/handlers/search_handlers.py:1) - Search and navigation
- [`callback_handlers.py`](app/handlers/callback_handlers.py:1) - Button and inline query callbacks
- [`group_handlers.py`](app/handlers/group_handlers.py:1) - Group chat message handling
- [`settings_handlers.py`](app/handlers/settings_handlers.py:1) - User preferences
- [`payment_handlers.py`](app/handlers/payment_handlers.py:1) - Telegram Stars integration
- [`admin_handlers.py`](app/handlers/admin_handlers.py:1) - Admin panel

**Business Logic Layer** (`app_ref/services/`)
- [`search_service.py`](app/services/search_service.py:1) - Search query processing and filtering
- [`book_service.py`](app/services/book_service.py:1) - Book metadata and download handling
- [`user_service.py`](app/services/user_service.py:1) - User management and preferences
- [`admin_service.py`](app/services/admin_service.py:1) - Admin operations and analytics
- [`flibusta_service.py`](app/services/flibusta_service.py:1) - Flibusta website interaction (URL generation, downloads)

**Data Access Layer** (`app_ref/repositories/`)
- [`book_repository.py`](app/repositories/book_repository.py:1) - MariaDB book data access with TTL-based caching
- [`user_repository.py`](app/repositories/user_repository.py:1) - SQLite user data management
- [`logs_repository.py`](app/repositories/logs_repository.py:1) - SQLite structured logging

**Core Layer** (`app_ref/core/`)
- [`cache.py`](app/core/cache.py:1) - TTL-based in-memory caching (SimpleCache)
- [`context_manager.py`](app/core/context_manager.py:1) - User session and state management
- [`structured_logger.py`](app/core/structured_logger.py:1) - Structured logging with SQLite backend
- [`logging_schema.py`](app/core/logging_schema.py:1) - Logging schema definitions
- [`custom_types.py`](app/core/custom_types.py:1) - Type definitions and dataclasses

## 📁 Project Structure

```
flibusta_bot/
├── app_ref/
│   ├── main_new.py                 # New entry point (new architecture)
│   │
│   ├── core/                       # Core layer
│   │   ├── __init__.py
│   │   ├── cache.py                # SimpleCache with TTL
│   │   ├── custom_types.py         # Type definitions and dataclasses
│   │   ├── context_manager.py      # State management
│   │   ├── structured_logger.py    # Structured logging with SQLite backend
│   │   └── logging_schema.py       # Logging schema definitions
│   │
│   ├── repositories/               # Data access layer
│   │   ├── __init__.py
│   │   ├── base_mariadb.py         # Base MariaDB repository
│   │   ├── base_sqlite.py          # Base SQLite repository
│   │   ├── book_repository.py      # Books (MariaDB + caching)
│   │   ├── user_repository.py      # Users (SQLite)
│   │   └── logs_repository.py      # Logs (SQLite)
│   │
│   ├── services/                   # Business logic layer
│   │   ├── __init__.py
│   │   ├── search_service.py       # Search functionality
│   │   ├── book_service.py         # Book operations
│   │   ├── user_service.py         # User management
│   │   └── admin_service.py        # Admin operations
│   │
│   ├── handlers/                   # Presentation layer
│   │   ├── __init__.py
│   │   ├── command_handlers.py     # Basic commands
│   │   ├── search_handlers.py      # Search and navigation
│   │   ├── callback_handlers.py    # Callback queries
│   │   ├── group_handlers.py       # Group chat
│   │   ├── settings_handlers.py    # User settings
│   │   ├── payment_handlers.py     # Payments
│   │   └── admin_handlers.py       # Admin panel
│   │
│   ├── utils/                      # Utility functions
│   │   ├── __init__.py
│   │   └── formatter.py            # Message formatting
│   │
│   └── tests/                      # Test suite
│       ├── test_new_arch.py        # Architecture tests
│       └── test_group_handlers.py  # Group handler tests
│
├── db_init/                        # MariaDB initialization
│   ├── manage_flibusta_db.sh       # Database management script
│   ├── README_CB_MIGRATION.md      # Migration documentation
│   ├── zz_00_rollback_cb_tables.sql
│   ├── zz_01_cleanup_old_tables.sql
│   ├── zz_10_convert_charset.sql
│   ├── zz_20_create_indexes.sql
│   ├── zz_30_create_FT_indexes.sql
│   ├── zz_40_fill_FT.sql
│   ├── zz_50_repair_FT.sql
│   ├── zz_59_migrate_cb_tables_to_old.sql
│   ├── zz_60_migrate_to_cb_tables.sql
│   ├── zz_65_copy_lib_to_cb_tables.sql
│   └── zz_sqlite_init_structured_log.sql
│
├── data/                           # SQLite databases (auto-created)
│   ├── FlibustaBot.sqlite         # User settings
│   └── FlibustaLogs.sqlite        # Structured logs
│
├── docker-compose.vps.yml          # Docker for production (VPS)
├── Dockerfile                      # Container definition
├── requirements.txt                # Python dependencies
├── deploy.sh                       # Deployment script
├── .env.example                    # Environment variables template
├── VERSION.py                      # Version info
└── CHANGELOG.md                    # Version history
```

## 🚀 Production Deployment (VPS)

### Prerequisites
- VPS with Docker and Docker Compose installed
- SSH access to VPS
- Telegram Bot Token (from @BotFather)
- Docker Hub account (for image deployment)

### Step 1: Configure Environment Variables

**IMPORTANT**: First, copy `.env.example` to `.env.vps` and configure it for production:

```bash
cp .env.example .env.vps
nano .env.vps
```

**Configure `.env.vps` for VPS deployment:**

```bash
# Telegram
BOT_TOKEN=your_production_bot_token_here
BOT_USERNAME=flibustabot

# MariaDB (Docker network)
DB_HOST=db
DB_PORT=3306
DB_NAME=flibusta
DB_USER=flibusta
DB_PASSWORD=your_secure_password

# SQLite paths (will be mounted from VPS)
SQLITE_DB_PATH=data/FlibustaBot.sqlite
LOGS_DB_PATH=data/FlibustaLogs.sqlite

# Timezone
TZ=Europe/Moscow

# Administrator
ADMIN_PASSWORD=your_secure_admin_password
```

### Step 2: Run Full Deployment

The deployment script will automatically copy `.env.vps` to your VPS as `.env` and use it for container configuration.

```bash
./deploy.sh
```

**What the deployment script does:**

1. **Prompts for credentials:**
   - VPS IP address and username
   - Docker Hub password/PAT
   - Git branch/tag to deploy from

2. **Copies configuration files:**
   - `.env.vps` → VPS as `.env`
   - `docker-compose.vps.yml` → VPS as `docker-compose.yml`

3. **Copies SQL scripts:**
   - Database management script (`manage_flibusta_db.sh`)
   - All SQL migration files (`zz_*.sql`)

4. **Builds and deploys:**
   - Clones git repository from specified branch/tag
   - Builds Docker image locally
   - Pushes to Docker Hub
   - Pulls image on VPS
   - Starts containers with docker-compose

5. **Verifies deployment:**
   - Checks container status
   - Displays MariaDB logs

### Step 3: Initialize Database

After successful deployment, SSH into your VPS and initialize the database:

```bash
# SSH into VPS
ssh username@vps_ip

# Navigate to project directory
cd ~/flbst-bot-mdb/db_init

# Run database management script
./manage_flibusta_db.sh
```

**Follow the menu options in order:**

1. **Option 1** - Download SQL files from Flibusta
2. **Option 2** - Load SQL files into temporary `lib*` tables
3. **Option 3** - Apply preparation scripts (indexes, full-text search)
4. **Option 4** - Activate tables by renaming `lib*` → `cb_lib*`

This completes the database setup. The bot is now ready to use.

### Step 4: Verify Services

```bash
# Check containers
docker-compose ps

# View bot logs
docker-compose logs -f bot

# View database logs
docker-compose logs -f db
```

## 🐳 Docker Compose Configuration

The production stack consists of two containers:

**MariaDB 12.0** (`flibusta-db`)
- Hosts the Flibusta book database
- Automatic restarts on failure
- Health checks enabled
- Data persisted in named volume

**Bot Application** (`flibusta-bot`)
- Python Telegram bot (new architecture)
- Depends on healthy MariaDB
- Automatic restarts
- Logs and data mounted from host
- Structured logging enabled

## 🗄️ Database Management

### Database Table Naming Convention

The Flibusta database uses a two-stage table naming system for safe updates:

- **`lib*` tables** - Initial tables loaded from Flibusta SQL dumps
- **`cb_lib*` tables** - Active tables used by the bot (renamed from `lib*`)

This allows for safe database updates: new data is loaded into `lib*` tables, prepared with indexes, then quickly activated by renaming to `cb_lib*`.

### Initial Database Setup

After deployment, initialize the database on your VPS:

```bash
# SSH into VPS
ssh username@vps_ip
cd ~/flbst-bot-mdb/db_init

# Run database management script
./manage_flibusta_db.sh
```

**Database Manager Menu:**
1. **Download SQL files** - Download Flibusta database dumps to `sql/` directory
2. **Load lib*.sql** - Import SQL files into temporary `lib*` tables
3. **Apply preparation scripts** - Run charset conversion, create indexes, build full-text search
4. **Activate cb_lib*** - Rename `lib*` → `cb_lib*` (fast atomic operation)
5. **Rollback** - Restore previous version from `cb_lib*_old` tables
6. **Cleanup old tables** - Remove backup `cb_lib*_old` tables
7. **Cleanup SQL files** - Remove downloaded `.sql.gz` files

### Database Deployment Workflow

**Fresh Installation:**
```bash
# Step 1-2: Download and load data
Options 1 → 2: Download SQL files and load into lib* tables

# Step 3: Prepare data
Option 3: Apply all preparation scripts (indexes, full-text search)

# Step 4: Activate
Option 4: Rename lib* → cb_lib* (instant activation)
```

**Update Existing Database:**
```bash
# Previous cb_lib* tables are automatically backed up to cb_lib*_old
# Follow same steps 1-4 for fresh installation
# Verify new data works correctly, then optionally:
Option 6: Cleanup old tables (removes cb_lib*_old)
```

**Rollback if Issues:**
```bash
Option 5: Rollback to previous version (renames cb_lib*_old → cb_lib*)
```

### Database Tables

The active Flibusta database (`cb_lib*` tables) includes:
- `cb_libbook` - Book metadata
- `cb_libavtor` / `cb_libavtorname` - Author information
- `cb_libgenre` / `cb_libgenrelist` - Genre classifications
- `cb_libseq` / `cb_libseqname` - Book series
- `cb_libbannotations` / `cb_libaannotations` - Book and author annotations
- `cb_librate` - Book ratings
- `cb_librecs` / `cb_libreviews` - Recommendations and reviews
- `cb_libbook_fts` - Full-text search index
- Additional tables for pictures and translations

### Structured Logging Database

The new architecture includes a SQLite database for structured logs:

**Tables:**
- `StructuredLog` - Main logging table with JSON metadata

## 🔄 Maintenance

### Update Bot Code

```bash
# Quick update (pull latest image and restart)
./deploy.sh --update
```

### Update News File

```bash
# Copy only news file to VPS
./deploy.sh --news
```

### Update Database Scripts

```bash
# Copy SQL scripts to VPS
./deploy.sh --sql
```

### Monitor Resources

```bash
# Check container resource usage
docker stats

# View recent logs
docker-compose logs --tail=50
```

## 🔑 Key Differences from Legacy Version

| Aspect | Legacy Version (main.py) | New Version (main_new.py) |
|--------|------------------------|---------------------------|
| **Architecture** | Procedural (functions) | OOP (classes, layers) |
| **Typing** | Minimal | Full (dataclasses, enum) |
| **Logging** | print() | StructuredLogger (JSON + SQLite) |
| **Caching** | None | SimpleCache with TTL |
| **Repositories** | Mixed code | Separate layer (3 repositories) |
| **Services** | Mixed code | Separate layer (4 services) |
| **Handlers** | Mixed code | Separate layer (8 classes) |
| **Security** | Basic | User blocking checks at all levels |
| **Testing** | Manual | Automated test suite |
| **Maintainability** | Difficult | Easy (SOLID principles) |

## 🔗 Architecture Dependencies

### Dependency Flow
```
Telegram Update → Handlers → Services → Repositories → Databases
                                ↓
                          FlibustaService (URLs, downloads)
```

### Component Dependencies

**Handlers Layer:**
- All handlers receive services via dependency injection
- [`callback_handlers.py`](app/handlers/callback_handlers.py:1) depends on:
 - [`SearchService`](app/services/search_service.py:22)
 - [`BookService`](app/services/book_service.py:14)
 - [`UserService`](app/services/user_service.py:8)
 - [`SettingsHandlers`](app/handlers/settings_handlers.py:82) (injected)
 - [`StructuredLogger`](app/core/structured_logger.py:1)

**Services Layer:**
- [`BookService`](app/services/book_service.py:14) depends on:
 - [`BookRepository`](app/repositories/book_repository.py:1) (data access)
 - [`FlibustaService`](app/services/flibusta_service.py:22) (URLs, downloads, covers)
 
- [`SearchService`](app/services/search_service.py:22) depends on:
 - [`BookRepository`](app/repositories/book_repository.py:1) (data access)
 
- [`UserService`](app/services/user_service.py:8) depends on:
 - [`UserRepository`](app/repositories/user_repository.py:1) (data access)

- [`SettingsHandlers`](app/handlers/settings_handlers.py:82) depends on:
 - [`UserService`](app/services/user_service.py:8)
 - [`BookService`](app/services/book_service.py:14)
 - [`StructuredLogger`](app/core/structured_logger.py:1)

**FlibustaService (Central URL Generator):**
- [`FlibustaService`](app/services/flibusta_service.py:22) is the **single source of truth** for all Flibusta URLs
- Provides methods for URL generation:
 - [`get_book_url()`](app/services/flibusta_service.py:60) - Book pages
 - [`get_download_url()`](app/services/flibusta_service.py:64) - Download links
 - [`get_author_url()`](app/services/flibusta_service.py:68) - Author pages
 - [`get_series_url()`](app/services/flibusta_service.py:72) - Series pages
 - [`get_genre_url()`](app/services/flibusta_service.py:76) - Genre pages
 - [`get_cover_url()`](app/services/flibusta_service.py:80) - Book covers
 - [`get_author_photo_url()`](app/services/flibusta_service.py:84) - Author photos

### Key Architectural Rules

1. **No Local Imports in Handlers**: All dependencies must be injected via constructor
  - ❌ Wrong: `from ..handlers.settings_handlers import SettingsHandlers` inside a method
  - ✅ Right: `SettingsHandlers` injected in `__init__()`

2. **All Flibusta URLs via FlibustaService**: Never hardcode URLs
  - ❌ Wrong: `flibusta_base_url = "https://flibusta.is"` in handlers
  - ✅ Right: `self.book_service.flibusta_service.get_genre_url(genre_id)`

3. **Service Layer Access Pattern**:
  - Handlers call services, not repositories directly
  - Services orchestrate repositories and FlibustaService
  - FlibustaService handles all external Flibusta interactions

4. **Dependency Injection Chain**:
  ```
  main_new.py
  ├─> Creates repositories
  ├─> Creates services (injecting repositories + FlibustaService)
  ├─> Creates handlers (injecting services + other handlers)
  └─> Registers handlers with application
  ```

## 🛡️ Security

### Security Checks at All Layers

1. **Repositories:**
   - Parameter validation
   - SQL injection protection
   - Input sanitization

2. **Services:**
   - User blocking checks
   - Data validation
   - Access control

3. **Handlers:**
   - Permission verification
   - Error handling
   - Rate limiting

### User Blocking System

```python
# In every handler
if self.user_service.is_user_blocked(user.id):
    return
```

## 📞 Support

- **Email**: holyshithappens@proton.me
- **Telegram**: @FlibustaBotNews
- **GitHub Issues**: Create issue with `new-arch` label

## 📝 Important Documentation

- **`CHANGELOG.md`** - Version history and migration notes
- **`README_CB_MIGRATION.md`** - Database migration guide

---

*Status: Development | Architecture: Clean Architecture | Deployment: Docker on VPS*
