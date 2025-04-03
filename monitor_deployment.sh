#!/bin/bash
# Deployment Monitoring Script
# This script helps monitor the deployment status of the application

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
FRONTEND_PORT=${FRONTEND_PORT:-3000}
BACKEND_PORT=${BACKEND_PORT:-5000}
BROWSER_API_PORT=${BROWSER_API_PORT:-8000}
HOST="localhost"

# Print header
echo -e "${BLUE}===============================================${NC}"
echo -e "${BLUE}      Deployment Monitoring Dashboard         ${NC}"
echo -e "${BLUE}===============================================${NC}"
echo -e "${YELLOW}Date: $(date)${NC}"
echo ""

# Check if a service is running on a port
function check_service {
  local port=$1
  local name=$2
  
  # Check if the port is open
  if nc -z $HOST $port >/dev/null 2>&1; then
    echo -e "  ${GREEN}✓${NC} $name is running on port $port"
    return 0
  else
    echo -e "  ${RED}✗${NC} $name is not running on port $port"
    return 1
  fi
}

# Check environment variables
echo -e "${BLUE}Environment Variables:${NC}"
if [ -n "$SKIP_API_SERVER" ]; then
  echo -e "  SKIP_API_SERVER: ${YELLOW}$SKIP_API_SERVER${NC}"
else
  echo -e "  SKIP_API_SERVER: ${RED}Not set${NC}"
fi

echo -e "  FRONTEND_PORT: ${YELLOW}$FRONTEND_PORT${NC}"
echo -e "  BACKEND_PORT: ${YELLOW}$BACKEND_PORT${NC}"
echo -e "  BROWSER_API_PORT: ${YELLOW}$BROWSER_API_PORT${NC}"
echo ""

# Check services
echo -e "${BLUE}Service Status:${NC}"
check_service $FRONTEND_PORT "Frontend Server"
check_service $BACKEND_PORT "Backend API"

if [ "$SKIP_API_SERVER" != "true" ]; then
  check_service $BROWSER_API_PORT "Browser API Server"
else
  echo -e "  ${YELLOW}⚠${NC} Browser API Server is skipped (SKIP_API_SERVER=true)"
fi
echo ""

# Check workflow status
echo -e "${BLUE}Workflow Status:${NC}"
./manage-workflows.sh status | grep -v "Status is simulated"
echo ""

# Check database status
echo -e "${BLUE}Database Status:${NC}"
if [ -n "$DATABASE_URL" ]; then
  echo -e "  ${GREEN}✓${NC} Database URL is set"
  # Check if we can connect to the database
  if pg_isready -d "${DATABASE_URL}" >/dev/null 2>&1; then
    echo -e "  ${GREEN}✓${NC} Database connection successful"
  else
    echo -e "  ${RED}✗${NC} Cannot connect to database"
  fi
else
  echo -e "  ${RED}✗${NC} DATABASE_URL environment variable is not set"
fi
echo ""

# Check disk usage
echo -e "${BLUE}Disk Usage:${NC}"
df -h . | awk 'NR==2 {print "  Used: " $5 " of " $2 " (" $3 " used, " $4 " free)"}'
echo ""

# Check memory usage
echo -e "${BLUE}Memory Usage:${NC}"
free -h | awk 'NR==2 {print "  Used: " $3 " of " $2 " (" $3/$2*100 "% used)"}'
echo ""

# Display recent logs
echo -e "${BLUE}Recent Server Logs:${NC}"
if [ -f "logs/server.log" ]; then
  tail -n 5 logs/server.log | sed 's/^/  /'
else
  echo -e "  ${YELLOW}⚠${NC} No server logs found"
fi
echo ""

# Recommendations
echo -e "${BLUE}Deployment Recommendations:${NC}"
if [ "$SKIP_API_SERVER" != "true" ]; then
  echo -e "  ${YELLOW}⚠${NC} Consider setting SKIP_API_SERVER=true for initial deployment"
fi

# Get the count of running workflows
running_workflows=$(./manage-workflows.sh status | grep -c "Running")
if [ $running_workflows -gt 5 ]; then
  echo -e "  ${YELLOW}⚠${NC} Running too many workflows ($running_workflows). Consider reducing the number to avoid resource issues."
fi
echo ""

echo -e "${BLUE}===============================================${NC}"
echo -e "${GREEN}Monitoring complete. Use ./restart_individual_workflow.sh to restart specific workflows.${NC}"
echo -e "${BLUE}===============================================${NC}"

exit 0