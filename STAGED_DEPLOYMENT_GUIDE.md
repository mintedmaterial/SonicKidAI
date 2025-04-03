# Staged Deployment Guide for GOAT Platform

## Overview

This document outlines the staged deployment approach for the GOAT Platform to address the issue of multiple competing workflows preventing successful deployment. Instead of trying to deploy everything at once, we'll deploy components in stages:

1. **Stage 1:** Frontend Application Only
2. **Stage 2:** Core Backend Services
3. **Stage 3:** Additional Workflows and Services

## Stage 1: Frontend Application Only

### Deployment Steps

1. **Prepare the deployment server:**
   ```bash
   # Set environment variables to skip the Browser API Server
   NODE_ENV=production DEPLOYMENT_MODE=true SINGLE_SERVER_MODE=true SKIP_API_SERVER=true node deployment.js
   ```

2. **Verify the frontend is working:**
   - Check that the static files are being properly served
   - Confirm that the frontend application loads correctly in the browser
   - Verify that routes are working properly
   - Any API calls that require the Browser API Server will show appropriate error messages

## Stage 2: Core Backend Services

After successful deployment of the frontend, add the Browser API Server:

1. **Start the Browser API Server workflow:**
   ```bash
   # Use the restart_individual_workflow.sh script to start the Browser API Server
   ./restart_individual_workflow.sh "Browser API Server"
   ```

2. **Enable the Browser API Server in the deployment server:**
   ```bash
   # Remove the SKIP_API_SERVER flag
   NODE_ENV=production DEPLOYMENT_MODE=true SINGLE_SERVER_MODE=true node deployment.js
   ```

3. **Verify that the Browser API Server is working:**
   - Check that API endpoints return the expected responses
   - Verify that frontend features that depend on the Browser API Server are functioning

## Stage 3: Additional Workflows and Services

After the core application is deployed and working, add additional workflows one by one:

1. **Start essential services first:**
   ```bash
   # Start the Telegram Bot workflow
   ./restart_individual_workflow.sh "Telegram Bot"
   
   # Start the Discord Bot workflow
   ./restart_individual_workflow.sh "Discord Bot"
   ```

2. **Add additional services as needed:**
   ```bash
   # Example of starting other services
   ./restart_individual_workflow.sh "Market Service Test"
   ./restart_individual_workflow.sh "Test DexScreener"
   ```

3. **Verify each service is working before adding the next one:**
   - Check logs to ensure services are starting correctly
   - Confirm that features dependent on each service are functioning

## Troubleshooting

If a deployment fails:

1. **Check the logs:**
   ```bash
   # View the deployment server logs
   tail -f deployment.log
   ```

2. **Roll back to the previous stage:**
   - If adding a workflow causes issues, stop that workflow and continue with the rest
   - If the core deployment fails, restart without the problematic components

3. **Common issues:**
   - Port conflicts: Ensure no other processes are using ports 3000 or 8000
   - Memory limits: Monitor memory usage and reduce the number of concurrent workflows
   - Environment variables: Verify all required environment variables are set correctly

## Deployment Sequence Diagram

```
┌─────────────┐      ┌───────────────────┐      ┌─────────────────────┐
│ Frontend    │      │ Core Backend      │      │ Additional Services │
│ Application │──────│ (Browser API)     │──────│ (Bots, Analytics)   │
└─────────────┘      └───────────────────┘      └─────────────────────┘
      Stage 1               Stage 2                    Stage 3
```

## Best Practices

1. **Always back up before deployment:**
   - Take snapshots or backups of your Replit environment
   - Document the current state of the deployment

2. **Monitor resource usage:**
   - Keep track of memory usage during deployment
   - Limit the number of concurrent workflows based on available resources

3. **Maintain a deployment log:**
   - Document which components were deployed and when
   - Note any issues encountered and their solutions

4. **Test thoroughly between stages:**
   - Do not proceed to the next stage until the current stage is verified
   - Involve users or testers in the verification process when possible