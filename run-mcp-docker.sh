#!/bin/bash

# Docker run script for Elastic MCP Server

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}Elastic MCP Server Docker Runner${NC}"
echo "=================================="

# Check if .env file exists
if [ ! -f .env ]; then
    echo -e "${YELLOW}Warning: .env file not found${NC}"
    echo "Please create a .env file based on env.example"
    echo "Required environment variables:"
    echo "  - ES_URL: Your Elasticsearch URL"
    echo "  - ES_API_KEY: Your Elasticsearch API key"
    echo "  - GOOGLE_MAPS_API_KEY: Your Google Maps API key"
    exit 1
fi

# Load environment variables
source .env

# Validate required environment variables
if [ -z "$ES_URL" ]; then
    echo -e "${RED}Error: ES_URL is not set in .env file${NC}"
    exit 1
fi

if [ -z "$ES_API_KEY" ]; then
    echo -e "${RED}Error: ES_API_KEY is not set in .env file${NC}"
    exit 1
fi

if [ -z "$GOOGLE_MAPS_API_KEY" ]; then
    echo -e "${RED}Error: GOOGLE_MAPS_API_KEY is not set in .env file${NC}"
    exit 1
fi

echo -e "${GREEN}Environment variables loaded successfully${NC}"

# Check if Docker is running
if ! docker info > /dev/null 2>&1; then
    echo -e "${RED}Error: Docker is not running${NC}"
    exit 1
fi

# Build and run with docker-compose
echo -e "${GREEN}Building and starting the MCP server...${NC}"
docker-compose up --build -d

echo -e "${GREEN}MCP server is starting up...${NC}"
echo "Server will be available at: http://localhost:8001/sse"
echo ""
echo "To view logs: docker-compose logs -f"
echo "To stop: ./stop-mcp-docker.sh or docker-compose down"
echo "To restart: docker-compose restart" 