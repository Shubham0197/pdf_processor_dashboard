#!/bin/bash
set -e

# Create a virtual environment if it doesn't exist
if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python -m venv venv
fi

# Activate virtual environment
source venv/bin/activate

# Install dependencies
echo "Installing dependencies..."
pip install -r requirements.txt

# Set up environment variables if .env file exists
if [ -f .env ]; then
    echo "Loading environment variables from .env file..."
    export $(grep -v '^#' .env | xargs)
fi

# Run the application
echo "Starting the application..."
uvicorn app.main:app --host ${API_HOST:-0.0.0.0} --port ${API_PORT:-8000} --reload
