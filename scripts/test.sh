#!/bin/bash

# Test script for Aurorah API Server

USE_RUFF=true
USE_PYRIGHT=true

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
        --pyright)
            USE_PYRIGHT=true
            shift
            ;;
        --mypy)
            USE_PYRIGHT=false
            shift
            ;;
        *)
            echo "Unknown option: $1"
            echo "Usage: $0 [--ruff true|false|1|0 (default: true)] [--black (alternative: false)] [--pyright (default: true)] [--mypy (alternative: false)]"
            exit 1
            ;;
    esac
done

echo "Running tests for Aurorah API Server..."

# Activate virtual environment if it exists
if [ -d ".venv" ]; then
    echo "Activating virtual environment..."
    source .venv/bin/activate
fi

if [ "$USE_RUFF" = true ]; then
    # Check linting issues with ruff
    echo "Checking lint issues with Ruff..."
    ruff check app/ tests/

    # Check formatting with ruff
    echo "Checking code formatting with Ruff..."
    ruff format --check app/ tests/
else
    # Run linting with flake8
    # - flake8: Slower (written in Python)
    # - ruff: 10-100x faster (written in Rust). funtionality of: Linter + formatter + import sorter (replaces flake8, black, isort and more)
    echo "Running linting with flake8..."
    flake8 app/ --max-line-length=100 --ignore=E203,E266,E501,W503

    # Run black check for code formatting
    echo "Checking code formatting with Black..."
    black --check app/

    # Run isort check for import sorting
    echo "Checking import sorting with isort..."
    isort --check-only app/
fi

# Run type checking
# - mypy: Slower (written in Python)
# - Cursor Pyright: Faster (written in TypeScript), works with Cursor (built-in extension: .vscode/settings.json)
if [ "$USE_PYRIGHT" = true ]; then
    echo "Running type checking with Pyright..."
    pyright app/
else
    echo "Running type checking with mypy..."
    mypy app/ --ignore-missing-imports || true
fi

# Run tests
echo "Running pytest..."
pytest --cov=app --cov-report=term-missing --cov-report=html

echo "All tests passed!"
