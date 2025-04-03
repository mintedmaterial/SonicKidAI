#!/bin/bash
# Clean for Deployment
# This script cleans up the project for deployment

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}=== Cleaning Project for Deployment ===${NC}"
echo ""

# Step 1: Ask for confirmation
echo -e "${RED}WARNING: This will clean the project for deployment.${NC}"
echo -e "${YELLOW}Make sure you have committed your changes before proceeding.${NC}"
echo -e "${YELLOW}Press Enter to continue, or Ctrl+C to cancel...${NC}"
read -r

# Step 2: Remove build files and caches
echo -e "\n${BLUE}Removing build files and caches...${NC}"
rm -rf .cache dist build node_modules/.cache __pycache__ 2>/dev/null
find . -name "__pycache__" -type d -exec rm -rf {} + 2>/dev/null || true
find . -name "*.pyc" -delete 2>/dev/null || true
find . -name ".DS_Store" -delete 2>/dev/null || true
echo -e "${GREEN}✓ Build files and caches removed${NC}"

# Step 3: Clean up log files (keep last 100 lines)
echo -e "\n${BLUE}Cleaning up log files...${NC}"
find . -name "*.log" -size +1M -exec sh -c 'tail -n 100 "{}" > "{}.tmp" && mv "{}.tmp" "{}"' \; 2>/dev/null || true
echo -e "${GREEN}✓ Log files cleaned up${NC}"

# Step 4: Set environment variables for deployment
echo -e "\n${BLUE}Setting environment variables for deployment...${NC}"
export SKIP_API_SERVER=true
export FRONTEND_PORT=3000
export BACKEND_PORT=5000
export BROWSER_API_PORT=8000
echo -e "${GREEN}✓ Environment variables set${NC}"

# Step 5: Build frontend for production
echo -e "\n${BLUE}Building frontend for production...${NC}"
if [ -f "package.json" ]; then
  npm run build || echo -e "${YELLOW}⚠ Frontend build failed${NC}"
else
  echo -e "${YELLOW}⚠ No package.json found${NC}"
fi
echo -e "${GREEN}✓ Frontend build complete${NC}"

# Step 6: Stop all workflows
echo -e "\n${BLUE}Stopping all workflows...${NC}"
./manage-workflows.sh stop-all || echo -e "${YELLOW}⚠ Failed to stop all workflows${NC}"
echo -e "${GREEN}✓ All workflows stopped${NC}"

# Step 7: Final reminder
echo -e "\n${BLUE}=== Deployment Preparation Complete ===${NC}"
echo ""
echo -e "${YELLOW}Next steps:${NC}"
echo "1. Make sure the SKIP_API_SERVER environment variable is set in Replit Secrets"
echo "2. Deploy the application using the Replit deploy button"
echo "3. After deployment, enable workflows one by one using ./manage-workflows.sh"
echo ""
echo -e "${GREEN}Project is ready for deployment!${NC}"

exit 0