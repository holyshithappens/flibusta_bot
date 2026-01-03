# Flibusta Bot

A comprehensive Telegram bot for searching and downloading books from the Flibusta digital library.

## 📚 Project Overview

**Flibusta Bot** is a feature-rich Telegram bot that provides access to the Flibusta library's vast collection of books. Built with Python and powered by MariaDB, it offers full-text search, filtering, and direct book downloads through Telegram.

- **Language**: Python 3.11
- **Bot Framework**: python-telegram-bot
- **Primary Database**: MariaDB 12.0 (Flibusta native database)
- **Secondary Database**: SQLite (user logs and settings)
- **Deployment**: Docker + docker-compose
- **Latest Version**: 1.1.0

## 🛠️ Tech Stack

### Core Dependencies
- **python-telegram-bot** - Telegram Bot API wrapper with job queue support
- **aiohttp** - Async HTTP client for Flibusta requests
- **mysql-connector-python** - MariaDB connection handling
- **beautifulsoup4** - HTML parsing
- **psutil** - System resource monitoring

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
│  │   callbacks, │  │   (MariaDB + │  │  (HTTP)   │ │
│  │   messages)  │  │    SQLite)   │  └───────────┘ │
│  └──────────────┘  └──────────────┘                │
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

**Data Layer** (`database.py`)
- MariaDB connection pooling
- SQLite user data management
- Query execution and result mapping

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
│   ├── logger.py               # Logging configuration
│   ├── utils.py                # Utility functions
│   ├── health.py               # Health checks & cleanup
│   └── VERSION.py              # Version info
├── db_init/
│   ├── manage_flibusta_db.sh   # Database management script
│   ├── README_CB_MIGRATION.md  # Migration documentation
│   ├── sql/                    # Downloaded SQL.gz files from Flibusta
│   └── *.sql                   # Migration & initialization scripts
├── config/
│   └── my.cnf.vps              # MariaDB config for VPS
├── docker-compose.vps.yml      # Docker composition (VPS)
├── Dockerfile                  # Container definition
├── requirements.txt            # Python dependencies
├── deploy.sh                   # Deployment script
└── .env.example               # Environment variables template
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
DB_PASSWORD=flibusta

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
   - `config/my.cnf.vps` → VPS as `config/my.cnf`
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
- Python Telegram bot
- Depends on healthy MariaDB
- Automatic restarts
- Logs and data mounted from host

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
- `cb_libbook_fts` - Full-text search index (created by db_init script)
- Additional tables for pictures and translations (not yet in use)

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

## 🔐 Security Notes

- All sensitive data stored in `.env.vps` (never committed to git)
- Admin panel protected by password
- User data isolated in separate SQLite databases
- Prepared statements prevent SQL injection
- SSH key-based authentication recommended for VPS

## 📞 Support

- **Email**: holyshithappens@proton.me
- **Telegram**: @FlibustaBotNews
- **GitHub Issues**: Create issue with project details

## 📝 Important Documentation

- **`CHANGELOG.md`** - Version history and migration notes
- **`README_CB_MIGRATION.md`** - Database migration guide

---

*Version: 1.1.0 | Deployment: Docker on VPS*