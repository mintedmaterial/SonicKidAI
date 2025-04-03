# Port Configuration Guide

This document explains the port configuration setup for the GOAT Platform, focusing on resolving port conflicts in development and deployment environments.

## Overview

The application uses a clear separation of ports:

| Service            | Default Port | Environment Variable |
|-------------------|--------------|----------------------|
| Frontend Dashboard | 3000         | FRONTEND_PORT        |
| Backend API        | 5000         | BACKEND_PORT         |
| Browser API Server | 8000         | BROWSER_API_PORT     |

## Development Environment

In development mode, the application can operate in two ways:

1. **Single-port mode** (recommended): The application runs on a single port (default: 3000)
2. **Dual-port mode**: The application runs on both frontend and backend ports simultaneously (not recommended, leads to conflicts)

### Using Single-port Mode

To use single-port mode, set the environment variable:

```bash
export ENABLE_SECONDARY_SERVER=false
```

You can use the provided helper script to start the server with the correct configuration:

```bash
./start-fixed-server.sh
```

## Port Conflict Resolution

The main port conflict issue occurred because:

1. The server was trying to bind to both port 3000 and 5000 simultaneously in development mode
2. The Replit workflow was configured to wait for port 5000, but the server was primarily using port 3000

### Fixed Configuration

We made the following changes to resolve port conflicts:

1. Updated `server/index.ts` to:
   - Define all port variables clearly: FRONTEND_PORT, BACKEND_PORT, BROWSER_API_PORT
   - Make the secondary server optional via an environment variable
   - Use consistent port naming and configuration

2. Added `start-fixed-server.sh` as a helper script that:
   - Sets the correct environment variables
   - Disables the secondary server to prevent port conflicts
   - Runs the development server

3. Updated `deployment.js` to:
   - Use consistent environment variables for ports
   - Parse port values safely
   - Export port configuration as environment variables for child processes

## Replit Workflow Configuration

The Replit workflow should be configured to use port 3000 instead of 5000:

```toml
[[workflows.workflow.tasks]]
task = "shell.exec"
args = "./start-fixed-server.sh"
waitForPort = 3000
```

## Deployment Port Configuration

During deployment, port configuration follows these priorities:

1. If `PORT` is set by Replit, it will be used for the main application
2. Otherwise, `FRONTEND_PORT` (or default 3000) will be used

The Browser API Server will always use `BROWSER_API_PORT` (default: 8000).

## Troubleshooting

If you encounter port conflicts:

1. Check if multiple instances of the server are running
2. Verify that the port is not already in use by another service
3. Use `./start-fixed-server.sh` to start the server with the correct configuration
4. If starting workflows manually, always start the Browser API Server (port 8000) first