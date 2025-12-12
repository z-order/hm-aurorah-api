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
COMMAND=${1:-help}
if [ $# -gt 0 ]; then
    shift
fi

# List all containers in a specific project
list_containers() {
    sudo docker ps --filter "label=com.docker.compose.project=aurorah"
}

# With more details
list_containers_with_details() {
    sudo docker ps -a --filter "label=com.docker.compose.project=aurorah" --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"
}

# Real-time stats for all containers in the project
show_real_time_stats() {
    sudo docker stats $(sudo docker ps --filter "label=com.docker.compose.project=aurorah" -q)
}

# View logs for all containers in the project
show_logs() {
    if [ $# -eq 0 ]; then
        set -- -n 10
    fi
    sudo docker compose -p aurorah logs -f "$@"
}

show_help() {
    cat <<EOF

╔════════════════════════════════════════════════════════════════════════════╗
║                         DOCKER CLI HELPER SCRIPT                           ║
╚════════════════════════════════════════════════════════════════════════════╝

USAGE:
  $0 <command> [args...]

COMMANDS:
  ps    - list running containers for compose project 'aurorah'
  psd   - list all containers (incl. stopped) with status/ports table
  stats - show real-time CPU/mem/net IO stats for running 'aurorah' containers
  logs  - follow logs for 'aurorah' services (docker compose logs -f)

ARGS:
  optional options passed to 'docker compose logs' (default: -n 10).
  Note: if you need multiple options, wrap them in quotes, e.g. "--tail 50 --since 1h"

EXAMPLES:
  $ $0 ps
  $ $0 psd
  $ $0 stats
  $ $0 logs -n 10
  $ $0 logs --tail 50 --since 1h

EOF
}

# Handle command line arguments
case "$COMMAND" in
    ps)
        list_containers
        ;;
    psd)
        list_containers_with_details
        ;;
    stats)
        show_real_time_stats
        ;;
    logs)
        show_logs "$@"
        ;;
    help|--help|-h)
        show_help
        ;;
    *)
        show_help
        ;;
esac
