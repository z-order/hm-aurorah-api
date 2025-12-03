#!/bin/sh

#
# Usage:
# $ deploy.sh <environment> <target>
#
# For development:
# $ deploy.sh development api
# $ deploy.sh development all
#
# For production:
# $ deploy.sh production api
# $ deploy.sh production all
#

# Get parameters (with defaults)
ENV=${1:-development}
TARGET=${2:-api}

function build_api() {
    cd "$(dirname "$0")/.." || exit 1
    sudo docker build -f deployment/Dockerfile -t hm-aurorah-api .
    cd - > /dev/null || exit 1
}

function build() {
    build_api
}

function start() {
    cd "$(dirname "$0")" || exit 1
    if [ "$ENV" = "development" ]; then
        sudo docker compose -f docker-compose.dev.yml up -d
    else
        sudo docker compose -f docker-compose.prod.yml up -d
    fi
    cd - > /dev/null || exit 1
}

function start_api() {
    cd "$(dirname "$0")" || exit 1
    if [ "$ENV" = "development" ]; then
        sudo docker compose -f docker-compose.dev.yml up -d hm-aurorah-api
    else
        sudo docker compose -f docker-compose.prod.yml up -d hm-aurorah-api
    fi
    cd - > /dev/null || exit 1
}

function stop() {
    cd "$(dirname "$0")" || exit 1
    if [ "$ENV" = "development" ]; then
        sudo docker compose -f docker-compose.dev.yml stop
    else
        sudo docker compose -f docker-compose.prod.yml stop
    fi
    cd - > /dev/null || exit 1
}

function stop_api() {
    cd "$(dirname "$0")" || exit 1
    if [ "$ENV" = "development" ]; then
        sudo docker compose -f docker-compose.dev.yml stop hm-aurorah-api
    else
        sudo docker compose -f docker-compose.prod.yml stop hm-aurorah-api
    fi
    cd - > /dev/null || exit 1
}

function restart() {
    stop
    start
}

function restart_api() {
    stop_api
    start_api
}

function deploy() {
    build
    restart
}

function deploy_api() {
    build_api
    restart_api
}

# Handle command line arguments
case "$TARGET" in
    all)
        deploy
        ;;
    api)
        deploy_api
        ;;
    *)
        echo "Usage: $0 <environment> <target>"
        echo "  environment: development | production (default: development)"
        echo "  target: all | api (default: api)"
        exit 1
        ;;
esac
