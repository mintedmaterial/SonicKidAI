# Staged Deployment Guide

This guide outlines the process for performing a staged deployment of the application, which helps prevent resource competition and ensures a successful deployment.

## Overview

The staged deployment approach involves:

1. First deploying the frontend and core server components
2. Then gradually enabling individual workflows as needed

This approach ensures that the main application is successfully deployed before potentially resource-intensive workflows are activated.

## Prerequisites

- Ensure all environment variables are properly set in Replit Secrets
- Make sure the `SKIP_API_SERVER` environment variable is set to `true` for initial deployment
- Verify that all required scripts are executable:
  ```bash
  chmod +x manage-workflows.sh
  chmod +x clean-for-deployment.sh
  chmod +x restart_individual_workflow.sh
  chmod +x monitor_deployment.sh
  ```

## Step 1: Prepare for Deployment

```bash
# Run the clean-for-deployment script to prepare the project
./clean-for-deployment.sh
```

This script will:
- Clean up build files and caches
- Trim log files
- Set necessary environment variables for deployment
- Build the frontend for production
- Stop all workflows

## Step 2: Deploy the Main Application

1. Click the "Deploy" button in Replit
2. Wait for the deployment to complete
3. Verify that the main application is working correctly

## Step 3: Enable Workflows Gradually

After the main application is deployed and working, gradually enable workflows one by one:

```bash
# First, check the status of all workflows
./manage-workflows.sh status

# Start individual workflows as needed
./restart_individual_workflow.sh telegram_bot
./restart_individual_workflow.sh discord_bot

# Wait and verify each workflow before starting the next one
```

## Step 4: Monitor Deployment

Use the monitoring script to check on the status of your deployment:

```bash
./monitor_deployment.sh
```

## Port Configuration

The application uses the following port configuration:

- **Frontend Port**: 3000 (default)
- **Backend Port**: 5000 
- **Browser API Port**: 8000

These ports can be configured via environment variables:
- `FRONTEND_PORT`
- `BACKEND_PORT`
- `BROWSER_API_PORT`

## Environment Variables

The following environment variables control the deployment:

- `SKIP_API_SERVER`: When set to `true`, the Browser API Server will not be started during initial deployment
- `FRONTEND_PORT`: Port for the frontend server (default: 3000)
- `BACKEND_PORT`: Port for the backend server (default: 5000)
- `BROWSER_API_PORT`: Port for the Browser API Server (default: 8000)

## Troubleshooting

### Common Issues

1. **Deployment times out**:
   - Make sure `SKIP_API_SERVER` is set to `true`
   - Ensure all workflows are stopped before deployment

2. **Workflow fails to start after deployment**:
   - Check for conflicting port usage
   - Verify that the required environment variables are set
   - Look for errors in the workflow logs

3. **Resource limits exceeded**:
   - Start fewer workflows simultaneously
   - Consider optimizing resource-intensive workflows

### Getting Help

If you encounter issues with the deployment, refer to:
- `REPLIT_DEPLOYMENT_GUIDE.md` for Replit-specific deployment information
- Workflow logs for detailed error messages
- Replit documentation on deployment limits and best practices

## Next Steps

After successful deployment:

1. Test the application thoroughly
2. Set up monitoring and alerts
3. Consider implementing CI/CD pipelines for future deployments
4. Document the production environment configuration