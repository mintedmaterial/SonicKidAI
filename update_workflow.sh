#!/bin/bash

# Replace the command line in the Twitter Test workflow file
echo "<command>
python3 test_twitter_standalone.py
</command>" > .replit.workflow.twitter_test

# Make the script executable
chmod +x .replit.workflow.twitter_test

echo "Workflow updated to use test_twitter_standalone.py"