# Port Configuration Guide

This document outlines the port configuration used in the application to ensure all services work together correctly without port conflicts.

## Overview

The application uses three main ports:

| Service          | Port | Environment Variable |
|------------------|------|---------------------|
| Frontend         | 3000 | FRONTEND_PORT       |
| Backend API      | 5000 | BACKEND_PORT        |
| Browser API      | 8000 | BROWSER_API_PORT    |

## Configuration

### Environment Variables

Set the following environment variables to configure the ports:

```
FRONTEND_PORT=3000
BACKEND_PORT=5000
BROWSER_API_PORT=8000
```

These can be set in:
- `.env` file for local development
- Replit Secrets for deployment

### Default Values

If not specified, the application will use these default port values:
- Frontend: 3000
- Backend API: 5000
- Browser API: 8000

## Service-Specific Configuration

### Node.js Server (Frontend + Backend)

The main Node.js server handles both frontend and backend services:

- Frontend is served on `FRONTEND_PORT` (3000)
- Backend API routes are accessible at `FRONTEND_PORT/api` (3000/api)

Configuration is in:
- `server/index.ts`
- `deployment.js`

### Python Browser API Server

The Python-based Browser API server runs on `BROWSER_API_PORT` (8000):

- This service can be skipped during initial deployment by setting `SKIP_API_SERVER=true`
- Configuration is in `src/server/app.py`

### Workflow Services

Each workflow should respect port configuration to avoid conflicts:

- Discord Bot: Uses API client connection to Backend API port
- Telegram Bot: Uses API client connection to Backend API port
- Various test workflows: Should avoid using the main ports

## Common Issues and Solutions

### Port Conflicts

If you experience port conflicts:

1. Check if multiple services are trying to use the same port
2. Make sure environment variables are properly set and propagated to all services
3. Verify that no other applications on your system are using these ports

### Connection Errors

If services cannot connect to each other:

1. Ensure the correct host is being used (usually `localhost` or `0.0.0.0`)
2. Check that the correct port is being used for connection
3. Verify firewall or network configuration is not blocking connections

## Best Practices

1. Always use environment variables for port configuration
2. In Python services, read port configuration:
   ```python
   backend_port = os.environ.get("BACKEND_PORT", "5000")
   ```
3. In Node.js services, read port configuration:
   ```javascript
   const frontendPort = process.env.FRONTEND_PORT || 3000;
   ```
4. When running in a workflow, ensure the service is aware of the correct ports

## Deployment Considerations

During deployment:

1. Set all port-related environment variables as Replit Secrets
2. Consider setting `SKIP_API_SERVER=true` for initial deployment
3. After successful deployment of the main server, start the Browser API Server separately

For more details on deployment, refer to `STAGED_DEPLOYMENT_GUIDE.md` and `REPLIT_DEPLOYMENT_GUIDE.md`.