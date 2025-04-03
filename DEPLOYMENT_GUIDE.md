# GOAT Platform Deployment Guide

This guide provides step-by-step instructions for deploying the GOAT Platform to Replit.

## Pre-Deployment Checklist

Before deploying, make sure:

1. You are on the main branch with the latest code
2. All dependencies are correctly listed in package.json
3. Environment variables are set up correctly
4. You have run the cleanup script to reduce deployment size
5. All unnecessary workflows are disabled (use manage-workflows.sh)

## Size Optimization

The GOAT Platform includes AI models which can make the deployment size large. To reduce size:

1. Run the cleanup script:
   ```bash
   bash clean-for-deployment.sh
   ```

2. This script:
   - Removes Hugging Face model cache (models will download on first use)
   - Removes unnecessary test files and images
   - Cleans up node_modules and Python caches
   - Removes Git history for deployment
   - Removes ChromaDB files that can be regenerated
   - Removes test data, development files, and large unused models

3. Test the deployment preparation:
   ```bash
   bash test-deployment-prep.sh
   ```
   
   This will validate that all cleanup steps are working and the server can start properly.

## Server Configuration

For deployment, we use a unified server approach with a smart proxy:

1. Use `deployment.js` as the main entry point (uses ES modules)
2. Set the start command to: `NODE_ENV=production node deployment.js`
3. Make sure PORT environment variable is set (or defaults to 3000)
4. The deployment server will:
   - Set environment flags to prevent duplicate servers: `DEPLOYMENT_MODE=true`, `SINGLE_SERVER_MODE=true`
   - Automatically check for and start the Browser API Server (port 8000) if needed
   - Proxy Browser API Server requests through port 3000 via the path `/browser-api/*`
   - Serve static files and handle main application routes
   - Provide health check and monitoring endpoints

## Managing Workflows

To prevent multiple server instances from running in deployment:

1. Use the workflow management script to disable unwanted workflows:
   ```bash
   bash manage-workflows.sh stop     # Stop all workflows
   bash manage-workflows.sh start    # Start only the deployment server
   bash manage-workflows.sh status   # Check current workflow status
   ```

2. If you need to manually configure workflow:
   - Create a file `.replit.workflow.deployment` with content: `NODE_ENV=production node deployment.js`
   - Create a file `.replit.workflow.deployment.name` with content: `Deployment Server`

## Environment Variables

Make sure the following environment variables are set:

- `DATABASE_URL`: PostgreSQL database connection string
- `OPENAI_API_KEY`: OpenAI API key for AI features
- `NODE_ENV`: Set to "production" for deployment
- `DEPLOYMENT_MODE`: Set to "true" to enable deployment optimizations
- `SINGLE_SERVER_MODE`: Set to "true" to prevent multiple servers from running

## Deployment Steps

1. Run the cleanup script to reduce size and remove unnecessary files:
   ```bash
   bash clean-for-deployment.sh
   ```

2. Test deployment preparation (this will test both servers):
   ```bash
   bash test-deployment-prep.sh
   ```

3. Stop all running workflows to prevent conflicts:
   ```bash
   bash manage-workflows.sh stop
   ```

4. Click the Deploy button in Replit
   - This will start the deployment process
   - The unified server will automatically start both the main app and the Browser API Server

5. Set the following in Deployment settings:
   - Start Command: `NODE_ENV=production DEPLOYMENT_MODE=true SINGLE_SERVER_MODE=true node deployment.js`
   - Environment: Node.js

6. Monitor deployment logs for any issues:
   - Look for "GOAT Platform running in PRODUCTION mode" message
   - Check that both servers started successfully 
   - Check for any error messages related to port conflicts

## Verifying Deployment

1. The deployment server exposes these endpoints:
   - Health check: `/api/health`
   - Version info: `/api/version`

2. After deployment, verify these endpoints are working before proceeding.

## Post-Deployment

After deployment:

1. Check the deployed site works by accessing the provided URL
2. Verify API endpoints are working correctly
3. Check database connections are established
4. Confirm that only one server instance is running

## Troubleshooting

If deployment fails:

1. Check deployment logs for specific errors
2. Ensure total size is under 8GB (run `du -sh .` to check)
   - If over the limit, run `bash clean-for-deployment.sh` to reduce size
3. Check server configurations:
   - The main application should use port 3000 only in production mode
   - Browser API Server should use port 8000 and be proxied through `/browser-api`
   - Verify these environment flags are set: `DEPLOYMENT_MODE=true`, `SINGLE_SERVER_MODE=true`
4. Make sure all required environment variables are set
5. Test the deployment server locally:
   ```bash
   bash manage-workflows.sh stop    # Stop all workflows first
   NODE_ENV=production node deployment.js
   ```
6. After deployment, check:
   - Main app health endpoint: `curl https://yourapp.replit.app/api/health`
   - Browser API proxy endpoint: `curl https://yourapp.replit.app/browser-api/docs`

## Support

For any deployment issues, contact the development team.