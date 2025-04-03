#!/bin/bash
# Script to manage workflows for deployment

# Usage: bash manage-workflows.sh [start|stop|status]

ACTION=$1

if [ -z "$ACTION" ]; then
  echo "Usage: bash manage-workflows.sh [start|stop|status]"
  echo "  start  - Start only the main application workflow"
  echo "  stop   - Stop all workflows"
  echo "  status - Show status of all workflows"
  exit 1
fi

# Function to stop all workflows
stop_all_workflows() {
  echo "Stopping all workflows..."
  pkill -f "npm run" || true
  pkill -f "python" || true
  pkill -f "node " || true
  
  # Kill any specific workflow processes if needed
  # Add pkill commands for specific processes here
  
  echo "All workflows stopped."
}

# Function to start only the main application
start_main_workflow() {
  echo "Starting only the main application workflow..."
  
  # First ensure all other processes are stopped
  stop_all_workflows
  
  # Start only the deployment.js file
  echo "Starting deployment server..."
  NODE_ENV=production node deployment.js &
  
  echo "Main application started. Process ID: $!"
}

# Function to show status of workflows
show_workflow_status() {
  echo "Current workflows status:"
  echo "------------------------"
  
  # Check for Node.js processes
  echo "Node.js processes:"
  ps aux | grep "node" | grep -v grep
  
  # Check for Python processes
  echo "Python processes:"
  ps aux | grep "python" | grep -v grep
  
  echo "------------------------"
}

# Main execution logic
case "$ACTION" in
  "start")
    start_main_workflow
    ;;
  "stop")
    stop_all_workflows
    ;;
  "status")
    show_workflow_status
    ;;
  *)
    echo "Unknown action: $ACTION"
    echo "Usage: bash manage-workflows.sh [start|stop|status]"
    exit 1
    ;;
esac

exit 0