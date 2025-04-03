#!/bin/bash
# Workflow Management Script
# This script helps manage Replit workflows

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Print usage information
function show_usage {
  echo "Usage: $0 [command]"
  echo ""
  echo "Commands:"
  echo "  status             - Show status of all workflows"
  echo "  start-all          - Start all workflows"
  echo "  stop-all           - Stop all workflows"
  echo "  restart-all        - Restart all workflows"
  echo "  start [workflow]   - Start a specific workflow"
  echo "  stop [workflow]    - Stop a specific workflow"
  echo "  restart [workflow] - Restart a specific workflow"
  echo "  list               - List all available workflows"
  echo "  help               - Show this help message"
  echo ""
  echo "Examples:"
  echo "  $0 status"
  echo "  $0 start telegram_bot"
  echo "  $0 stop-all"
  exit 1
}

# List all workflows
function list_workflows {
  echo -e "${BLUE}Available workflows:${NC}"
  find . -maxdepth 1 -type f -name ".replit.workflow.*" | grep -v ".name$" | while read -r wf_file; do
    wf=$(basename "$wf_file" | sed 's/^\.replit\.workflow\.//')
    name_file="${wf_file}.name"
    if [ -f "$name_file" ]; then
      display_name=$(cat "$name_file")
    else
      display_name=$wf
    fi
    echo -e "  ${GREEN}$wf${NC} - $display_name"
  done
}

# Get workflow display name
function get_workflow_name {
  local workflow=$1
  local name_file=".replit.workflow.${workflow}.name"
  
  if [ -f "$name_file" ]; then
    cat "$name_file"
  else
    echo "$workflow"
  fi
}

# Check if workflow exists
function check_workflow {
  local workflow=$1
  local workflow_file=".replit.workflow.$workflow"
  
  if [ ! -f "$workflow_file" ]; then
    echo -e "${RED}Error: Workflow '$workflow' not found${NC}"
    echo "Available workflows:"
    list_workflows
    exit 1
  fi
}

# Show status of all workflows
function show_status {
  echo -e "${BLUE}Workflow Status:${NC}"
  echo -e "${YELLOW}Status is simulated and may not reflect actual state${NC}"
  echo ""
  
  # Get list of all workflows
  find . -maxdepth 1 -type f -name ".replit.workflow.*" | grep -v ".name$" | while read -r wf_file; do
    wf=$(basename "$wf_file" | sed 's/^\.replit\.workflow\.//')
    display_name=$(get_workflow_name "$wf")
    
    # Simulate status check (would need integration with Replit API for actual status)
    # For now, randomly choose a status
    status_num=$((RANDOM % 3))
    case $status_num in
      0) status="${GREEN}Running${NC}" ;;
      1) status="${RED}Stopped${NC}" ;;
      2) status="${YELLOW}Error${NC}" ;;
    esac
    
    echo -e "  ${GREEN}$display_name${NC}: $status"
  done
}

# Start all workflows
function start_all {
  echo -e "${BLUE}Starting all workflows...${NC}"
  echo -e "${YELLOW}This action is simulated${NC}"
  echo ""
  
  find . -maxdepth 1 -type f -name ".replit.workflow.*" | grep -v ".name$" | while read -r wf_file; do
    wf=$(basename "$wf_file" | sed 's/^\.replit\.workflow\.//')
    display_name=$(get_workflow_name "$wf")
    echo -e "  Starting ${GREEN}$display_name${NC}..."
    # Simulate starting workflow
    sleep 0.5
  done
  
  echo -e "\n${GREEN}All workflows started${NC}"
}

# Stop all workflows
function stop_all {
  echo -e "${BLUE}Stopping all workflows...${NC}"
  echo -e "${YELLOW}This action is simulated${NC}"
  echo ""
  
  find . -maxdepth 1 -type f -name ".replit.workflow.*" | grep -v ".name$" | while read -r wf_file; do
    wf=$(basename "$wf_file" | sed 's/^\.replit\.workflow\.//')
    display_name=$(get_workflow_name "$wf")
    echo -e "  Stopping ${GREEN}$display_name${NC}..."
    # Simulate stopping workflow
    sleep 0.5
  done
  
  echo -e "\n${GREEN}All workflows stopped${NC}"
}

# Restart all workflows
function restart_all {
  echo -e "${BLUE}Restarting all workflows...${NC}"
  echo -e "${YELLOW}This action is simulated${NC}"
  echo ""
  
  stop_all
  start_all
}

# Start a specific workflow
function start_workflow {
  local workflow=$1
  check_workflow "$workflow"
  
  display_name=$(get_workflow_name "$workflow")
  echo -e "${BLUE}Starting workflow: ${GREEN}$display_name${NC}"
  echo -e "${YELLOW}This action is simulated${NC}"
  
  # Simulate starting workflow
  sleep 1
  echo -e "${GREEN}Workflow '$display_name' started${NC}"
}

# Stop a specific workflow
function stop_workflow {
  local workflow=$1
  check_workflow "$workflow"
  
  display_name=$(get_workflow_name "$workflow")
  echo -e "${BLUE}Stopping workflow: ${GREEN}$display_name${NC}"
  echo -e "${YELLOW}This action is simulated${NC}"
  
  # Simulate stopping workflow
  sleep 1
  echo -e "${GREEN}Workflow '$display_name' stopped${NC}"
}

# Restart a specific workflow
function restart_workflow {
  local workflow=$1
  check_workflow "$workflow"
  
  display_name=$(get_workflow_name "$workflow")
  echo -e "${BLUE}Restarting workflow: ${GREEN}$display_name${NC}"
  echo -e "${YELLOW}This action is simulated${NC}"
  
  # Simulate restarting workflow
  sleep 1
  echo -e "${GREEN}Workflow '$display_name' restarted${NC}"
}

# Main logic
if [ $# -lt 1 ]; then
  show_usage
fi

command=$1

case $command in
  "status")
    show_status
    ;;
  "start-all")
    start_all
    ;;
  "stop-all")
    stop_all
    ;;
  "restart-all")
    restart_all
    ;;
  "start")
    if [ $# -lt 2 ]; then
      echo -e "${RED}Error: Missing workflow name${NC}"
      show_usage
    fi
    start_workflow "$2"
    ;;
  "stop")
    if [ $# -lt 2 ]; then
      echo -e "${RED}Error: Missing workflow name${NC}"
      show_usage
    fi
    stop_workflow "$2"
    ;;
  "restart")
    if [ $# -lt 2 ]; then
      echo -e "${RED}Error: Missing workflow name${NC}"
      show_usage
    fi
    restart_workflow "$2"
    ;;
  "list")
    list_workflows
    ;;
  "help")
    show_usage
    ;;
  *)
    echo -e "${RED}Error: Unknown command '$command'${NC}"
    show_usage
    ;;
esac

exit 0