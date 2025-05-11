#!/bin/bash

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
python elastic_mcp_server.py 