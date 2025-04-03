# GOAT Platform Deployment Steps

This document provides a concise step-by-step guide for deploying the GOAT Platform in stages to ensure a successful deployment without overwhelming Replit's resources.

## Prerequisites

- Ensure all code is committed and pushed to the repository
- Verify that frontend build artifacts are generated or will be generated during deployment
- Check that environment variables are properly set up:
  ```bash
  # Run the environment variable check script
  ./check_deployment_env.sh
  
  # If any environment variables are missing, add them in the Replit Secrets tab
  # Then run the check script again to verify
  ```

## Port Configuration

The application uses the following port configuration:

- **Frontend Dashboard:** Port 3000 (configurable via `FRONTEND_PORT`)
- **Backend API Services:** Port 5000 (configurable via `BACKEND_PORT`)
- **Browser API Server:** Port 8000 (configurable via `BROWSER_API_PORT`)

During deployment, these ports are used with the following priorities:
1. If `PORT` is set by Replit, it will be used for the main application
2. Otherwise, `FRONTEND_PORT` (or default 3000) will be used

You can customize ports by setting these environment variables in the Replit Secrets tab.

## Stage 1: Deploy Frontend Only

1. **Prepare the environment:**
   ```bash
   # Stop all running workflows (if any)
   ./manage-workflows.sh stop-all
   
   # Run any pre-deployment cleanup or build steps
   ./prepare-for-deployment.sh
   ```

2. **Start the deployment server in frontend-only mode:**
   ```bash
   NODE_ENV=production DEPLOYMENT_MODE=true SINGLE_SERVER_MODE=true SKIP_API_SERVER=true node deployment.js
   ```

3. **Verify frontend deployment:**
   - Check that the server starts successfully
   - Visit the application URL and confirm the frontend loads
   - Verify basic navigation and UI components
   - Note: API calls may fail at this stage, which is expected

## Stage 2: Add Core Backend Services

1. **Deploy the Browser API Server with proper port configuration:**
   ```bash
   # If you want to use custom ports, set them as environment variables
   # export FRONTEND_PORT=3000
   # export BACKEND_PORT=5000
   # export BROWSER_API_PORT=8000
   
   # Start the Browser API Server workflow
   ./restart_individual_workflow.sh "Browser API Server"
   
   # Wait for the service to start up (about 30 seconds)
   sleep 30
   ```

2. **Restart the deployment server with API support:**
   ```bash
   # Stop the previous deployment server instance (if running)
   # Then start a new one without skipping the API server
   # Make sure to use the same port configuration as before
   NODE_ENV=production DEPLOYMENT_MODE=true SINGLE_SERVER_MODE=true node deployment.js
   ```

3. **Verify backend integration:**
   - Check that the Browser API Server is running on its designated port (default: 8000)
   - Check that the frontend is accessible on its port (default: 3000, or PORT if set by Replit)
   - Verify that frontend API calls are working
   - Test key app functionality that relies on the API

## Stage 3: Add Additional Services

1. **Start essential services first:**
   ```bash
   # Start the Telegram Bot workflow
   ./restart_individual_workflow.sh "Telegram Bot"
   
   # Start the Discord Bot workflow
   ./restart_individual_workflow.sh "Discord Bot"
   ```

2. **Monitor deployment health:**
   ```bash
   # Run the monitoring script in a separate terminal
   ./monitor_deployment.sh
   ```

3. **Add remaining services one by one:**
   ```bash
   # Add services with 30-second intervals between them
   ./restart_individual_workflow.sh "Market Service Test"
   sleep 30
   
   ./restart_individual_workflow.sh "Test DexScreener"
   sleep 30
   
   # Add more services as needed
   ```

## Troubleshooting

If you encounter issues during deployment:

1. **Check the logs:**
   - Deployment server logs
   - Workflow logs in the Replit console
   - Monitoring script logs

2. **Common issues:**
   - **Memory limits:** If you see out-of-memory errors, reduce the number of concurrent workflows
   - **Port conflicts:** Make sure no other processes are using the defined ports:
     - Frontend Dashboard: FRONTEND_PORT (default: 3000)
     - Backend API: BACKEND_PORT (default: 5000)
     - Browser API Server: BROWSER_API_PORT (default: 8000)
   - **API unavailability:** Verify the Browser API Server is running on the correct port
   - **Missing environment variables:** Check that all required environment variables are set

3. **Recovery steps:**
   - Stop problematic workflows
   - Restart the deployment in a more minimal configuration
   - Add services one by one, monitoring resources

## Final Verification

Once all services are running:

1. Test end-to-end functionality
2. Verify that all workflows are operational
3. Monitor resource usage for at least 10 minutes
4. Confirm that the application responds correctly to user inputs

## Additional Resources

- Detailed deployment guide: [STAGED_DEPLOYMENT_GUIDE.md](./STAGED_DEPLOYMENT_GUIDE.md)
- Deployment scripts: `deployment.js`, `restart_individual_workflow.sh`
- Monitoring: `monitor_deployment.sh`