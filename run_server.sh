#!/bin/bash

# Parse command line arguments
BACKGROUND=false
while [[ $# -gt 0 ]]; do
    case $1 in
        -b|--background)
            BACKGROUND=true
            shift
            ;;
        -h|--help)
            echo "Usage: $0 [-b|--background] [-h|--help]"
            echo "  -b, --background  Run server in background"
            echo "  -h, --help        Show this help message"
            exit 0
            ;;
        *)
            echo "Unknown option $1"
            echo "Use -h or --help for usage information"
            exit 1
            ;;
    esac
done

# Load environment variables from env_config.sh
if [ -f env_config.sh ]; then
    source env_config.sh
else
    echo "Error: env_config.sh not found. Please create it from env_config.template.sh"
    exit 1
fi

# Check for required environment variables
if [ -z "$ES_URL" ]; then
    echo "Error: ES_URL environment variable is not set"
    exit 1
fi

if [ -z "$ES_API_KEY" ]; then
    echo "Error: ES_API_KEY environment variable is not set"
    exit 1
fi

if [ -z "$GOOGLE_MAPS_API_KEY" ]; then
    echo "Error: GOOGLE_MAPS_API_KEY environment variable is not set"
    exit 1
fi

# Run the server
if [ "$BACKGROUND" = true ]; then
    echo "Starting Elastic MCP Server in background..."
    
    # Create logs directory if it doesn't exist
    mkdir -p logs
    
    nohup python elastic_mcp_server.py > logs/elastic_mcp_server.log 2>&1 &
    PID=$!
    echo "Server started with PID: $PID"
    echo "Logs are being written to: logs/elastic_mcp_server.log"
    echo "To stop the server, run: kill $PID"
    echo "Or use: pkill -f elastic_mcp_server.py"
else
    echo "Starting Elastic MCP Server in foreground..."
    python elastic_mcp_server.py 
fi 