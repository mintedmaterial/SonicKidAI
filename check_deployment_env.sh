#!/bin/bash

# Script to check and set required environment variables for deployment
# Usage: ./check_deployment_env.sh

# Terminal colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Core deployment variables
CORE_VARS=(
  "NODE_ENV"
  "DEPLOYMENT_MODE"
  "SINGLE_SERVER_MODE"
  "DATABASE_URL"
)

# Port configuration (optional with defaults)
PORT_VARS=(
  "PORT"           # Main port used by Replit for the application
  "FRONTEND_PORT"  # Frontend dashboard (default: 3000)
  "BACKEND_PORT"   # Backend API services (default: 5000)
  "BROWSER_API_PORT" # Browser API service (default: 8000)
)

# Workflow-specific variables
WORKFLOW_VARS=(
  # Telegram Bot
  "TELEGRAM_BOT_TOKEN"
  "TELEGRAM_ADMIN_USER_ID"
  
  # Discord Bot
  "DISCORD_BOT_TOKEN"
  "DISCORD_CLIENT_ID"
  
  # Twitter
  "TWITTER_API_KEY"
  "TWITTER_API_SECRET"
  "TWITTER_ACCESS_TOKEN"
  "TWITTER_ACCESS_SECRET"
  
  # AI Services
  "OPENAI_API_KEY"
  "ANTHROPIC_API_KEY"
  
  # Blockchain
  "ETHEREUM_RPC_URL"
  "SONIC_RPC_URL"
)

# Function to check if a variable is set
check_var() {
  local var_name=$1
  if [ -n "${!var_name}" ]; then
    echo -e "${GREEN}✓${NC} $var_name is set"
    return 0
  else
    echo -e "${RED}✗${NC} $var_name is NOT set"
    return 1
  fi
}

# Function to print a section header
print_header() {
  echo -e "\n${BLUE}=== $1 ===${NC}"
}

# Main function
main() {
  echo -e "${BLUE}=============================================${NC}"
  echo -e "${BLUE}    Deployment Environment Variable Check    ${NC}"
  echo -e "${BLUE}=============================================${NC}\n"
  
  # Check core variables
  print_header "Core Deployment Variables"
  missing_core=0
  for var in "${CORE_VARS[@]}"; do
    check_var "$var" || ((missing_core++))
  done
  
  # Check port configuration
  print_header "Port Configuration Variables"
  missing_port=0
  for var in "${PORT_VARS[@]}"; do
    if check_var "$var"; then
      # Variable is set
      true
    else
      # Variable not set, but these all have defaults
      echo -e "${YELLOW}  (Default value will be used)${NC}"
      ((missing_port++))
    fi
  done
  
  # Check workflow variables
  print_header "Workflow-Specific Variables"
  missing_workflow=0
  for var in "${WORKFLOW_VARS[@]}"; do
    check_var "$var" || ((missing_workflow++))
  done
  
  # Summary
  print_header "Summary"
  if [ $missing_core -eq 0 ]; then
    echo -e "${GREEN}✓ All core deployment variables are set${NC}"
  else
    echo -e "${RED}✗ Missing $missing_core core deployment variables${NC}"
  fi
  
  if [ $missing_port -eq 0 ]; then
    echo -e "${GREEN}✓ All port configuration variables are set${NC}"
  else
    echo -e "${YELLOW}! Missing $missing_port port configuration variables${NC}"
    echo -e "${YELLOW}  This is OK - default values will be used for these:${NC}"
    echo -e "${YELLOW}  - FRONTEND_PORT=3000${NC}"
    echo -e "${YELLOW}  - BACKEND_PORT=5000${NC}"
    echo -e "${YELLOW}  - BROWSER_API_PORT=8000${NC}"
  fi
  
  if [ $missing_workflow -eq 0 ]; then
    echo -e "${GREEN}✓ All workflow-specific variables are set${NC}"
  else
    echo -e "${YELLOW}! Missing $missing_workflow workflow-specific variables${NC}"
    echo -e "${YELLOW}  This may be ok if you're not using those workflows initially${NC}"
  fi
  
  # Deployment readiness
  print_header "Deployment Readiness"
  if [ $missing_core -eq 0 ]; then
    echo -e "${GREEN}✓ READY FOR CORE DEPLOYMENT${NC}"
    echo -e "  You can proceed with Stage 1 deployment (frontend only)"
    
    if [ $missing_workflow -eq 0 ]; then
      echo -e "${GREEN}✓ READY FOR FULL DEPLOYMENT${NC}"
      echo -e "  You can proceed with all stages (1-3) of deployment"
    else
      echo -e "${YELLOW}! PARTIALLY READY FOR FULL DEPLOYMENT${NC}"
      echo -e "  Set the missing workflow variables before enabling those specific workflows"
    fi
  else
    echo -e "${RED}✗ NOT READY FOR DEPLOYMENT${NC}"
    echo -e "  Set the missing core variables before proceeding with deployment"
  fi
  
  # Next steps
  print_header "Next Steps"
  if [ $missing_core -gt 0 ] || [ $missing_workflow -gt 0 ]; then
    echo "1. Add missing environment variables to Replit Secrets tab"
    echo "2. Run this script again to verify all variables are set"
    echo "3. Proceed with deployment once core variables are set"
  else
    echo "1. Proceed with deployment using the commands in DEPLOYMENT_STEPS.md"
    echo "2. Start with Stage 1 (frontend only) deployment"
    echo "3. Add additional workflows one by one after frontend is deployed"
  fi
}

# Run the main function
main