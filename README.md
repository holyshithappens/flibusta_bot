# Flibusta Bot Repository

A comprehensive Telegram bot for searching and downloading books from the Flibusta digital library.

## 📚 Project Overview

**Flibusta Bot** is a feature-rich Telegram bot that provides access to the Flibusta library's vast collection of books. Built with Python and powered by MariaDB, it offers full-text search, filtering, and direct book downloads through Telegram.

- **Language**: Python 3.11
- **Bot Framework**: python-telegram-bot
- **Primary Database**: MariaDB 12.0 (Flibusta native database)
- **Secondary Database**: SQLite (user logs and settings)
- **Deployment**: Docker + docker-compose
- **Hosting**: VPS (2 CPU / 2 GB RAM)
- **Latest Version**: 1.2.0

## 🛠️ Tech Stack

### Core Dependencies
- **python-telegram-bot** - Telegram Bot API wrapper with job queue support
- **aiohttp** - Async HTTP client for Flibusta requests
- **mysql-connector-python** - MariaDB connection handling
- **beautifulsoup4** - HTML parsing
- **psutil** - System resource monitoring
- **pyyaml** - YAML parsing for i18n translations

### Development Tools
- **mypy** - Static type checking (Python 3.11)
- **black** - Code formatting (line length: 120)
- **isort** - Import sorting

## 📁 Project Structure

```
flibusta_bot/
├── app/
│   ├── main.py                 # Bot entry point & handler registration
│   ├── handlers_basic.py       # Core commands (/start, /help, /about, etc.)
│   ├── handlers_search.py      # Book search functionality
│   ├── handlers_callback.py    # Button & inline query callbacks
│   ├── handlers_group.py       # Group chat message handling
│   ├── handlers_info.py        # Information display handlers
│   ├── handlers_settings.py    # User search preferences
│   ├── handlers_utils.py       # Handler utilities
│   ├── handlers_payments.py    # Telegram Stars payments
│   ├── database.py             # Database abstraction layer
│   ├── admin.py                # Admin panel & commands
│   ├── context.py              # User context management
│   ├── flibusta_client.py      # HTTP client for Flibusta
│   ├── constants.py            # Application constants
│   ├── custom_types.py         # Type definitions
│   ├── tools.py                # Bot utility tools
│   ├── utils.py                # Utility functions
│   ├── health.py               # Health checks & cleanup
│   ├── VERSION.py              # Version info
│   ├── core/                   # Core modules
│   │   ├── logging_schema.py   # Structured logging schema
│   │   └── structured_logger.py # JSON format logger
│   ├── i18n/                   # Internationalization
│   │   ├── i18n.py             # i18n helper functions
│   │   ├── locale_manager.py   # Locale management
│   │   ├── plural_rules.py     # Pluralization rules
│   │   └── translations/       # Translation files
│   │       ├── en.yaml         # English translations
│   │       └── ru.yaml         # Russian translations
│   └── repositories/           # Data access layer
│       ├── base_sqlite.py      # Base SQLite repository
│       └── logs_repository.py  # Logs repository
├── app_ref/                     # Reference architecture
│   ├── core/
│   ├── handlers/
│   ├── repositories/
│   └── utils/
├── db_init/
│   ├── manage_flibusta_db.sh   # Database management script
│   ├── README_CB_MIGRATION.md  # Migration documentation
│   ├── sql/                     # SQL files directory
│   │   └── cb_libgenrelist_en.sql  # English genre translations
│   ├── zz_00_rollback_cb_tables.sql
│   ├── zz_01_cleanup_old_tables.sql
│   ├── zz_10_convert_charset.sql
│   ├── zz_20_create_indexes.sql
│   ├── zz_30_create_FT_indexes.sql
│   ├── zz_40_fill_FT.sql
│   ├── zz_50_repair_FT.sql
│   ├── zz_55_check_migration.sql
│   ├── zz_56_db_statistics.sql
│   ├── zz_59_migrate_cb_tables_to_old.sql
│   ├── zz_60_migrate_to_cb_tables.sql
│   ├── zz_65_copy_lib_to_cb_tables.sql
│   ├── zz_sqlite_init_payment_log.sql
│   ├── zz_sqlite_init_structured_log.sql
│   ├── zz_sqlite_init_user_log.sql
│   ├── zz_sqlite_init_user_settings.sql
│   └── scripts/                # Database management scripts
├── config/
│   ├── my.cnf                  # Local MySQL config
│   └── my.cnf.vps              # VPS MySQL config
├── data/
│   ├── bot_news_en.py          # English news content
│   ├── bot_news_ru.py          # Russian news content
│   └── bot_news_*.example.py   # Example templates
├── docs/
│   ├── FLIBUSTA_BOT_SPEC.md   # Detailed specification
│   ├── USER_GUIDE.md          # User guide
│   └── vps_performance_guide.md # VPS optimization guide
├── .github/
│   ├── workflows/              # CI/CD pipelines
│   └── pull_request_template.md
├── docker-compose.yml          # Docker composition (local)
├── docker-compose.vps.yml      # Docker composition (VPS)
├── docker-compose.prod.yml     # Docker composition (production)
├── docker-compose.test.yml     # Docker composition (testing)
├── deploy.sh                   # Production deployment script
├── deploy-local.sh             # Local deployment script
├── deploy-test.sh              # Test deployment script
├── Dockerfile                  # Container definition
├── requirements.txt            # Python dependencies
├── requirements-dev.txt        # Development dependencies
├── pyproject.toml             # Tool configurations (mypy, black, isort)
├── CHANGELOG.md               # Version history
└── .env.example               # Environment variables template
```

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
- **Full-text search** across book database
- **Multi-field search** - title, author, genre, series, year
- **Annotation search** - book and author annotations
- **Series grouping** - books organized by series
- **Author grouping** - books by specific authors
- **Pagination** - navigate through search results
- **Filtering** - rating-based filtering

### Advanced Features
- **Group chat support** - bot works in group conversations
- **User preferences** - customizable search settings
- **Payment integration** - Telegram Stars support
- **Admin panel** - moderation and statistics
- **Async processing** - efficient concurrent request handling
- **Error handling** - comprehensive error recovery
- **Internationalization (i18n)** - multi-language support (RU/EN)
- **Structured logging** - JSON format logs for analytics
- **Analytical views** - database views for statistics

## 🏗️ Architecture

### System Architecture
```
┌─────────────────────────────────────────────────────┐
│                  Telegram Bot API                   │
└─────────────────────┬───────────────────────────────┘
                       │
┌─────────────────────▼───────────────────────────────┐
│              Python Application                     │
│  ┌──────────────┐  ┌──────────────┐  ┌───────────┐ │
│  │   Handlers   │  │   Database   │  │  Flibusta │ │
│  │   (commands, │◄─┤   Layer      │◄─┤  Client   │ │
│  │   callbacks, │  │ (Repositories│  │  (HTTP)   │ │
│  │   messages)  │  │  + MariaDB + │  └───────────┘ │
│  └──────────────┘  │   SQLite)    │                │
│         │           └──────────────┘                │
│         │                                          │
│  ┌──────▼────────┐  ┌──────────────────────────┐  │
│  │  i18n Module  │  │  Structured Logging       │  │
│  │ (translations,│  │  (JSON format,           │  │
│  │  locale mgmt) │  │   analytics views)        │  │
│  └───────────────┘  └──────────────────────────┘  │
└─────────────────────────────────────────────────────┘
                       │
          ┌────────────┴────────────┐
          ▼                         ▼
┌─────────────────┐    ┌──────────────────┐
│   MariaDB       │    │   SQLite DBs     │
│  (books, authors,    │  (logs, user     │
│   genres, series)    │   settings)      │
└─────────────────┘    └──────────────────┘
```

### Layer Breakdown

**Presentation Layer** (`handlers_*.py`)
- Handles user interactions and commands
- Manages UI responses and pagination
- Processes callbacks and inline queries

**Business Logic** (`flibusta_client.py`, `context.py`)
- HTTP communication with Flibusta
- User session and context management
- Search query processing

**Internationalization Layer** (`i18n/`)
- Multi-language support (RU/EN)
- Translation management via YAML files
- Locale detection and switching
- Pluralization rules support

**Data Layer** (`database.py`, `repositories/`)
- MariaDB connection pooling
- SQLite user data management
- Repository pattern for data access
- Query execution and result mapping

**Logging Layer** (`core/`)
- Structured JSON format logging
- Analytical database views (not yet)
- Log parsing and transformation

## 🗄️ Database Schema

### MariaDB (Flibusta)
- **cb_libbook** - Book metadata
- **cb_libavtor** - Author-book relationships
- **cb_libavtorname** - Author information
- **cb_libgenre** - Book-genre relationships
- **cb_libgenrelist** - Genre classification (Russian)
- **cb_libgenrelist_en** - Genre classification (English translations)
- **cb_libseq** - Book-series relationships
- **cb_libseqname** - Series information
- **cb_librate** - Book ratings
- **cb_librecs** - Recommendations
- **cb_libreviews** - Reviews
- **cb_libbannotations** - Book annotations
- **cb_libaannotations** - Author annotations
- **cb_libbook_fts** - Full-text search index

### SQLite
- **User sessions** - active user tracking
- **User preferences** - search settings and favorites
- **Logs** - interaction history

## 🚀 Getting Started

### Prerequisites
- Python 3.11+
- Docker & Docker Compose (for containerized deployment)
- MariaDB 12.0
- Telegram Bot Token (from @BotFather)
- VPS access (for production deployment)

### Local Development Setup

1. **Clone and configure**:
   ```bash
   git clone https://github.com/holyshithappens/flibusta_bot.git
   cd flibusta_bot
   cp .env.example .env
   ```

2. **Edit environment variables** in `.env`:
   ```env
   BOT_TOKEN=your_bot_token_here
   TZ=Europe/Moscow
   BOT_USERNAME=your_bot_username
   DB_HOST=localhost
   DB_PORT=3306
   DB_NAME=flibusta
   DB_USER=flibusta
   DB_PASSWORD=flibusta
   ADMIN_PASSWORD=your_admin_password
   # Feedback contacts
   FEEDBACK_EMAIL=your_email@example.com
   FEEDBACK_PIKABU=https://pikabu.ru/@username
   FEEDBACK_PIKABU_USERNAME=@username
   FEEDBACK_TELEGRAM=https://t.me/username
   FEEDBACK_TELEGRAM_NAME=@username
   # Crypto donation addresses
   DONATE_SOL=your_sol_address
   DONATE_BTC=your_btc_address
   DONATE_ETH=your_eth_address
   DONATE_POL=your_pol_address
   DONATE_SUI=your_sui_address
   DONATE_TON=your_ton_address
   DONATE_TRX=your_trx_address
   ```

3. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

4. **Run locally**:
   ```bash
   python app/main.py
   ```

### Local Docker Deployment

**Start containers**:
```bash
docker-compose up -d
```

**View logs**:
```bash
docker-compose logs -f bot
docker-compose logs -f db
```

**Stop containers**:
```bash
docker-compose down
```

## 🐳 Docker Configuration

### docker-compose.yml (Local Development)
- **MariaDB 12.0** - 768MB memory limit
- **Bot container** - 256MB memory limit
- **Named volumes** - persist database data
- **Network** - internal communication between services

### docker-compose.test.yml (Test Environment)
- **Resource constraints** - optimized for 2 GB RAM / 2 CPU VPS
- **Restart policies** - `unless-stopped` for reliability
- **Health checks** - automatic container restart on failure
- **Volume mounts** - external configs and data directories
- **Environment variables** - loaded from `.env` file

### docker-compose.prod.yml (Production Alternative)
- **Simplified production** - alternative production configuration
- **Optimized resources** - tailored for production workloads
- **Service isolation** - separate containers for bot and database

### Resource Limits
```yaml
MariaDB:
  Memory: 1.0G
  CPU: 1.5 cores
  
Bot:
  Memory: 256M
  CPU: 0.8 cores
```

## 📦 Production Deployment

### Prerequisites for VPS
- VPS with 2 GB RAM, 2 CPU
- SSH access to VPS
- Docker & Docker Compose installed on VPS
- Docker Hub account (for image pushing)
- Flibusta database SQL files

### Deployment Script (`deploy.sh`)

The project includes an automated deployment script with multiple options:

#### 1. Full Deployment (Initial Setup)
```bash
./deploy.sh
```
**Actions**:
- Prompts for VPS credentials (IP, username)
- Prompts for Docker Hub PAT
- Prompts for git branch/tag to deploy from
- Copies config files (`.env`, `docker-compose.yml`, MySQL config)
- Copies SQL migration scripts
- Copies news file
- Builds Docker image locally
- Pushes image to Docker Hub
- Checks service status

#### 2. Quick Update (Restart Containers)
```bash
./deploy.sh -u
# or
./deploy.sh --update
```
**Actions**:
- Prompts for VPS credentials
- Pulls latest image from Docker Hub
- Restarts containers with `--force-recreate`
- Cleans up unused Docker resources

#### 3. Update News File
```bash
./deploy.sh -n
# or
./deploy.sh --news
```
**Actions**:
- Copies `data/bot_news.py` to VPS
- Useful for quick news updates without full deployment

#### 4. Update SQL/Database Scripts
```bash
./deploy.sh -s
# or
./deploy.sh --sql
```
**Actions**:
- Copies SQL migration scripts to VPS
- Copies database management script (`manage_flibusta_db.sh`)
- Useful for database updates

#### 5. Help
```bash
./deploy.sh -h
# or
./deploy.sh --help
```

### Step-by-Step VPS Deployment

#### Step 1: Prepare Local Environment
```bash
# Copy VPS environment file
cp .env.example .env.vps

# Edit with VPS credentials
nano .env.vps
```

#### Step 2: Run Full Deployment
```bash
./deploy.sh
```

When prompted:
- **VPS IP**: `162.199.167.194` (or your VPS IP)
- **VPS Username**: `holy` (or your username)
- **Docker Hub PAT**: Your Docker Hub personal access token
- **Deploy from**: `main` (or specific branch/tag)

#### Step 3: Monitor Deployment
The script will:
1. Build Docker image from source
2. Push to Docker Hub
3. SSH into VPS and pull the image
4. Start containers
5. Show container status and logs

#### Step 4: Verify Services
```bash
# SSH into VPS
ssh username@vps_ip

# Check containers
cd ~/flbst-bot-mdb
docker-compose ps

# View bot logs
docker-compose logs -f bot

# View database logs
docker-compose logs -f db
```

## 🗄️ Database Management

### Initial Database Setup

On VPS, use the database management script:

```bash
# SSH into VPS
ssh username@vps_ip
cd ~/flbst-bot-mdb/db_init

# Run management script
./manage_flibusta_db.sh
```

### Database Manager Menu

```
🔧 Flibusta DB Manager
1) Скачать SQL-файлы (в sql/)
2) Загрузить lib*.sql в БД (staging)
3) Применить скрипты подготовки (zz_10 → zz_50)
4) Переименовать lib* → cb_lib* (активация)
5) Откат: cb_lib*_old → cb_lib*
6) Удалить старые cb_lib*_old
7) Удалить все .sql.gz в sql/
0) Выйти
```

### Database Initialization Workflow

**Scenario 1: Fresh Installation**
1. Option 1: Download SQL files
   - Select required files or include optional tables
   - Files download to `db_init/sql/`

2. Option 2: Load SQL into database
   - Decompresses `.sql.gz` files
   - Loads into staging `lib_*` tables
   - Avoids overwriting existing `cb_lib_*` tables

3. Option 3: Apply preparation scripts
   - Converts charset to UTF-8
   - Creates indexes for better performance
   - Creates full-text search indexes
   - Fills and repairs full-text tables
   - Improves query speed

4. Option 4: Activate new tables
   - Renames existing `cb_lib_*` → `cb_lib_*_old` (backup)
   - Renames new `lib_*` → `cb_lib_*` (activate)
   - Safe rollback available if needed

**Scenario 2: Update Existing Database**
1. Use Options 1-3 to stage new data
2. Use Option 4 to safely activate
3. Use Option 5 to rollback if issues occur
4. Use Option 6 to clean up old tables after verification

**Scenario 3: Rollback Failed Update**
```
Option 5: Rollback to cb_lib_old*
- Restores previous tables
- No data loss
```

### SQL Migration Files

Located in `db_init/`:
- **zz_00_rollback_cb_tables.sql** - Rollback to previous version
- **zz_01_cleanup_old_tables.sql** - Remove backup tables
- **zz_10_convert_charset.sql** - UTF-8 conversion
- **zz_20_create_indexes.sql** - Create indexes
- **zz_30_create_FT_indexes.sql** - Create full-text indexes
- **zz_40_fill_FT.sql** - Populate full-text indexes
- **zz_50_repair_FT.sql** - Repair full-text tables
- **zz_59_migrate_cb_tables_to_old.sql** - Backup current tables
- **zz_60_migrate_to_cb_tables.sql** - Activate new tables (RENAME operation)
- **zz_65_copy_lib_to_cb_tables.sql** - Copy lib* → cb_lib* (preserves original tables)

### Migration Strategy: RENAME vs COPY

**Standard Approach (zz_60_migrate_to_cb_tables.sql):**
```sql
RENAME TABLE libbook TO cb_libbook;  -- Atomic, fast
```
- ✅ Fast operation (instant for MariaDB)
- ✅ Atomic - no data loss risk
- ✅ Preserves indexes and constraints
- ❌ Original lib* tables removed
- **Time**: < 1 second
- **Recommended for**: Production deployments after testing

**Copy Approach (zz_65_copy_lib_to_cb_tables.sql):**
```sql
CREATE TABLE cb_libbook LIKE libbook;
INSERT INTO cb_libbook SELECT * FROM libbook;
```
- ✅ Preserves original lib* tables (safe backup)
- ✅ Allows parallel table operation
- ✅ Easy rollback (just delete cb_lib* tables)
- ❌ Takes longer execution time
- ❌ Temporarily uses double disk space
- **Time**: 5-30 minutes (depends on data size)
- **Recommended for**: Testing, validation, conservative deployments

**When to use each:**

| Scenario | Use |
|----------|-----|
| Fresh installation | zz_60 (RENAME) - faster, cleaner |
| Testing migration | zz_65 (COPY) - preserve original data |
| Dual operation | zz_65 (COPY) - parallel tables |
| Have backup | zz_60 (RENAME) - safe enough |
| Risk aversion | zz_65 (COPY) - easy rollback |
| Disk space tight | zz_60 (RENAME) - uses less space |

## 📊 Recent Changes (v1.2.0)

### Added (v1.2.0 - 2026-05-05)
- **Internationalization (i18n)** - Full support for RU/EN locales
- **i18n module** - Translation management with YAML files
- **Language settings** - Users can switch interface language in menu
- **Structured logging** - JSON format logs for better analytics
- **Analytical database views** - For advanced statistics
- **Log parser** - Convert old logs to new structured format

### In Planning (v1.2.0)
- Refactoring to Service/Repository/Handler architecture
- Splitting `database.py` into dedicated repositories
- Creating service layer for business logic

### Fixed (v1.1.11 - 2026-04-28)
- Corrected queries for searching novelties and popular books

### Fixed (v1.1.10 - 2026-04-10)
- Removed error nested query limitations for popular/new books search

### Added (v1.1.9 - 2026-03-19)
- Show current bot version in admin panel

### Fixed (v1.1.8 - 2026-03-05)
- Resolved log_payment error

### Fixed (v1.1.7 - 2026-03-05)
- Corrected number of authors calculation

### Fixed (v1.1.6 - 2026-02-15)
- Removed cache repopulation issues

### Fixed (v1.1.5 - 2026-02-07)
- Cleanup interval set to 3600 seconds

### Fixed (v1.1.4 - 2026-02-07)
- Cache invalidation after database updates
- Cleanup of inactive user sessions
