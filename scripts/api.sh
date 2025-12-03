#!/bin/bash

#
# API script for Aurorah API Server
#
API_URL=${API_URL:-http://localhost:8000}
API_KEY=${API_KEY:-sk-test123}

#
# Example: 
#
# $ ./api.sh --url http://localhost:8000/api/v1/users/ --api-key sk-test123
#
# or:
#
# $ ./api.sh /api/v1/users
#
# The same way for using curl directly (without the script):
#
# $ curl -i http://localhost:8000/api/v1/users/ \
#   -H "Authorization: Bearer sk-test123"
#

set -e

# Parse command line arguments
PATH_ARG=""
while [[ $# -gt 0 ]]; do
    case $1 in
        --url)
            URL=$2
            shift 2
            ;;
        --api-key)
            API_KEY=$2
            shift 2
            ;;
        /*)
            PATH_ARG=$1
            shift
            ;;
        *)
            echo "Unknown option: $1"
            echo "Usage: $0 [--url http://localhost:8000] [--api-key sk-test123] or $0 /path"
            exit 1
            ;;
    esac
done

# Construct final URL
if [[ -n "$URL" ]]; then
    FINAL_URL=$URL
elif [[ -n "$PATH_ARG" ]]; then
    FINAL_URL="${API_URL}${PATH_ARG}"
else
    echo "Error: No URL or path provided"
    echo "Usage: $0 [--url http://localhost:8000/api/v1/users/] [--api-key sk-test123]"
    echo "   or: $0 /api/v1/users [--api-key sk-test123]"
    exit 1
fi

printf "Response for %s:\n" "$FINAL_URL"
printf '%.0s-' {1..120}; echo
curl -i "$FINAL_URL" \
  -H "Authorization: Bearer $API_KEY"
echo
printf '%.0s-' {1..120}; echo
