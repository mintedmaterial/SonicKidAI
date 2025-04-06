#!/bin/bash

# Make script exit on first error
set -e

echo "🧹 Cleaning up repository for Vercel deployment..."

# Remove Replit specific files
echo "Removing Replit files..."
find . -name ".replit*" -type f -delete
find . -name "replit.nix" -type f -delete
rm -f .upm* 2>/dev/null || true

# Remove old deployment files
echo "Removing old deployment files..."
rm -f deployment.js DEPLOYMENT_GUIDE.md DEPLOYMENT_STEPS.md REPLIT_DEPLOYMENT_GUIDE.md STAGED_DEPLOYMENT_GUIDE.md PORT_CONFIGURATION.md 2>/dev/null || true

# Remove test files
echo "Removing test files..."
find . -name "*.test.*" -type f -delete
find . -name "*.spec.*" -type f -delete
find . -name "__tests__" -type d -exec rm -rf {} + 2>/dev/null || true

# Remove the telegram-mini-app directory since it's now integrated into dashboard
echo "Removing old telegram-mini-app directory..."
rm -rf apps/telegram-mini-app 2>/dev/null || true

# Clean build artifacts
echo "Cleaning build artifacts..."
rm -rf dist build .turbo .cache node_modules 2>/dev/null || true
find . -name "node_modules" -type d -exec rm -rf {} + 2>/dev/null || true

# Install dependencies
echo "Installing dependencies..."
pnpm install

# Build the project to test configuration
echo "Building project..."
pnpm build

echo "✅ Repository cleaned and ready for Vercel deployment!"
echo ""
echo "Next steps:"
echo "1. Create a new repository on GitHub"
echo "2. Push this cleaned codebase to the new repository"
echo "3. Import the repository in Vercel"
echo "4. Configure environment variables in Vercel dashboard"
echo "5. Deploy!"
