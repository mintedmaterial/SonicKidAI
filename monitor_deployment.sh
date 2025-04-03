#!/bin/bash

# Deployment Monitoring Script
# Usage: ./monitor_deployment.sh

# Constants
MAIN_PORT=3000
API_PORT=8000
CHECK_INTERVAL=5 # seconds
LOG_FILE="deployment_monitor_$(date +%s).log"

# Terminal colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Initialize log file
echo "=== GOAT Platform Deployment Monitor Log ===" > "$LOG_FILE"
echo "Started at: $(date)" >> "$LOG_FILE"
echo "===============================================" >> "$LOG_FILE"

# Helper function for timestamps
timestamp() {
  date '+%Y-%m-%d %H:%M:%S'
}

# Check if a service is running on a specific port
check_service() {
  local port=$1
  local name=$2
  
  # Try to connect to the port
  if nc -z localhost "$port" 2>/dev/null; then
    echo -e "${GREEN}✅ $name is running on port $port${NC}"
    echo "[$(timestamp)] $name is running on port $port" >> "$LOG_FILE"
    return 0
  else
    echo -e "${RED}❌ $name is NOT running on port $port${NC}"
    echo "[$(timestamp)] $name is NOT running on port $port" >> "$LOG_FILE"
    return 1
  fi
}

# Check if a specific workflow is running
check_workflow() {
  local name=$1
  
  if ps aux | grep -i "$name" | grep -v grep > /dev/null; then
    echo -e "${GREEN}✅ Workflow \"$name\" is running${NC}"
    echo "[$(timestamp)] Workflow \"$name\" is running" >> "$LOG_FILE"
    return 0
  else
    echo -e "${YELLOW}⚠️ Workflow \"$name\" is not detected${NC}"
    echo "[$(timestamp)] Workflow \"$name\" is not detected" >> "$LOG_FILE"
    return 1
  fi
}

# Check the health endpoint of the main server
check_health_endpoint() {
  local response
  
  echo -e "${BLUE}🔍 Checking health endpoint...${NC}"
  
  # Try to connect to the health endpoint
  response=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:$MAIN_PORT/api/health)
  
  if [ "$response" = "200" ]; then
    echo -e "${GREEN}✅ Health endpoint is responding (HTTP 200)${NC}"
    echo "[$(timestamp)] Health endpoint is responding (HTTP 200)" >> "$LOG_FILE"
    return 0
  else
    echo -e "${RED}❌ Health endpoint returned HTTP $response${NC}"
    echo "[$(timestamp)] Health endpoint returned HTTP $response" >> "$LOG_FILE"
    return 1
  fi
}

# Check memory usage
check_memory_usage() {
  echo -e "${BLUE}🔍 Checking memory usage...${NC}"
  
  # Get memory information
  local total_mem=$(free -m | awk '/^Mem:/{print $2}')
  local used_mem=$(free -m | awk '/^Mem:/{print $3}')
  local usage_percent=$((used_mem * 100 / total_mem))
  
  echo -e "${CYAN}Memory: $used_mem MB / $total_mem MB ($usage_percent%)${NC}"
  echo "[$(timestamp)] Memory: $used_mem MB / $total_mem MB ($usage_percent%)" >> "$LOG_FILE"
  
  # Warn if memory usage is high
  if [ $usage_percent -gt 85 ]; then
    echo -e "${RED}⚠️ WARNING: High memory usage detected!${NC}"
    echo "[$(timestamp)] WARNING: High memory usage detected!" >> "$LOG_FILE"
    return 1
  fi
  
  return 0
}

# Main monitoring function
monitor() {
  echo -e "${CYAN}=============================================${NC}"
  echo -e "${CYAN}      GOAT Platform Deployment Monitor      ${NC}"
  echo -e "${CYAN}=============================================${NC}"
  echo -e "${CYAN}Time: $(timestamp)${NC}"
  echo -e "${CYAN}Log: $LOG_FILE${NC}"
  echo ""
  
  # Check the main server
  check_service $MAIN_PORT "Main Server"
  MAIN_STATUS=$?
  
  # Check the Browser API Server
  check_service $API_PORT "Browser API Server"
  API_STATUS=$?
  
  # Check important workflows
  echo ""
  echo -e "${CYAN}--- Workflow Status ---${NC}"
  check_workflow "Browser API Server"
  check_workflow "Telegram Bot"
  check_workflow "Discord Bot"
  
  # Check memory usage
  echo ""
  check_memory_usage
  
  # Check the health endpoint if the main server is running
  if [ $MAIN_STATUS -eq 0 ]; then
    echo ""
    check_health_endpoint
  fi
  
  # Print overall status
  echo ""
  echo -e "${CYAN}--- Overall Status ---${NC}"
  if [ $MAIN_STATUS -eq 0 ]; then
    echo -e "${GREEN}✅ Main deployment is running${NC}"
  else
    echo -e "${RED}❌ Main deployment is NOT running${NC}"
  fi
  
  echo ""
  echo -e "${CYAN}Next check in $CHECK_INTERVAL seconds...${NC}"
  echo "-----------------------------------------"
  echo ""
}

# Infinite monitoring loop
echo "Starting deployment monitor..."
echo "Press Ctrl+C to stop monitoring"
echo ""

while true; do
  monitor
  sleep $CHECK_INTERVAL
done