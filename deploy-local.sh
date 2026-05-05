#!/bin/bash
# deploy-local.sh - Локальное развертывание приложения

set -e

# Конфигурация
DOCKER_USERNAME="holyshithappens"
DOCKER_IMAGE_NAME="flbst-bot-mdb"
IMAGE_NAME="$DOCKER_USERNAME/$DOCKER_IMAGE_NAME"
PROJECT_DIR="."

# Функции
show_usage() {
    echo "Usage: $0 [OPTION]"
    echo "Local deployment script for Flibusta Bot"
    echo ""
    echo "Options:"
    echo "  -u, --update    Quick update (restart containers without rebuild)"
    echo "  -h, --help      Show this help message"
    echo ""
    echo "Without options: Full deployment (build and deploy)"
}

build_local_image() {
    echo "🚀 Building Docker image from local files..."

    # Сборка образа из текущей директории
    docker build -t "$IMAGE_NAME:dev" .

    echo "✅ Local image build completed"
}

deploy_containers() {
    echo "🚀 Deploying containers..."

    cd "$PROJECT_DIR"
    docker-compose down bot || true
    # Запускаем без автоматического пересоздания
    docker-compose up -d bot

    echo "✅ Container deployment completed"
}

check_status() {
    echo "🔍 Checking service status..."

    cd "$PROJECT_DIR"
    sleep 10
    docker-compose ps
    echo ""
    docker-compose logs --tail=10 db bot

    echo "✅ Status check completed"
}

cleanup_docker() {
    echo "🧹 Cleaning up Docker..."
    docker system prune -f
}

# Обработка аргументов
case "${1:-}" in
    -u|--update)
        echo "🔄 Starting QUICK update..."
        deploy_containers
        check_status
        echo "✅ Quick update completed!"
        ;;

    -h|--help)
        show_usage
        ;;

    "")
        echo "🚀 Starting FULL deployment..."
        build_local_image
        deploy_containers
        check_status
        cleanup_docker
        echo "✅ Full deployment completed!"
        ;;

    *)
        echo "Error: Unknown option $1"
        show_usage
        exit 1
        ;;
esac