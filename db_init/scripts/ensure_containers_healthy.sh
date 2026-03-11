#!/bin/bash
# ensure_containers_healthy.sh - Ensures Docker containers are healthy
# This script brings down containers, starts them, and checks their health status

set -e -o pipefail

# Configuration
#DOCKER_COMPOSE_FILE="$HOME/flbst-bot-mdb/docker-compose.yml"
: "${DOCKER_COMPOSE_FILE:=$(cd "$(dirname "$0")/../.." && pwd)/docker-compose.yml}"

# Function to check container health
has_unhealthy_containers() {
    local unhealthy_containers=$(docker ps --format '{{.Names}}: {{.Status}}' | grep -E 'unhealthy|starting' || true)
    if [ -n "$unhealthy_containers" ]; then
        echo "$(date '+%Y-%m-%d %H:%M:%S') - ❌ Unhealthy containers detected:"
        echo "$unhealthy_containers"
        return 0
    else
        echo "$(date '+%Y-%m-%d %H:%M:%S') - ✅ All containers are healthy"
        return 1
    fi
}

# Function to bring down containers
bring_down_containers() {
    echo "$(date '+%Y-%m-%d %H:%M:%S') - 🛑 Bringing down containers..."
    docker-compose -f "$DOCKER_COMPOSE_FILE" down
    echo "$(date '+%Y-%m-%d %H:%M:%S') - ✅ Containers brought down successfully"
}

# Function to bring up containers
bring_up_containers() {
    echo "$(date '+%Y-%m-%d %H:%M:%S') - 🚀 Bringing up containers..."
    docker-compose -f "$DOCKER_COMPOSE_FILE" up -d
    echo "$(date '+%Y-%m-%d %H:%M:%S') - ✅ Containers started"
}

# Function to wait for containers to become healthy
wait_for_healthy_containers() {
    local max_attempts=12
    local attempt=0
    local wait_time=10

    echo "$(date '+%Y-%m-%d %H:%M:%S') - ⏳ Waiting for containers to become healthy..."

    while [ $attempt -lt $max_attempts ]; do
        if has_unhealthy_containers; then
            attempt=$((attempt + 1))
            echo "$(date '+%Y-%m-%d %H:%M:%S') - ⏳ Attempt $attempt/$max_attempts: Waiting $wait_time seconds..."
            sleep $wait_time
        else
            echo "$(date '+%Y-%m-%d %H:%M:%S') - ✅ All containers are healthy"
            return 0
        fi
    done

    echo "$(date '+%Y-%m-%d %H:%M:%S') - ❌ Containers did not become healthy after $max_attempts attempts"
    return 1
}

# Main function
main() {
    echo "$(date '+%Y-%m-%d %H:%M:%S') - 🔄 Starting container health check process"

    local max_attempts=10
    local attempt=0
    local success=false

    for ((attempt=1; attempt<=$max_attempts; attempt++)); do
        echo "$(date '+%Y-%m-%d %H:%M:%S') - 🔄 Attempt $attempt/$max_attempts: Bringing down containers..."
        bring_down_containers

        echo "$(date '+%Y-%m-%d %H:%M:%S') - 🚀 Attempt $attempt/$max_attempts: Bringing up containers..."
        bring_up_containers

        echo "$(date '+%Y-%m-%d %H:%M:%S') - ⏳ Attempt $attempt/$max_attempts: Waiting for containers to become healthy..."
        if wait_for_healthy_containers; then
            success=true
            break
        fi
    done

    if [ "$success" = false ]; then
        echo "$(date '+%Y-%m-%d %H:%M:%S') - ❌ Containers did not become healthy after $max_attempts attempts"
    else
        echo "$(date '+%Y-%m-%d %H:%M:%S') - ✅ Containers are healthy after $attempt attempts"
    fi

    echo "$(date '+%Y-%m-%d %H:%M:%S') - ✅ Container health check process completed"
}

# Run main function
main