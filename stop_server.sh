#!/bin/bash

echo "Stopping Elastic MCP Server..."

# Find and kill the server process
PID=$(pgrep -f "python elastic_mcp_server.py")

if [ -n "$PID" ]; then
    echo "Found server process with PID: $PID"
    kill $PID
    sleep 2
    
    # Check if process is still running
    if pgrep -f "python elastic_mcp_server.py" > /dev/null; then
        echo "Process still running, forcing termination..."
        pkill -9 -f "python elastic_mcp_server.py"
    fi
    
    echo "Server stopped successfully"
else
    echo "No running server process found"
fi 