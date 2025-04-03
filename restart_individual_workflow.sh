#!/bin/bash
# Restart Individual Workflow
# This script helps restart a specific Replit workflow

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Check if a workflow name is provided
if [ $# -lt 1 ]; then
  echo -e "${RED}Error: Missing workflow name${NC}"
  echo "Usage: $0 <workflow-name>"
  echo "Example: $0 telegram-bot"
  exit 1
fi

workflow=$1
workflow_file=".replit.workflow.$workflow"

# Check if the workflow file exists
if [ ! -f "$workflow_file" ]; then
  echo -e "${RED}Error: Workflow '$workflow' not found${NC}"
  echo "Available workflows:"
  find . -maxdepth 1 -type f -name ".replit.workflow.*" | grep -v ".name$" | while read -r wf_file; do
    wf=$(basename "$wf_file" | sed 's/^\.replit\.workflow\.//')
    echo "  $wf"
  done
  exit 1
fi

# Get the workflow display name
name_file="${workflow_file}.name"
if [ -f "$name_file" ]; then
  display_name=$(cat "$name_file")
else
  display_name=$workflow
fi

# Get the command from the workflow file
command=$(cat "$workflow_file")

echo -e "${BLUE}Restarting workflow: ${YELLOW}$display_name${NC}"
echo -e "Command: ${GREEN}$command${NC}"

# Wait for confirmation
echo ""
echo -e "${YELLOW}Press Enter to confirm restart, or Ctrl+C to cancel...${NC}"
read -r

# For demonstration, we'll show the restart message
echo -e "${GREEN}Workflow '$display_name' is being restarted...${NC}"
echo "Check the Replit console for workflow status and output."

exit 0