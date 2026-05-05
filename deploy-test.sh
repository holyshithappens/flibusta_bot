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

copy_sql_init_files() {
    echo ""
    echo "📁 Copying SQLite initialization SQL files to VPS..."

    # Ensure db_init directory exists on VPS
    ssh "$VPS_USER@$VPS_IP" "mkdir -p ~/$VPS_PATH/db_init"
    
    # Copy all SQLite init SQL files to VPS
    scp db_init/zz_sqlite_init_*.sql "$VPS_USER@$VPS_IP:$VPS_PATH/db_init/"
    
    echo "✅ SQL initialization files copied"
}

init_sqlite_dbs() {
    echo ""
    echo "🗄️ Initializing SQLite databases on VPS..."

    ssh "$VPS_USER@$VPS_IP" "cd ~/$VPS_PATH && \
        mkdir -p data logs && \
        
        # Initialize FlibustaSettings.sqlite
        sqlite3 data/FlibustaSettings.sqlite < db_init/zz_sqlite_init_user_settings.sql && \
        echo '✅ FlibustaSettings.sqlite initialized' && \
        
        # Initialize FlibustaLogs.sqlite with all required tables
        sqlite3 data/FlibustaLogs.sqlite < db_init/zz_sqlite_init_structured_log.sql && \
        sqlite3 data/FlibustaLogs.sqlite < db_init/zz_sqlite_init_payment_log.sql && \
        echo '✅ FlibustaLogs.sqlite initialized'"

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
        copy_sql_init_files
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
        copy_sql_init_files
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
