#!/bin/bash

# Code formatting script for Aurorah API Server

USE_RUFF=true

set -e

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --ruff)
            if [[ "$2" == "true" || "$2" == "1" ]]; then
                USE_RUFF=true
            elif [[ "$2" == "false" || "$2" == "0" ]]; then
                USE_RUFF=false
            else
                echo "Error: --ruff requires true/false or 1/0"
                exit 1
            fi
            shift 2
            ;;
        --black)
            USE_RUFF=false
            shift
            ;;
        *)
            echo "Unknown option: $1"
            echo "Usage: $0 [--ruff true|false|1|0 (default: true)] [--black]"
            exit 1
            ;;
    esac
done

echo "Formatting code..."

# Activate virtual environment if it exists
if [ -d ".venv" ]; then
    echo "Activating virtual environment..."
    source .venv/bin/activate
fi

if [ "$USE_RUFF" = true ]; then
    # Fix linting issues and sort imports with ruff
    echo "Fixing lint issues and sorting imports with Ruff..."
    ruff check --fix app/ tests/

    # Format with ruff
    echo "Formatting with Ruff..."
    ruff format app/ tests/
else
    # Format with black
    echo "Formatting with Black..."
    black app/ tests/

    # Sort imports with isort
    echo "Sorting imports with isort..."
    isort app/ tests/
fi

echo "Code formatting complete!"
