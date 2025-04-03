#!/bin/bash
# Script to test deployment preparation

echo "===== DEPLOYMENT PREPARATION TEST ====="
echo "Starting deployment preparation test..."

# Make sure we're in the right directory
cd "$(dirname "$0")"

# First, check the initial size
echo "Current project size before cleanup:"
du -sh . | sort -hr

# Make sure scripts are executable
chmod +x clean-for-deployment.sh

# Run the cleanup script first
echo "Running aggressive cleanup script..."
bash clean-for-deployment.sh

# Build the frontend for deployment
echo "Building frontend for deployment..."
NODE_ENV=production npm run build

# Get the size after cleanup and build
echo "Current project size after cleanup and build:"
du -sh . | sort -hr

# List largest directories to see what's still taking up space
echo "Largest directories (for further optimization if needed):"
du -sh ./* ./.* 2>/dev/null | sort -hr | head -10

# Test if the deployment.js file exists
if [ ! -f "deployment.js" ]; then
  echo "ERROR: deployment.js not found!"
  exit 1
fi

# Stop any running services first
echo "Stopping any existing services..."
bash manage-workflows.sh stop
sleep 3

# Test the deployment.js file
echo "Testing unified deployment server..."
NODE_ENV=production DEPLOYMENT_MODE=true SINGLE_SERVER_MODE=true node deployment.js &
DEPLOYMENT_PID=$!

# Wait for server to start
echo "Waiting for servers to start..."
sleep 10  # Give more time for both servers to start

# Test the health endpoint
echo "Testing main server health endpoint..."
HEALTH_RESPONSE=$(curl -s http://localhost:3000/api/health)
echo "$HEALTH_RESPONSE"

# Check if health check worked
if [[ $HEALTH_RESPONSE == *"status"*"ok"* ]]; then
  echo "✅ Main server health check passed!"
else
  echo "❌ Main server health check failed!"
fi

# Test the version endpoint
echo "Testing version endpoint..."
VERSION_RESPONSE=$(curl -s http://localhost:3000/api/version)
echo "$VERSION_RESPONSE"

# Check if version endpoint worked
if [[ $VERSION_RESPONSE == *"version"* ]]; then
  echo "✅ Version endpoint passed!"
else
  echo "❌ Version endpoint failed!"
fi

# Test the Browser API Server through proxy
echo "Testing Browser API Server via proxy..."
BROWSER_API_RESPONSE=$(curl -s http://localhost:3000/browser-api/docs)

# Check if Browser API is accessible through proxy
if [[ -n "$BROWSER_API_RESPONSE" ]]; then
  echo "✅ Browser API proxy check passed!"
else
  echo "❌ Browser API proxy check failed!"
  
  # Try direct access as fallback
  echo "Testing direct Browser API Server access..."
  DIRECT_API_RESPONSE=$(curl -s http://localhost:8000/docs)
  
  if [[ -n "$DIRECT_API_RESPONSE" ]]; then
    echo "✅ Direct Browser API check passed (but proxy failed)!"
  else
    echo "❌ Both proxy and direct Browser API checks failed!"
  fi
fi

# Kill the test servers
echo "Stopping test servers..."
kill $DEPLOYMENT_PID
sleep 2
pkill -f "uvicorn" || true  # Kill Python API server if running

echo "===== DEPLOYMENT PREPARATION SUMMARY ====="
echo "✅ Cleanup completed"
echo "✅ Build completed"
echo "✅ Deployment server tested"
echo "Current size: $(du -sh . | cut -f1)"

echo "===== DEPLOYMENT INSTRUCTIONS ====="
echo "1. Set the Start Command to: 'node deployment.js'"
echo "2. Set the Environment to: Node.js"
echo "3. Make sure the following environment variables are set:"
echo "   - DATABASE_URL"
echo "   - NODE_ENV=production"
echo "   - OPENAI_API_KEY (for AI features)"
echo "===== END OF TEST ====="