#!/bin/bash
set -e

echo "Installing system dependencies..."
sudo apt-get update
sudo apt-get install -y wget ca-certificates redis-tools gnupg

echo "Setting up PostgreSQL repository..."
sudo mkdir -p /etc/apt/keyrings
wget --quiet -O - https://www.postgresql.org/media/keys/ACCC4CF8.asc | sudo gpg --dearmor -o /etc/apt/keyrings/pgdg.gpg
sudo sh -c 'echo "deb [signed-by=/etc/apt/keyrings/pgdg.gpg] http://apt.postgresql.org/pub/repos/apt $(lsb_release -cs)-pgdg main" > /etc/apt/sources.list.d/pgdg.list'

echo "Installing PostgreSQL client..."
sudo apt-get update
sudo apt-get install -y postgresql-client-18

echo "Installing Python packages..."
pip install --upgrade pip
pip install jupyterlab
pip install -r requirements.txt

echo "Setup complete!"