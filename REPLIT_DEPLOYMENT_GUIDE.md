# Replit Deployment Guide

This guide provides detailed instructions for deploying this application on Replit, with a focus on managing resource constraints and ensuring a successful deployment.

## Replit Deployment Considerations

Replit has specific constraints that need to be considered when deploying complex applications:

1. **Resource Limits**: Replit has CPU, memory, and storage limits that vary by subscription tier
2. **Deployment Process**: Replit's deployment is a one-click process that builds and deploys the application
3. **Environment Variables**: All environment variables from the development environment need to be transferred to secrets
4. **Workflow Management**: Multiple workflows must be managed carefully to avoid resource competition

## Pre-Deployment Setup

### Environment Variables

Ensure all required environment variables are set as Replit Secrets:

1. Click on the "Secrets" tab in your Replit project
2. Add all needed environment variables as secrets, particularly:
   - `SKIP_API_SERVER=true` (for initial deployment)
   - `FRONTEND_PORT=3000` 
   - `BACKEND_PORT=5000`
   - `BROWSER_API_PORT=8000`
   - Database credentials
   - API keys
   - Other service credentials

### Verify Port Configuration

The application uses specific ports that should be configured via environment variables:

- **Frontend**: Port 3000 (`FRONTEND_PORT`)
- **Backend API**: Port 5000 (`BACKEND_PORT`)
- **Browser API**: Port 8000 (`BROWSER_API_PORT`)

Make sure these ports are properly configured and not causing conflicts.

## Deployment Steps

### 1. Prepare the Project

```bash
# Run the clean-for-deployment script
./clean-for-deployment.sh
```

### 2. Deploy via Replit

1. Click the "Deploy" button in the Replit interface
2. Wait for the build and deployment process to complete
3. Once deployed, your application will be available at `https://your-project-name.username.repl.co`

### 3. Post-Deployment Workflow Management

After successful deployment of the main application:

```bash
# Check status of all workflows
./manage-workflows.sh status

# Start essential workflows first
./restart_individual_workflow.sh telegram_bot

# Wait a few minutes, then verify the workflow is running correctly
./manage-workflows.sh status

# Start additional workflows one by one
./restart_individual_workflow.sh discord_bot
# Wait and verify before continuing with more workflows
```

## Replit-Specific Troubleshooting

### Deployment Timeouts

If deployment times out or fails due to resource constraints:

1. Ensure `SKIP_API_SERVER=true` is set in Secrets
2. Stop all workflows before deploying
3. Reduce the number of dependencies or optimize build scripts
4. Split deployment into smaller stages

### "Internal Service Error"

If you see an "Internal Service Error" after deployment:

1. Check the Replit console for error messages
2. Verify that the server is actually running on the correct port
3. Look for port conflicts in the application
4. Check if the build process completed successfully

### Workflow Failures

If workflows fail to start after deployment:

1. Check workflow logs for specific error messages
2. Verify that required environment variables are set
3. Ensure no port conflicts between different workflows
4. Start workflows one at a time to identify problematic ones

### Resource Limit Errors

If you encounter resource limit errors:

1. Optimize CPU and memory-intensive processes
2. Reduce the number of concurrent workflows
3. Consider upgrading to a higher Replit subscription tier
4. Implement lazy-loading and better resource management

## Staged Deployment Workflow

For complex applications, follow a staged deployment workflow:

1. Deploy only the frontend and core server first
2. Verify that the basic application works
3. Gradually enable individual workflows one at a time
4. Monitor performance and resource usage after each workflow is started

For more detailed information on the staged deployment approach, see `STAGED_DEPLOYMENT_GUIDE.md`.

## Production Considerations

### Monitoring

Monitor your deployed application:

```bash
# Check deployment status
./monitor_deployment.sh
```

### Logs and Debugging

Access logs for debugging:

1. Check Replit console for real-time logs
2. Use workflow logs for specific service issues
3. Implement structured logging for better troubleshooting

### Updates and Maintenance

For future updates:

1. Make changes in a development environment first
2. Test thoroughly before deploying to production
3. Follow the staged deployment process for updates
4. Consider implementing a CI/CD pipeline for automated testing and deployment