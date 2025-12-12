#!/bin/sh

#
# Usage:
# $ deploy.sh <environment> <target>
#
# For local:
# $ deploy.sh local api
# $ deploy.sh local all
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
ENV=${1:-}
TARGET=${2:-api}

# Log message with timestamp
log() {
    echo "[ -_- ] $(date '+%Y-%m-%d %H:%M:%S') - $1"
}

build_api() {
    log "Building hm-aurorah-api..."
    cd "$(dirname "$0")/.." || exit 1
    sudo docker build -f deployment/Dockerfile -t hm-aurorah-api .
    log "Build completed successfully"
    cd - > /dev/null || exit 1
}

build_all() {
    log "Building all services..."
    build_api
    log "All services built"
}

start_api() {
    log "Starting hm-aurorah-api container (${ENV})..."
    cd "$(dirname "$0")" || exit 1
    if [ "$ENV" = "local" ]; then
        sudo docker compose -f docker-compose.local.yml up -d hm-aurorah-api
    elif [ "$ENV" = "development" ]; then
        sudo docker compose -f docker-compose.dev.yml up -d hm-aurorah-api
    else
        sudo docker compose -f docker-compose.prod.yml up -d hm-aurorah-api
    fi
    log "hm-aurorah-api container started"
    cd - > /dev/null || exit 1
}

start_all() {
    log "Starting all containers (${ENV})..."
    cd "$(dirname "$0")" || exit 1
    if [ "$ENV" = "local" ]; then
        sudo docker compose -f docker-compose.local.yml up -d
    elif [ "$ENV" = "development" ]; then
        sudo docker compose -f docker-compose.dev.yml up -d
    else
        sudo docker compose -f docker-compose.prod.yml up -d
    fi
    log "All containers started"
    cd - > /dev/null || exit 1
}

stop_api() {
    log "Stopping hm-aurorah-api container (${ENV})..."
    cd "$(dirname "$0")" || exit 1
    if [ "$ENV" = "local" ]; then
        sudo docker compose -f docker-compose.local.yml stop hm-aurorah-api
    elif [ "$ENV" = "development" ]; then
        sudo docker compose -f docker-compose.dev.yml stop hm-aurorah-api
    else
        sudo docker compose -f docker-compose.prod.yml stop hm-aurorah-api
    fi
    log "hm-aurorah-api container stopped"
    cd - > /dev/null || exit 1
}

stop_all() {
    log "Stopping all containers (${ENV})..."
    cd "$(dirname "$0")" || exit 1
    if [ "$ENV" = "local" ]; then
        sudo docker compose -f docker-compose.local.yml stop
    elif [ "$ENV" = "development" ]; then
        sudo docker compose -f docker-compose.dev.yml stop
    else
        sudo docker compose -f docker-compose.prod.yml stop
    fi
    log "All containers stopped"
    cd - > /dev/null || exit 1
}

restart_api() {
    stop_api
    start_api
}

restart_all() {
    stop_all
    start_all
}

deploy_api() {
    log "Deploying hm-aurorah-api (${ENV})..."
    build_api
    restart_api
    log "hm-aurorah-api deployment complete"
}

deploy_all() {
    log "Deploying all services (${ENV})..."
    build_all
    restart_all
    log "All services deployment complete"
}

show_help() {
    cat <<EOF

╔════════════════════════════════════════════════════════════════════════════╗
║                           DEPLOY HELPER SCRIPT                             ║
╚════════════════════════════════════════════════════════════════════════════╝

USAGE:
  $0 <environment> <target>

ARGUMENTS:
  environment: local | development | production
  target:      all | api (default: api)

EXAMPLES:
  $0 local api
  $0 development all
  $0 production api

EOF
}

# Validate environment
if [ -z "$ENV" ]; then
    show_help
    exit 1
fi

# Handle environment
case "$ENV" in
    local)
        ;;
    development)
        ;;
    production)
        ;;
    help|--help|-h)
        show_help
        exit 1
        ;;
    *)
        show_help
        exit 1
        ;;
esac

# Handle target
case "$TARGET" in
    all)
        deploy_all
        ;;
    api)
        deploy_api
        ;;
    *)
        show_help
        exit 1
        ;;
esac
