#!/bin/bash
# deploy-test.sh - Simple deployment script for test environment

set -euo pipefail

# Базовые переменные
DOCKER_USERNAME="holyshithappens"
DOCKER_IMAGE_NAME="flbst-bot-mdb"
IMAGE_NAME="$DOCKER_USERNAME/$DOCKER_IMAGE_NAME"
IMAGE_TAG="test"
VPS_PATH="flbst-bot-mdb-test"
GITHUB_REPO="https://github.com/holyshithappens/flibusta_bot.git"

# Переменные для хранения введенных данных
VPS_IP=""
VPS_USER=""
DOCKER_PASSWORD=""

# Функции
show_usage() {
    cat <<EOF
Usage: $0 [OPTION]
Deploy Flibusta Bot TEST environment (bot only, uses production database)

Options:
  -u, --update    Quick update (pull image and restart containers)
  -d, --init-db   Initialize SQLite databases on VPS (create tables if not exist)
  -n, --news      Copy only news files to VPS
  -h, --help      Show this help
  (no option)     Full deploy: build test image, copy config and deploy
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
    echo "📁 Copying test config files to VPS..."
#    ssh "$VPS_USER@$VPS_IP" "mkdir -p ~/$VPS_PATH/{data,logs}"
    scp .env.test "$VPS_USER@$VPS_IP:$VPS_PATH/.env"
    scp docker-compose.test.yml "$VPS_USER@$VPS_IP:$VPS_PATH/docker-compose.yml"
    echo "✅ Config files copied"
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

copy_news_file() {
    echo ""
    echo "📰 Copying news file to VPS..."

    # Копируем файл на VPS
    scp ./data/bot_news*.py $VPS_USER@$VPS_IP:$VPS_PATH/data/

    echo "✅ News file copied successfully"
}

build_and_push_test_image() {
    local deploy_ref="$1"
    echo ""
    echo "🚀 Building and pushing TEST Docker image from '$deploy_ref'..."

    # Build locally
    echo "📥 Cloning repo..."
    rm -rf /tmp/flibusta_build_test
    git clone --branch "$deploy_ref" --single-branch "$GITHUB_REPO" /tmp/flibusta_build_test

    echo "🐳 Building test image..."
    docker build -t "$IMAGE_NAME:$IMAGE_TAG" /tmp/flibusta_build_test

    echo "📤 Pushing to Docker Hub..."
    echo "$DOCKER_PASSWORD" | docker login -u "$DOCKER_USERNAME" --password-stdin
    docker push "$IMAGE_NAME:$IMAGE_TAG"
    docker logout

    rm -rf /tmp/flibusta_build_test
    echo "✅ Test image pushed"
}

deploy_containers() {
    echo ""
    echo "🚀 Pulling and starting test containers..."
    ssh "$VPS_USER@$VPS_IP" "cd ~/$VPS_PATH && \
        docker-compose down 2>/dev/null || true && \
        docker-compose pull && \
        docker-compose up -d --force-recreate && \
        docker system prune -f"
    echo "✅ Test containers deployed"
}

check_status() {
    echo ""
    echo "🔍 Checking test service status..."
    ssh "$VPS_USER@$VPS_IP" "cd ~/$VPS_PATH && sleep 5 && docker-compose ps"
    echo ""
    ssh "$VPS_USER@$VPS_IP" "cd ~/$VPS_PATH && docker-compose logs --tail=20 bot-test | grep -E 'ready|started|error|ERROR'"
    echo "✅ Status check done"
}

read_deploy_ref() {
    read -rp "Deploy from [branch/tag] (default: main): " DEPLOY_REF
    echo "${DEPLOY_REF:-main}"
}

# Обработка аргументов командной строки
case "${1:-}" in
    -u|--update)
        echo "🔄 Quick update (pull + restart)"
        prompt_user_input_vps
        deploy_containers
        check_status
        ;;

    -d|--init-db)
        prompt_user_input_vps
        init_sqlite_dbs
        ;;

    -n|--news)
        prompt_user_input_vps
        copy_news_file
        ;;

    -h|--help)
        show_usage
        ;;

    "")
        echo "🚀 Full test deployment (build + copy config + deploy)"
        prompt_user_input_vps
        prompt_user_input_docker
        DEPLOY_REF=$(read_deploy_ref)
        copy_config_files
        init_sqlite_dbs
        copy_news_file
        build_and_push_test_image "$DEPLOY_REF"
        deploy_containers
        check_status
        ;;

    *)
        echo "❌ Unknown option: $1" >&2
        show_usage
        exit 1
        ;;
esac
