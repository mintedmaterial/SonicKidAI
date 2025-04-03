#!/bin/bash

# Script to start Python services with correct environment variables for API communication

# Default values
FRONTEND_PORT=3000
BACKEND_PORT=5000
BROWSER_API_PORT=8000

# Override with environment variables if they exist
if [ ! -z "$REPLIT_FRONTEND_PORT" ]; then
  FRONTEND_PORT=$REPLIT_FRONTEND_PORT
fi

if [ ! -z "$REPLIT_BACKEND_PORT" ]; then
  BACKEND_PORT=$REPLIT_BACKEND_PORT
fi

if [ ! -z "$REPLIT_BROWSER_API_PORT" ]; then
  BROWSER_API_PORT=$REPLIT_BROWSER_API_PORT
fi

# Display configuration
echo "Starting Python service with these environment variables:"
echo "- FRONTEND_PORT: $FRONTEND_PORT"
echo "- BACKEND_PORT: $BACKEND_PORT"
echo "- BROWSER_API_PORT: $BROWSER_API_PORT"
echo "- API_BASE_URL: http://localhost:$FRONTEND_PORT"

# Set environment variables for the Python process
export FRONTEND_PORT=$FRONTEND_PORT
export BACKEND_PORT=$BACKEND_PORT
export BROWSER_API_PORT=$BROWSER_API_PORT
export API_BASE_URL="http://localhost:$FRONTEND_PORT"

# Check if we have a script name argument
if [ $# -eq 0 ]; then
  echo "Error: No Python script provided"
  echo "Usage: $0 <python_script.py> [arguments]"
  exit 1
fi

# Run the Python script with any additional arguments
python "$@"