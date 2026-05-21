#!/bin/bash
# deploy.sh - Deployment script with functions and options

set -euo pipefail

# Базовые переменные
DOCKER_USERNAME="holyshithappens"
DOCKER_IMAGE_NAME="flbst-bot-mdb"
IMAGE_NAME="$DOCKER_USERNAME/$DOCKER_IMAGE_NAME"
VPS_PATH="flbst-bot-mdb"
GITHUB_REPO="https://github.com/holyshithappens/flibusta_bot.git"
#BRANCH="main"

# Переменные для хранения введенных данных
VPS_IP=""
VPS_USER=""
DOCKER_PASSWORD=""

# Функции
show_usage() {
    cat <<EOF
Usage: $0 [OPTION]
Deploy Flibusta Bot configuration and Docker containers (no DB logic)

Options:
  -h, --help      Show this help
  -n, --news      Copy only news file to VPS
  -u, --update    Quick update (pull image and restart containers)
  -d, --init-db   Initialize SQLite databases on VPS (create tables if not exist)
  -s, --sql       Copy only sql and db manager scripts to VPS
  (no option)     Full deploy: push new image and deploy
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
    scp docker-compose.prod.yml "$VPS_USER@$VPS_IP:$VPS_PATH/docker-compose.yml"
#    scp ./data/bot_news.py "$VPS_USER@$VPS_IP:$VPS_PATH/data/bot_news.py"
#    scp db_init/download_flibusta.sh $VPS_USER@$VPS_IP:$VPS_PATH/db_init/download_flibusta.sh
#    scp db_init/init_db.sh $VPS_USER@$VPS_IP:$VPS_PATH/db_init/init_db.sh
    echo "✅ Config files copied"
}

copy_sql_files() {
    echo ""
    echo "📁 Copying SQL files on VPS..."

    # Копируем SQL файлы если они существуют
    scp db_init/manage_flibusta_db.sh $VPS_USER@$VPS_IP:$VPS_PATH/db_init/manage_flibusta_db.sh
    scp db_init/zz_*.sql $VPS_USER@$VPS_IP:$VPS_PATH/db_init/
    if ls db_init/sql/*.sql.gz 1> /dev/null 2>&1; then
        echo "📦 Copying SQL.gz files to VPS..."
#        scp db_init/sql/*.sql.gz $VPS_USER@$VPS_IP:$VPS_PATH/db_init/sql/
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

    # Копируем файл на VPS
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

    # Build locally
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

deploy_containers() {
    echo ""
    echo "🚀 Pulling and starting containers..."
    ssh "$VPS_USER@$VPS_IP" "cd ~/$VPS_PATH && \
        docker-compose down 2>/dev/null || true && \
        docker-compose pull && \
        docker-compose up -d --force-recreate && \
        docker system prune -f"
    echo "✅ Containers deployed"
}

check_status() {
    echo ""
    echo "🔍 Checking service status..."
    ssh "$VPS_USER@$VPS_IP" "cd ~/$VPS_PATH && sleep 5 && docker-compose ps"
    echo ""
    ssh "$VPS_USER@$VPS_IP" "cd ~/$VPS_PATH && docker-compose logs --tail=20 db | grep -E 'ready|started|error|ERROR'"
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

# --- FlibustaSettings.sqlite ---
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

# --- FlibustaLogs.sqlite ---
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
        echo "🔄 Quick update (pull + restart)"
        prompt_user_input_vps
        deploy_containers
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

    -h|--help)
        show_usage
        ;;

    "")
        echo "🚀 Full deployment (build + push + deploy)"
        prompt_user_input_vps
        prompt_user_input_docker
        DEPLOY_REF=$(read_deploy_ref)
        copy_config_files
        copy_sql_files
#        init_sqlite_dbs
        copy_news_file
#        setup_permissions
        build_and_push_image "$DEPLOY_REF"
        deploy_containers
        check_status
        ;;

    *)
        echo "❌ Unknown option: $1" >&2
        show_usage
        exit 1
        ;;
esac