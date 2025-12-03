#/bin/sh

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
    sudo docker compose up -d
    cd - > /dev/null || exit 1
}

function start_api() {
    cd "$(dirname "$0")" || exit 1
    sudo docker compose up -d hm-aurorah-api
    cd - > /dev/null || exit 1
}

function stop() {
    cd "$(dirname "$0")" || exit 1
    sudo docker compose stop
    cd - > /dev/null || exit 1
}

function stop_api() {
    cd "$(dirname "$0")" || exit 1
    sudo docker compose stop hm-aurorah-api
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
case "${1:-api}" in
    all)
        deploy
        ;;
    api)
        deploy_api
        ;;
    *)
        echo "Usage: $0 {all|api}"
        echo "  all - Deploy all services"
        echo "  api - Deploy API service only (default)"
        exit 1
        ;;
esac
