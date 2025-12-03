#!/bin/bash

# Setup script for Aurorah API Server

USE_VENV=false

# Check Python version
PYTHON_VERSION=$(python3 --version 2>&1 | grep -Po '(?<=Python )(.+)')
REQUIRED_VERSION="3.13"

set -e

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --venv)
            USE_VENV=true
            shift
            ;;
        *)
            echo "Unknown option: $1"
            echo "Usage: $0 [--venv (default: false)]"
            exit 1
            ;;
    esac
done

echo "Setting up Aurorah API Server..."

if [[ "$(printf '%s\n' "$REQUIRED_VERSION" "$PYTHON_VERSION" | sort -V | head -n1)" != "$REQUIRED_VERSION" ]]; then 
    echo "Python $REQUIRED_VERSION or higher is required. Current version: $PYTHON_VERSION"
    exit 1
fi

echo "Python version: $PYTHON_VERSION"

if [ "$USE_VENV" = true ]; then
    echo "Using virtual environment..."
    # Create virtual environment
    if [ ! -d ".venv" ]; then
        echo "Creating virtual environment..."
        python3 -m venv .venv
    fi

    # Activate virtual environment
    echo "Activating virtual environment..."
    source .venv/bin/activate
fi

# Upgrade pip
echo "Upgrading pip..."
pip install --upgrade pip

# Install dependencies
echo "Installing dependencies..."
pip install -r requirements.txt

# Create .env.local.sh file for local development if it doesn't exist
if [ ! -f ".env.local.sh" ]; then
    echo "Creating .env.local.sh file from .env.local.sh.example..."
    cp .env.local.sh.example .env.local.sh
    chmod +x .env.local.sh
    echo "Please edit .env.local.sh file with your local development configuration and source it:"
    echo "  $ source .env.local.sh"
else
    # Source .env.local.sh file for local development
    source .env.local.sh
fi

echo "Setup complete!"
echo ""
echo "Next steps:"
echo "1. Edit .env.local.sh file with your local development configuration and source it:"
echo "  $ source .env.local.sh"
echo "2. Start PostgreSQL and Redis"
echo "3. Run: $ ./scripts/start.sh"
