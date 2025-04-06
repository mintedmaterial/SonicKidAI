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

# Remove test files from dashboard app only
echo "Removing test files from dashboard app..."
find apps/dashboard -name "*.test.*" -type f -delete
find apps/dashboard -name "*.spec.*" -type f -delete
find apps/dashboard -name "__tests__" -type d -exec rm -rf {} + 2>/dev/null || true

# Remove unnecessary apps and packages
echo "Removing unnecessary directories..."
rm -rf apps/telegram-mini-app 2>/dev/null || true
rm -rf packages/telegram-bot 2>/dev/null || true
rm -rf packages/discord-bot 2>/dev/null || true
rm -rf packages/twitter-client 2>/dev/null || true

# Clean build artifacts
echo "Cleaning build artifacts..."
rm -rf apps/dashboard/dist apps/dashboard/.turbo apps/dashboard/.cache apps/dashboard/node_modules 2>/dev/null || true
rm -rf node_modules 2>/dev/null || true

# Install dependencies
echo "Installing dependencies..."
pnpm install --no-frozen-lockfile

# Build the dashboard app
echo "Building dashboard app..."
pnpm build

echo "✅ Repository cleaned and ready for Vercel deployment!"
echo ""
echo "Next steps:"
echo "1. Ensure all required environment variables are set in Vercel dashboard:"
echo "   - VITE_SUBGRAPH_ENDPOINT"
echo "   - VITE_THIRDWEB_CLIENT_ID"
echo "   - VITE_TELEGRAM_BOT_TOKEN"
echo "   - VITE_TELEGRAM_BOT_USERNAME"
echo "2. Deploy the project"
