#!/bin/bash
# Script to prepare the project for deployment

echo "Starting deployment preparation..."

# Run the cleanup script first
bash clean-for-deployment.sh

# Build the frontend
echo "Building frontend..."
npm run build

# Check the size after cleanup and build
echo "Current project size:"
du -sh .

echo "Deployment preparation complete!"
echo "To deploy, set the Start Command to: 'node deployment.js'"
echo "Make sure all required environment variables are set in the deployment settings."