# Port Configuration Guide

This document explains the port configuration setup for the GOAT Platform on Replit.

## Port Overview

The application uses the following port configuration:

| Service | Port | Environment Variable | Notes |
|---------|------|----------------------|-------|
| Main Server | 8888 | FRONTEND_PORT | Primary application server |
| Secondary Server | 5000 | SECONDARY_PORT | Proxy server that forwards to main server |
| Browser API | 8000 | BROWSER_API_PORT | Browser integration API |

## Dual Server Setup

Due to Replit workflow restrictions and existing configurations, the application uses a dual server configuration:

1. **Main Server (port 8888)**: This is the primary application server that handles all actual requests.
2. **Secondary Server (port 5000)**: This is a proxy server that forwards all requests to the main server on port 8888.

The secondary server exists because many existing workflows and services expect the application to be running on port 5000.

## Environment Variables

The following environment variables control the port configuration:

- `FRONTEND_PORT`: Controls the port for the main server (default: 8888)
- `BACKEND_PORT`: Used for compatibility with existing code (default: 5000)
- `SECONDARY_PORT`: Controls the port for the secondary proxy server (default: 5000)
- `BROWSER_API_PORT`: Controls the port for the browser API server (default: 8000)
- `API_BASE_URL`: Optional override for the base URL used in API requests

## Workflows

The platform includes several workflows that start the various servers:

- **Start application**: Starts the main application server on port 8888
- **Dual Server**: Starts both the main server (port 8888) and secondary proxy server (port 5000)
- **Browser API Server**: Starts the browser API server on port 8000

## API Client Configuration

The API client configuration in `src/api_client_config.py` determines which URL to use for API requests. It follows this logic:

1. If `API_BASE_URL` is defined, use that value
2. Otherwise, construct a URL using `http://0.0.0.0:{FRONTEND_PORT}`

## Common Issues

### Connection Refused Errors

If you're seeing connection refused errors, check:

1. That the appropriate server is running
2. That you're connecting to the correct port
3. That you're using `0.0.0.0` instead of `localhost` for URL connections

### Missing Services or Endpoints

If certain services or endpoints are not available:

1. Check which workflow is running
2. Ensure the dual server workflow is running for complete compatibility
3. Verify that environment variables are set correctly

## Making Changes

When making changes to the port configuration:

1. Update the relevant environment variables
2. Restart the appropriate workflows
3. Update any hardcoded URLs in the codebase
4. Test connections using the test scripts