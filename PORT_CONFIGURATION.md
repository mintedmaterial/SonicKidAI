# Port Configuration Guide

This document explains the port configuration setup for the GOAT Platform on Replit.

## Port Overview

The application uses the following port configuration:

| Service | Port | Environment Variable | Notes |
|---------|------|----------------------|-------|
| Fast Startup Server | 5000 | PORT | Quickly binds for Replit workflow detection |
| Main Server | 8888 | PORT or FRONTEND_PORT | Primary application server |
| Secondary Server | 5001 | SECONDARY_PORT | Proxy server that forwards to main server |
| Browser API | 8000 | BROWSER_API_PORT | Browser integration API |

## Replit Workflow Challenge

The primary challenge with Replit workflows is that they require a service to bind to port 5000 within 20 seconds of startup. Unfortunately, this timeout appears to be extremely strict and difficult to consistently satisfy with our application architecture.

We've created and tested multiple server strategies to try to satisfy this requirement:
- `fast-start-server.js`: Initial attempt to quickly bind to port 5000
- `minimal-server.js`: Simplified server with minimal dependencies
- `ultra-minimal-server.js`: Ultra-streamlined server with no extra logic
- `instant-server.js`: Non-blocking server with immediate binding
- `port-binder.js`: Dedicated server focused solely on port binding
- `bare-server.js`: Absolute minimum 3-line server implementation

Despite these optimization attempts, the Start application workflow consistently fails to start within Replit's 20-second timeout. However, the application itself works correctly when started manually.

## Current Server Architecture

Despite the workflow challenges, the application uses a multi-server configuration:

1. **Main Server (port 8888)**: This is the primary application server that handles all actual requests and business logic.

2. **Secondary Server (port 5001)**: This is a proxy server that forwards all requests to the main server on port 8888.

3. **Browser API (port 8000)**: Dedicated server for browser integration.

## Environment Variables

The following environment variables control the port configuration:

- `PORT`: Controls the port for the main server (default: 8888)
- `FRONTEND_PORT`: Alternative for main server port (default: 8888)
- `SECONDARY_PORT`: Controls the port for the secondary proxy server (default: 5001)
- `BROWSER_API_PORT`: Controls the port for the browser API server (default: 8000)
- `API_BASE_URL`: Optional override for the base URL used in API requests
- `ENABLE_SECONDARY_SERVER`: Controls whether to start the secondary server (default: "true")

## Startup Sequence

The platform uses a carefully designed startup sequence to ensure Replit workflow compatibility:

1. **Fast Server Start**: The `fast-start-server.js` script runs first, immediately binding to port 5000 for Replit workflow detection.

2. **Main Application Launch**: The fast server then launches the main application process in the background:
   - The main server starts on port 8888 (may take 10-15 seconds to initialize)
   - The secondary server starts on port 5001 as a proxy to the main server

3. **Error Handling**:
   - If port 5000 is already in use, the application continues starting normally
   - This provides resilience against workflow restarts and double-launches

## Workflows

The platform includes several workflow configurations:

- **Start application**: Starts the fast server which then launches the main and secondary servers
- **Browser API Server**: Starts the browser API server on port 8000
- **Telegram Bot**: Runs the Telegram bot service (no port binding)
- **Discord Bot**: Runs the Discord bot service (no port binding)

## API Client Configuration

The API client configuration in `src/api_client_config.py` determines which URL to use for API requests. It follows this logic:

1. If `API_BASE_URL` is defined, use that value
2. Otherwise, construct a URL using `http://0.0.0.0:{FRONTEND_PORT}`

## Common Issues

### Workflow Timeout Errors

If you're seeing "Workflow failed to start" or timeout errors:

1. Check if the Fast Startup Server is binding to port 5000 quickly enough
2. Increase verbosity in fast-start-server.js for debugging
3. If workflows consistently fail, try manually restarting the workflow

### Connection Refused Errors

If you're seeing connection refused errors, check:

1. That the appropriate server is running
2. That you're connecting to the correct port (8888 for main server, 5001 for secondary)
3. That you're using `0.0.0.0` instead of `localhost` for URL connections
4. If connecting to the Fast Startup Server (port 5000), be aware that it offers limited functionality

### EADDRINUSE Errors

If you see "EADDRINUSE" errors:

1. This is normal if the Fast Startup Server detects that port 5000 is already in use
2. The application will continue to start normally even with this error
3. If you need to force a clean start, restart the Replit environment completely

### Missing Services or Endpoints

If certain services or endpoints are not available:

1. Check which workflow is running
2. Ensure the Start application workflow is running (it launches all required servers)
3. Verify that the main server has fully started - this can take 10-15 seconds
4. Check the console logs for any initialization errors

## Recommended Workarounds

Due to the persistent issues with the "Start application" workflow, we recommend the following workarounds:

1. **Manual Start Approach**: 
   - Run `node server/index.js` directly in the shell to start the main server
   - This bypasses the workflow timeout restrictions
   - The server will start on port 8888 (or whatever PORT is set to)

2. **Split Workflow Strategy**:
   - Use individual targeted workflows for specific services instead of the "Start application" workflow
   - For example, use "Telegram Bot" or "Browser API Server" for those specific services
   - This avoids the need for all services to pass the strict 20-second timeout check

3. **Alternative Port Configuration**:
   - Consider modifying the application to bind to port 5000 directly
   - This would eliminate the need for the proxy/fast-start servers
   - May require significant code changes but would solve the fundamental issue

## Making Changes

When making changes to the port configuration:

1. Update the relevant environment variables
2. Modify the server scripts (fast-start-server.js, start-dual-servers.js, etc.) if necessary
3. Update PORT_CONFIGURATION.md to document your changes
4. Test by restarting the Start application workflow or using manual start
5. Verify that all necessary servers are started 
6. Test connections using the test_connections.py script