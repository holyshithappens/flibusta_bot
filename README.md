# Flibusta Bot Repository

A comprehensive Telegram bot for searching and downloading books from the Flibusta digital library.

## 📚 Project Overview

**Flibusta Bot** is a feature-rich Telegram bot that provides access to the Flibusta library's vast collection of books. Built with Python and powered by MariaDB, it offers full-text search, filtering, and direct book downloads through Telegram.

- **Language**: Python 3.11
- **Bot Framework**: python-telegram-bot
- **Primary Database**: MariaDB 12.0 (Flibusta native database)
- **Secondary Database**: SQLite (user logs and settings)
- **Deployment**: Docker + docker-compose
- **Hosting**: VPS (1 CPU / 1 GB RAM)
- **Latest Version**: 1.1.0

## 🛠️ Tech Stack

### Core Dependencies
- **python-telegram-bot** - Telegram Bot API wrapper with job queue support
- **aiohttp** - Async HTTP client for Flibusta requests
- **mysql-connector-python** - MariaDB connection handling
- **beautifulsoup4** - HTML parsing
- **psutil** - System resource monitoring

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
│   ├── logger.py               # Logging configuration
│   ├── utils.py                # Utility functions
│   ├── health.py               # Health checks & cleanup
│   └── VERSION.py              # Version info
├── db_init/
│   ├── manage_flibusta_db.sh   # Database management script
│   ├── README_CB_MIGRATION.md  # Migration documentation
│   └── *.sql                   # Migration & initialization scripts
├── config/
│   ├── my.cnf                  # Local MySQL config
│   └── my.cnf.vps              # VPS MySQL config
├── .github/
│   ├── workflows/              # CI/CD pipelines
│   └── pull_request_template.md
├── tools/
│   └── df.sh                   # Disk usage script
├── docker-compose.yml          # Docker composition (local)
├── docker-compose.vps.yml      # Docker composition (VPS)
├── Dockerfile                  # Container definition
├── requirements.txt            # Python dependencies
├── pyproject.toml             # Tool configurations (mypy, black, isort)
├── CHANGELOG.md               # Version history
├── flibusta_bot_spec.md       # Detailed specification (1226 lines)
├── refactoring_plan.md        # Refactoring roadmap (50KB)
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

## 🗄️ Database Schema

### MariaDB (Flibusta)
- **cb_books** - Book metadata
- **cb_authors** - Author information
- **cb_genres** - Genre classification
- **cb_series** - Book series
- Full-text indexes on title, author, annotations

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
   DB_HOST=localhost
   DB_USER=flibusta
   DB_PASSWORD=flibusta
   DB_NAME=flibusta
   DB_ROOT_PASSWORD=rootpassword
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

### docker-compose.vps.yml (Production)
- **Resource constraints** - optimized for 1 GB RAM VPS
- **Restart policies** - `unless-stopped` for reliability
- **Health checks** - automatic container restart on failure
- **Volume mounts** - external configs and data directories
- **Environment variables** - loaded from `.env` file

### Resource Limits
```yaml
MariaDB:
  Memory: 768M
  CPU: 0.9 cores
  
Bot:
  Memory: 256M
  CPU: 0.9 cores
```

## 📦 Production Deployment

### Prerequisites for VPS
- VPS with 1 GB RAM, 1 CPU
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
1) Download SQL files from Flibusta
2) Load lib*.sql into database
3) Apply preparation scripts (indexes, full-text search)
4) Activate cb_lib* tables (rename from lib* → cb_lib*)
5) Rollback to cb_lib_old* tables
6) Delete old cb_lib_old* tables
0) Exit
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

### Database Tables

The `cb_` prefixed tables include:
- `cb_books` - Book metadata
- `cb_authors` - Author information
- `cb_avtorname` - Author translations
- `cb_genres` - Genre classifications
- `cb_genrelist` - Genre lists
- `cb_series` - Book series
- `cb_seqname` - Series translations
- `cb_rate` - Book ratings
- `cb_filename` - File information
- `cb_translator` - Translator info
- `cb_annotations` - Annotations (books & authors)
- Additional tables for recommendations and reviews

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

## 📊 Recent Changes (v1.1.0)

### Changed
- Migration to `cb_` prefix for Flibusta tables
- Safe database update strategy with rollback support

### Added
- SQL migration scripts with version control
- Database update documentation
- Rollback procedures

### Fixed (v1.0.0)
- Book downloads across all languages
- Group chat stability

## 📈 Development Status

### Current Focus
- Full function type hints implementation
- Refactoring to class-based architecture
- SQL query optimization

### Known Limitations
- 1 GB RAM resource constraint
- Language filtering in progress

## 📝 Important Files

- **`flibusta_bot_spec.md`** (1226 lines) - Complete system specification
- **`refactoring_plan.md`** (50KB) - Refactoring roadmap and guidelines
- **`CHANGELOG.md`** - Version history and migration notes
- **`README_CB_MIGRATION.md`** - Database migration documentation

## 🔧 Configuration Files

- **`pyproject.toml`** - Tool configurations (mypy, black, isort)
- **`docker-compose.yml`** - Local development stack
- **`docker-compose.vps.yml`** - VPS production stack
- **`.env.example`** - Environment variables template

## 🐛 Error Handling

The bot includes comprehensive error handling for:
- Blocked users (Forbidden errors)
- Expired callback queries
- Network timeouts
- Invalid requests
- General exceptions

See `main.py:25-45` for error handler implementation.

## 📞 Key Module Responsibilities

| Module | Purpose |
|--------|---------|
| `main.py` | Bot initialization, handler registration, error handling |
| `handlers_search.py` | Core search functionality and pagination |
| `database.py` | MariaDB/SQLite abstraction and queries |
| `admin.py` | Admin panel and privileged operations |
| `flibusta_client.py` | External Flibusta API integration |
| `context.py` | User session state management |
| `handlers_payments.py` | Telegram Stars payment processing |

## 🔐 Security Notes

- **Environment variables** - Bot token and credentials in `.env` only (never committed)
- **Admin password protection** - Secure access to admin panel
- **User data isolation** - SQLite user data kept separate from Flibusta database
- **Prepared statements** - MySQL connector prevents SQL injection
- **No secrets in code** - All sensitive data externalized
- **VPS configuration** - SSH key-based authentication recommended

## 📋 Deployment Checklist

### Pre-Deployment
- [ ] Telegram Bot Token obtained from @BotFather
- [ ] VPS credentials (IP, username)
- [ ] Docker Hub account created (for image storage)
- [ ] Docker Hub PAT generated
- [ ] `.env` file configured with all required variables
- [ ] SSH keys configured for VPS access

### Deployment
- [ ] Run `./deploy.sh` for full deployment or appropriate option
- [ ] Monitor deployment script output
- [ ] Verify containers are running: `docker-compose ps`
- [ ] Check logs for errors: `docker-compose logs -f`
- [ ] Test bot with `/start` command

### Post-Deployment
- [ ] Database initialization via `manage_flibusta_db.sh` (if needed)
- [ ] Test search functionality
- [ ] Verify admin panel access
- [ ] Check resource usage: `docker stats`
- [ ] Review logs for any warnings

## 📞 Common Deployment Issues

### Issue: "Bot was blocked by the user"
**Solution**: This is normal - users are blocking the bot. Check logs to see activity.

### Issue: "Query is too old"
**Solution**: Old callback buttons expire. This is handled gracefully in error handler.

### Issue: Database connection fails
**Solution**: Ensure MariaDB container is healthy - check `docker-compose logs db`

### Issue: Out of memory
**Solution**: 1 GB VPS is tight. Monitor with `docker stats`. Consider:
- Increasing VPS resources
- Optimizing queries in `database.py`
- Reducing cache retention in `context.py`

### Issue: Slow searches
**Solution**: 
- Verify full-text indexes created (Option 3 in manage_flibusta_db.sh)
- Check MariaDB logs for query warnings
- Consider running OPTIMIZE on tables

## 🔄 Typical Maintenance Tasks

### Update Bot Code
```bash
./deploy.sh -u
```
Pull latest image and restart containers.

### Update News
```bash
./deploy.sh -n
```
Deploy updated bot news without full rebuild.

### Update Database
```bash
./deploy.sh -s
```
Copy latest SQL scripts, then SSH to VPS:
```bash
cd ~/flbst-bot-mdb/db_init
./manage_flibusta_db.sh
```

### Monitor Resources
```bash
ssh username@vps_ip
cd ~/flbst-bot-mdb
docker stats
```

### View Logs
```bash
docker-compose logs -f bot
docker-compose logs -f db --tail=100
```

### Restart Services
```bash
docker-compose restart
# or specific service
docker-compose restart bot
```

## 📈 Performance Optimization

### Database Optimization
- Full-text indexes on `cb_books` title and `cb_authors` name
- Regular index maintenance via `zz_50_repair_FT.sql`
- Query result caching in `context.py`

### Memory Management
- User session cleanup every 24 hours (see `health.py`)
- Async processing prevents blocking (see `handlers_search.py`)
- Connection pooling in `database.py`

### VPS Resource Usage
- MariaDB: ~500-600 MB (with data)
- Bot: ~50-100 MB
- OS/Docker: ~200-300 MB
- Free buffer: ~100-200 MB

---

*Last Updated: 2025-12-19 | Version: 1.1.0 | Deployment Guide Included*
