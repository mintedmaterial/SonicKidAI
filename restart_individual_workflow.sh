#!/bin/bash

# Script to restart a single workflow after deployment
# Usage: ./restart_individual_workflow.sh "Workflow Name"

# Check if workflow name was provided
if [ -z "$1" ]; then
    echo "❌ Error: No workflow name provided"
    echo "Usage: ./restart_individual_workflow.sh \"Workflow Name\""
    exit 1
fi

WORKFLOW_NAME="$1"
echo "🔄 Attempting to restart workflow: $WORKFLOW_NAME"

# Check for essential environment variables
check_env_vars() {
    local missing_vars=()
    
    # Standard deployment variables
    if [ -z "$NODE_ENV" ]; then missing_vars+=("NODE_ENV"); fi
    if [ -z "$DATABASE_URL" ]; then missing_vars+=("DATABASE_URL"); fi
    
    # Check for workflow-specific variables
    case "$WORKFLOW_NAME" in
        "Telegram Bot")
            if [ -z "$TELEGRAM_BOT_TOKEN" ]; then missing_vars+=("TELEGRAM_BOT_TOKEN"); fi
            ;;
        "Discord Bot")
            if [ -z "$DISCORD_BOT_TOKEN" ]; then missing_vars+=("DISCORD_BOT_TOKEN"); fi
            ;;
        "Twitter Test")
            if [ -z "$TWITTER_API_KEY" ]; then missing_vars+=("TWITTER_API_KEY"); fi
            if [ -z "$TWITTER_API_SECRET" ]; then missing_vars+=("TWITTER_API_SECRET"); fi
            ;;
        "Test EternalAI")
            if [ -z "$OPENAI_API_KEY" ]; then missing_vars+=("OPENAI_API_KEY"); fi
            ;;
    esac
    
    # Report missing variables
    if [ ${#missing_vars[@]} -gt 0 ]; then
        echo "⚠️ Warning: Missing environment variables for $WORKFLOW_NAME:"
        for var in "${missing_vars[@]}"; do
            echo "  - $var"
        done
        echo ""
        echo "📝 These variables may be required for the workflow to function correctly."
        echo "   You can add them in the Replit Secrets tab."
        echo ""
        read -p "Continue anyway? (y/n): " -n 1 -r
        echo ""
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            echo "❌ Restart canceled."
            exit 1
        fi
    fi
}

# Run the environment variable check
check_env_vars

# Check if the .replit file exists
if [ ! -f .replit ]; then
    echo "❌ Error: .replit file not found"
    exit 1
fi

# Function to check if the workflow exists
check_workflow_exists() {
    grep -q "\\[\\\"$WORKFLOW_NAME\\\"\\]" .replit
    return $?
}

# Check if the workflow exists
if ! check_workflow_exists; then
    echo "❌ Error: Workflow \"$WORKFLOW_NAME\" not found in .replit file"
    echo "Available workflows:"
    grep -o '\["[^"]*"\]' .replit | tr -d '[]"'
    exit 1
fi

# Generate a unique ID for this restart operation
RESTART_ID=$(date +%s)
LOG_FILE="workflow_restart_${RESTART_ID}.log"

echo "📝 Logging to $LOG_FILE"
echo "⏱️ Restart initiated at $(date)" > "$LOG_FILE"

# Restart the workflow
echo "🚀 Restarting workflow: $WORKFLOW_NAME"
echo "🔍 This may take a moment..."

# Use the Replit workflow API to restart the workflow
# Note: This assumes you're running this script in a Replit environment
curl -s -X POST "https://replit.com/api/v1/graphql" \
     -H "Content-Type: application/json" \
     -H "X-Requested-With: XMLHttpRequest" \
     -H "Accept: application/json" \
     -H "Connection: keep-alive" \
     -H "Referrer: https://replit.com" \
     -H "Cookie: connect.sid=$REPLIT_SID" \
     -d "{\"query\":\"mutation { startRepl(id: \\\"$REPL_ID\\\", workflowName: \\\"$WORKFLOW_NAME\\\") { id } }\"}" \
     >> "$LOG_FILE" 2>&1

RESULT=$?

if [ $RESULT -eq 0 ]; then
    echo "✅ Restart command sent successfully for workflow: $WORKFLOW_NAME"
    echo "⏱️ Restart completed at $(date)" >> "$LOG_FILE"
    echo "📊 Workflow should be active shortly"
else
    echo "❌ Error restarting workflow: $WORKFLOW_NAME"
    echo "⚠️ Check $LOG_FILE for details"
    echo "⚠️ Error occurred at $(date)" >> "$LOG_FILE"
fi

# Wait a moment to allow the workflow to start
echo "⏳ Waiting for workflow to initialize..."
sleep 5

# Check if the workflow is running (this is a simple check)
echo "🔍 Checking if workflow is running..."
ps aux | grep -i "$WORKFLOW_NAME" | grep -v grep >> "$LOG_FILE"
RUNNING=$?

if [ $RUNNING -eq 0 ]; then
    echo "✅ Workflow \"$WORKFLOW_NAME\" appears to be running"
else
    echo "⚠️ Could not confirm if workflow \"$WORKFLOW_NAME\" is running"
    echo "🔄 You may need to check the Replit console or try again"
fi

echo "---"
echo "📝 Restart operation complete. For details see: $LOG_FILE"
echo "⚙️  To deploy another workflow, run this script again with a different workflow name"