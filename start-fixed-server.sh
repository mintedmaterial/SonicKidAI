#!/bin/bash

# Script to start the server with correct port configuration
echo "Starting server with fixed port configuration..."

# Set environment variables
export FRONTEND_PORT=3000
export BACKEND_PORT=5000
export BROWSER_API_PORT=8000
export ENABLE_SECONDARY_SERVER=false

# Print configuration
echo "Using the following configuration:"
echo "- FRONTEND_PORT: $FRONTEND_PORT"
echo "- BACKEND_PORT: $BACKEND_PORT"
echo "- BROWSER_API_PORT: $BROWSER_API_PORT"
echo "- ENABLE_SECONDARY_SERVER: $ENABLE_SECONDARY_SERVER"

# Run the dev server
npm run dev