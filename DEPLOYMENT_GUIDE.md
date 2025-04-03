# Deployment Guide for Replit Application

This guide provides a summary of the deployment process and available tools for managing deployment on Replit.

## Staged Deployment Approach

A staged deployment approach is recommended to avoid resource conflicts on Replit:

1. First deploy the frontend application
2. Then gradually add backend services and workflows

This approach helps ensure successful deployments by preventing resource competition.

## Available Tools

The following tools are available for managing deployment:

- **clean-for-deployment.sh**: Prepares the project for deployment by cleaning up files, stopping workflows, and setting environment variables
- **manage-workflows.sh**: Helps manage workflow status, start/stop workflows, and list available workflows
- **restart_individual_workflow.sh**: Restarts a specific workflow after deployment
- **monitor_deployment.sh**: Monitors the status of deployment, services, and resources

## Quick Start

```bash
# 1. Prepare for deployment
./clean-for-deployment.sh

# 2. Deploy using Replit's deploy button

# 3. After deployment, check status
./monitor_deployment.sh

# 4. Start essential workflows one by one
./restart_individual_workflow.sh telegram_bot
# Wait and verify it's working before continuing

./restart_individual_workflow.sh discord_bot
# Continue with additional workflows as needed
```

## Port Configuration

The application uses three main ports:

- **Frontend Port**: 3000 (FRONTEND_PORT)
- **Backend Port**: 5000 (BACKEND_PORT)
- **Browser API Port**: 8000 (BROWSER_API_PORT)

## Environment Variables

Important environment variables for deployment:

- **SKIP_API_SERVER**: Set to `true` for initial deployment to skip Browser API Server
- **FRONTEND_PORT**: Port for the frontend (default: 3000)
- **BACKEND_PORT**: Port for the backend API (default: 5000)
- **BROWSER_API_PORT**: Port for the Browser API Server (default: 8000)

## Detailed Documentation

For more detailed information, refer to:

- [Staged Deployment Guide](STAGED_DEPLOYMENT_GUIDE.md)
- [Replit Deployment Guide](REPLIT_DEPLOYMENT_GUIDE.md)
- [Port Configuration](PORT_CONFIGURATION.md)

## Troubleshooting

If you encounter issues during deployment:

1. Check workflow logs for errors
2. Verify environment variables are properly set
3. Use `monitor_deployment.sh` to diagnose issues
4. Ensure you're not running too many workflows simultaneously
5. Check for port conflicts between services

## Support

If you need additional support with deployment, please contact the development team.