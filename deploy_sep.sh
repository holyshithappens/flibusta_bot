#!/bin/bash
# deploy.sh - Deployment script with functions and options
# Bot and DB now have SEPARATE lifecycles/compose files/projects.
# Routine bot deploys never stop or recreate the DB container.

set -euo pipefail

# Базовые переменные
DOCKER_USERNAME="holyshithappens"
DOCKER_IMAGE_NAME="flbst-bot-mdb"
IMAGE_NAME="$DOCKER_USERNAME/$DOCKER_IMAGE_NAME"
VPS_PATH="flbst-bot-mdb"
GITHUB_REPO="https://github.com/holyshithappens/flibusta_bot.git"
#BRANCH="main"

# Compose files (separate projects on the VPS)
DB_COMPOSE="docker-compose.db.yml"
BOT_COMPOSE="docker-compose.bot.yml"
DB_PROJECT="flibusta-db"
BOT_PROJECT="flibusta-bot"

# Переменные для хранения введенных данных
VPS_IP=""
VPS_USER=""
DOCKER_PASSWORD=""

# Функции
show_usage() {
    cat <<EOF
Usage: $0 [OPTION]
Deploy Flibusta Bot configuration and Docker containers

Options:
  -h, --help        Show this help
  -n, --news        Copy only news file to VPS
  -u, --update      Quick update: pull bot image and restart BOT ONLY
  -d, --init-db      Initialize SQLite databases on VPS (create tables if not exist)
  -s, --sql         Copy only sql and db manager scripts to VPS
      --db-up       Start/recreate the DB container (rare - explicit only)
      --db-restart  Restart the DB container without recreating it
      --status      Show status of both stacks
  (no option)       Full deploy: push new bot image and deploy BOT ONLY
                    (starts the DB stack first only if it isn't already running)
EOF
}

prompt_user_input_vps() {
    echo "🔐 VPS Connection Details"
    read -rp "Enter VPS IP address [162.199.167.194]: " input_ip
    read -rp "Enter VPS username [holy]: " input_user
    VPS_IP=${input_ip:-"162.199.167.194"}
    VPS_USER=${input_user:-"holy"}
}

prompt_user_input_docker() {
    echo ""
    echo "🔐 Docker Hub auth for user: $DOCKER_USERNAME"
    read -rsp "Enter Docker Hub PAT or password: " DOCKER_PASSWORD
    echo
}

copy_config_files() {
    echo ""
    echo "📁 Copying config files to VPS..."
    ssh "$VPS_USER@$VPS_IP" "mkdir -p ~/$VPS_PATH/{data,logs,config}"
    scp .env.prod "$VPS_USER@$VPS_IP:$VPS_PATH/.env"
    scp config/my.cnf.prod "$VPS_USER@$VPS_IP:$VPS_PATH/config/my.cnf"
    scp app/VERSION.py "$VPS_USER@$VPS_IP:$VPS_PATH/VERSION.py"
    scp "$DB_COMPOSE" "$VPS_USER@$VPS_IP:$VPS_PATH/$DB_COMPOSE"
    scp "$BOT_COMPOSE" "$VPS_USER@$VPS_IP:$VPS_PATH/$BOT_COMPOSE"
    echo "✅ Config files copied"
}

copy_sql_files() {
    echo ""
    echo "📁 Copying SQL files on VPS..."

    scp db_init/manage_flibusta_db.sh $VPS_USER@$VPS_IP:$VPS_PATH/db_init/manage_flibusta_db.sh
    scp db_init/zz_*.sql $VPS_USER@$VPS_IP:$VPS_PATH/db_init/
    if ls db_init/sql/*.sql.gz 1> /dev/null 2>&1; then
        echo "📦 Copying SQL.gz files to VPS..."
        rsync -avz --progress --partial db_init/sql/*.sql.gz $VPS_USER@$VPS_IP:$VPS_PATH/db_init/sql
    else
        echo "⚠️  No SQL.gz files found in db_init/sql/"
    fi

    echo "✅ SQL files setup completed"
}

read_deploy_ref() {
    read -rp "Deploy from [branch/tag] (default: main): " DEPLOY_REF
    echo "${DEPLOY_REF:-main}"
}

copy_news_file() {
    echo ""
    echo "📰 Copying news file to VPS..."
    scp ./data/bot_news*.py $VPS_USER@$VPS_IP:$VPS_PATH/data/
    echo "✅ News file copied successfully"
}

setup_permissions() {
    echo ""
    echo "🔧 Setting permissions..."

    ssh $VPS_USER@$VPS_IP << EOF
cd ~/$VPS_PATH
chmod +x db_init/init_db.sh
chmod 755 data logs db_backups
EOF

    echo "✅ Permissions setup completed"
}

build_and_push_image() {
    local deploy_ref="$1"
    echo ""
    echo "🚀 Building and pushing Docker image from '$deploy_ref'..."

    echo "📥 Cloning repo..."
    rm -rf /tmp/flibusta_build
    git clone --branch "$deploy_ref" --single-branch "$GITHUB_REPO" /tmp/flibusta_build

    echo "🐳 Building image..."
    docker build -t "$IMAGE_NAME:latest" /tmp/flibusta_build

    echo "📤 Pushing to Docker Hub..."
    echo "$DOCKER_PASSWORD" | docker login -u "$DOCKER_USERNAME" --password-stdin
    docker push "$IMAGE_NAME:latest"
    docker logout

    rm -rf /tmp/flibusta_build
    echo "✅ Image pushed"
}

# ---------------------------------------------------------------------------
# DB lifecycle — separate from bot, only invoked explicitly
# ---------------------------------------------------------------------------

is_db_running() {
    ssh "$VPS_USER@$VPS_IP" \
        "docker inspect -f '{{.State.Running}}' flibusta-db 2>/dev/null" | grep -q true
}

deploy_db() {
    echo ""
    echo "🗄️  Starting/recreating DB stack (docker-compose.db.yml)..."
    ssh "$VPS_USER@$VPS_IP" "cd ~/$VPS_PATH && \
        docker network create flibusta-net 2>/dev/null || true && \
        docker-compose -p $DB_PROJECT -f $DB_COMPOSE pull && \
        docker-compose -p $DB_PROJECT -f $DB_COMPOSE up -d --force-recreate"
    echo "✅ DB stack deployed"
}

restart_db() {
    echo ""
    echo "🔄 Restarting DB container (no recreate)..."
    ssh "$VPS_USER@$VPS_IP" "cd ~/$VPS_PATH && docker-compose -p $DB_PROJECT -f $DB_COMPOSE restart"
    echo "✅ DB restarted"
}

wait_for_db_healthy() {
    echo ""
    echo "⏳ Waiting for DB to be healthy..."
    ssh "$VPS_USER@$VPS_IP" '
        for i in $(seq 1 30); do
            status=$(docker inspect -f "{{.State.Health.Status}}" flibusta-db 2>/dev/null || echo "missing")
            if [ "$status" = "healthy" ]; then
                echo "✅ DB is healthy"
                exit 0
            fi
            echo "  ...still waiting ($status)"
            sleep 2
        done
        echo "❌ DB did not become healthy in time"
        exit 1
    '
}

# ---------------------------------------------------------------------------
# Bot lifecycle — this is what routine deploys touch
# ---------------------------------------------------------------------------

deploy_bot() {
    echo ""
    echo "🚀 Pulling and starting BOT ONLY (DB untouched)..."
    ssh "$VPS_USER@$VPS_IP" "cd ~/$VPS_PATH && \
        docker-compose -p $BOT_PROJECT -f $BOT_COMPOSE pull && \
        docker-compose -p $BOT_PROJECT -f $BOT_COMPOSE up -d --force-recreate && \
        docker image prune -f"
    echo "✅ Bot deployed"
}

ensure_db_stack_running() {
    if is_db_running; then
        echo "ℹ️  DB stack already running — leaving it untouched."
    else
        echo "ℹ️  DB stack not running — starting it (first-time / after host reboot)."
        deploy_db
        wait_for_db_healthy
    fi
}

check_status() {
    echo ""
    echo "🔍 DB stack status:"
    ssh "$VPS_USER@$VPS_IP" "cd ~/$VPS_PATH && docker-compose -p $DB_PROJECT -f $DB_COMPOSE ps"
    echo ""
    echo "🔍 Bot stack status:"
    ssh "$VPS_USER@$VPS_IP" "cd ~/$VPS_PATH && sleep 3 && docker-compose -p $BOT_PROJECT -f $BOT_COMPOSE ps"
    echo "✅ Status check done"
}

init_sqlite_dbs() {
    echo ""
    echo "🗄️ Initializing SQLite databases on VPS..."

    ssh "$VPS_USER@$VPS_IP" "cd ~/$VPS_PATH && \
        mkdir -p data logs && \
        python3 -c \"
import sqlite3, os

os.makedirs('data', exist_ok=True)
os.makedirs('logs', exist_ok=True)

db_settings = 'data/FlibustaSettings.sqlite'
conn = sqlite3.connect(db_settings)
cursor = conn.cursor()
cursor.execute('''CREATE TABLE IF NOT EXISTS UserSettings (
    User_ID INTEGER NOT NULL UNIQUE,
    MaxBooks INTEGER NOT NULL DEFAULT 20,
    Lang VARCHAR(2) DEFAULT '',
    BookFormat VARCHAR(5) DEFAULT 'fb2',
    LastNewsDate VARCHAR(10) DEFAULT '2000-01-01',
    IsBlocked BOOLEAN DEFAULT FALSE,
    BookSize TEXT DEFAULT '',
    SearchType TEXT DEFAULT 'books',
    Rating TEXT DEFAULT '',
    SearchArea TEXT DEFAULT 'b',
    Locale VARCHAR(5) DEFAULT '',
    PRIMARY KEY(User_ID)
)''')
cursor.execute('CREATE UNIQUE INDEX IF NOT EXISTS IXUserSettings_User_ID ON UserSettings (User_ID)')
conn.commit()
conn.close()
print('✅ FlibustaSettings.sqlite initialized')

db_logs = 'data/FlibustaLogs.sqlite'
conn = sqlite3.connect(db_logs)
cursor = conn.cursor()
cursor.executescript('''
CREATE TABLE IF NOT EXISTS StructuredLog (
    timestamp TEXT NOT NULL,
    category TEXT NOT NULL,
    event_type TEXT NOT NULL,
    user_id INTEGER,
    username TEXT,
    chat_type TEXT NOT NULL,
    chat_id INTEGER,
    data_json TEXT,
    duration_ms INTEGER,
    error_message TEXT,
    error_type TEXT
);
CREATE INDEX IF NOT EXISTS idx_timestamp ON StructuredLog(timestamp);
CREATE INDEX IF NOT EXISTS idx_category ON StructuredLog(category);
CREATE INDEX IF NOT EXISTS idx_event_type ON StructuredLog(event_type);
CREATE INDEX IF NOT EXISTS idx_user_id ON StructuredLog(user_id);
CREATE INDEX IF NOT EXISTS idx_category_timestamp ON StructuredLog(category, timestamp);

CREATE TABLE IF NOT EXISTS UserLog (
    Timestamp VARCHAR(27) NOT NULL,
    UserID INTEGER NOT NULL,
    UserName VARCHAR(50),
    Action VARCHAR(50),
    Detail VARCHAR(255),
    PRIMARY KEY(Timestamp, UserID)
);
CREATE INDEX IF NOT EXISTS IXUserLog_UserID_Timestamp ON UserLog (UserID, Timestamp);

CREATE TABLE IF NOT EXISTS UserPayment (
    PaymentID VARCHAR(100) PRIMARY KEY,
    UserID INTEGER NOT NULL,
    UserName VARCHAR(100),
    Amount DECIMAL(15,2) NOT NULL,
    Currency VARCHAR(10) NOT NULL,
    PaymentMethod VARCHAR(50),
    PaymentDate DATETIME NOT NULL,
    PaymentStatus VARCHAR(20) NOT NULL,
    ProviderChargeID VARCHAR(100),
    TelegramPaymentChargeID VARCHAR(100),
    InvoicePayload TEXT,
    ProviderPaymentChargeID VARCHAR(100),
    OrderInfo TEXT,
    ShippingAddress TEXT,
    CreatedAt DATETIME DEFAULT CURRENT_TIMESTAMP,
    UpdatedAt DATETIME DEFAULT CURRENT_TIMESTAMP,
    Refundable BOOLEAN DEFAULT TRUE,
    RefundedAmount DECIMAL(15,2) DEFAULT 0,
    RefundedAt DATETIME,
    RefundReason TEXT,
    RefundTransactionID VARCHAR(100),
    UserLanguage VARCHAR(10),
    UserTimezone VARCHAR(50),
    IPAddress VARCHAR(45),
    UserAgent TEXT
);
CREATE INDEX IF NOT EXISTS IXUserPayments_UserID ON UserPayment (UserID);
''')
conn.commit()
conn.close()
print('✅ FlibustaLogs.sqlite initialized')
\""

    echo "✅ SQLite databases initialized"
}

# Обработка аргументов командной строки
case "${1:-}" in
    -u|--update)
        echo "🔄 Quick update — BOT ONLY (DB left running)"
        prompt_user_input_vps
        deploy_bot
        check_status
        ;;

    -n|--news)
        prompt_user_input_vps
        copy_news_file
        ;;

    -d|--init-db)
        prompt_user_input_vps
        init_sqlite_dbs
        ;;

    -s|--sql)
        prompt_user_input_vps
        copy_sql_files
        ;;

    --db-up)
        echo "🗄️  Explicit DB (re)deploy requested"
        prompt_user_input_vps
        deploy_db
        wait_for_db_healthy
        ;;

    --db-restart)
        echo "🔄 Explicit DB restart requested (no recreate)"
        prompt_user_input_vps
        restart_db
        ;;

    --status)
        prompt_user_input_vps
        check_status
        ;;

    -h|--help)
        show_usage
        ;;

    "")
        echo "🚀 Full deployment (build + push + deploy BOT ONLY; DB started if not already running)"
        prompt_user_input_vps
        prompt_user_input_docker
        DEPLOY_REF=$(read_deploy_ref)
        copy_config_files
        copy_sql_files
        copy_news_file
        ensure_db_stack_running
        build_and_push_image "$DEPLOY_REF"
        deploy_bot
        check_status
        ;;

    *)
        echo "❌ Unknown option: $1" >&2
        show_usage
        exit 1
        ;;
esac
