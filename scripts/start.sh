#!/bin/bash

# Startup script for Aurorah API Server

NUM_OF_CPUS=$(nproc --all)
NUM_OF_WORKERS=$((NUM_OF_CPUS * 2 + 1))

set -e

echo "Starting Aurorah API Server..."

# Activate virtual environment if it exists
if [ -d ".venv" ]; then
    echo "Activating virtual environment..."
    source .venv/bin/activate
fi

# Start the server
echo "Starting FastAPI server..."
uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers $NUM_OF_WORKERS --reload
