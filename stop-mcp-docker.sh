#!/bin/bash

# Stop script for Elastic MCP Server

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}Stopping Elastic MCP Server Docker containers...${NC}"
echo "=================================="

# Check if Docker is running
if ! docker info > /dev/null 2>&1; then
    echo -e "${RED}Error: Docker is not running${NC}"
    exit 1
fi

# Stop containers with docker-compose
echo -e "${YELLOW}Stopping containers...${NC}"
docker-compose down

echo -e "${GREEN}MCP server containers stopped successfully${NC}"
echo ""
echo "To start again: ./run-mcp-docker.sh"
echo "To view logs: docker-compose logs -f" 