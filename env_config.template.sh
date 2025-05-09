#!/bin/bash

# Activate virtual environment if not already activated
if [ -z "$VIRTUAL_ENV" ]; then
    source venv/bin/activate
fi

# Set environment variables
export ES_URL="your_elasticsearch_url"  # Change this to your Elasticsearch URL
export ES_API_KEY="your_elasticsearch_api_key"  # Add your API key if needed
export GOOGLE_MAPS_API_KEY="your_google_maps_api_key"  # Add your Google Maps API key if needed
export PROPERTIES_SEARCH_TEMPLATE="properties-search-template"
export ELSER_INFERENCE_ID=".elser-2-elasticsearch"
export ES_INDEX="properties"
export MCP_PORT=8001  # Default port for the MCP server

echo "Environment variables configured successfully!"
echo "To start the server, run: ./run_server.sh"

# Install dependencies
pip install -r requirements.txt 