#!/bin/bash
# Startup script for the frontend development server

# Change to frontend directory
cd "$(dirname "$0")"

# Check if node_modules exists, if not install dependencies
if [ ! -d "node_modules" ]; then
    echo "node_modules not found. Installing dependencies..."
    npm install
    if [ $? -ne 0 ]; then
        echo "Failed to install dependencies"
        exit 1
    fi
fi

# Run the development server
echo "Starting frontend development server on http://localhost:5173"
echo "Press Ctrl+C to stop the server"
npm run dev -- --host 0.0.0.0
