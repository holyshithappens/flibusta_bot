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
  -u, --update    Quick update (pull image and restart containers)
  -h, --help      Show this help
  -n, --news      Copy only news file to VPS
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
    scp .env.vps "$VPS_USER@$VPS_IP:$VPS_PATH/.env"
    scp config/my.cnf.vps "$VPS_USER@$VPS_IP:$VPS_PATH/config/my.cnf"
    scp docker-compose.vps.yml "$VPS_USER@$VPS_IP:$VPS_PATH/docker-compose.yml"
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
#    if ls db_init/sql/*.sql.gz 1> /dev/null 2>&1; then
#        echo "📦 Copying SQL.gz files to VPS..."
##        scp db_init/sql/*.sql.gz $VPS_USER@$VPS_IP:$VPS_PATH/db_init/sql/
#        rsync -avz --progress --partial db_init/sql/*.sql.gz $VPS_USER@$VPS_IP:$VPS_PATH/db_init/sql
#    else
#        echo "⚠️  No SQL.gz files found in db_init/sql/"
#    fi

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
    scp ./data/bot_news.py $VPS_USER@$VPS_IP:$VPS_PATH/data/bot_news.py

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