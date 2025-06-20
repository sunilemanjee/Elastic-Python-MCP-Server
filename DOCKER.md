# Docker Setup for Elastic MCP Server

This document explains how to run the Elastic MCP Server using Docker containers.

## Overview

The Docker setup provides a containerized version of the MCP server that:
- Runs in an isolated environment
- Includes all necessary dependencies
- Provides health checks and monitoring
- Supports easy deployment and scaling

## Prerequisites

- Docker and Docker Compose installed
- Elasticsearch Serverless instance configured
- Google Maps API key
- Property data ingested into Elasticsearch (see [Data Ingestion README](data-ingestion/README.md))

## Quick Start

### 1. Set up Environment Variables

Copy the example environment file and configure it:

```bash
cp env.example .env
```

Edit `.env` with your actual credentials:

```bash
# Required
ES_URL=https://your-deployment.es.us-east-1.aws.cloud.es.io
ES_API_KEY=your_elasticsearch_api_key
GOOGLE_MAPS_API_KEY=your_google_maps_api_key

# Optional (defaults provided)
PROPERTIES_SEARCH_TEMPLATE=properties-search-template
ELSER_INFERENCE_ID=.elser-2-elasticsearch
ES_INDEX=properties
MCP_PORT=8001
```

### 2. Run with Docker Compose

Use the provided script for easy setup:

```bash
./docker-run.sh
```

Or run manually:

```bash
docker-compose up --build -d
```

### 3. Verify the Server

Check if the server is running:

```bash
curl http://localhost:8001/sse
```

View logs:

```bash
docker-compose logs -f
```

## Docker Configuration

### Dockerfile

The `Dockerfile` creates a container with:
- Python 3.11 slim base image
- All required dependencies installed
- Non-root user for security
- Health checks configured
- Port 8001 exposed

### Docker Compose

The `docker-compose.yml` provides:
- Environment variable injection
- Port mapping (8001:8001)
- Health checks
- Automatic restart policy
- Network isolation

### Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `ES_URL` | Yes | Elasticsearch Serverless URL |
| `ES_API_KEY` | Yes | Elasticsearch API key |
| `GOOGLE_MAPS_API_KEY` | Yes | Google Maps API key |
| `ES_USERNAME` | No | Username (if not using API key) |
| `ES_PASSWORD` | No | Password (if not using API key) |
| `ES_CA_CERT` | No | CA certificate path |
| `PROPERTIES_SEARCH_TEMPLATE` | No | Search template ID (default: properties-search-template) |
| `ELSER_INFERENCE_ID` | No | ELSER inference endpoint (default: .elser-2-elasticsearch) |
| `ES_INDEX` | No | Elasticsearch index name (default: properties) |
| `MCP_PORT` | No | Server port (default: 8001) |

## Management Commands

### Start the server
```bash
docker-compose up -d
```

### Stop the server
```bash
docker-compose down
```

### View logs
```bash
docker-compose logs -f
```

### Restart the server
```bash
docker-compose restart
```

### Rebuild and start
```bash
docker-compose up --build -d
```

### Check container status
```bash
docker-compose ps
```

## Production Deployment

### Using Docker Run

For production deployments without Docker Compose:

```bash
docker run -d \
  --name elastic-mcp-server \
  -p 8001:8001 \
  -e ES_URL="your_elasticsearch_url" \
  -e ES_API_KEY="your_api_key" \
  -e GOOGLE_MAPS_API_KEY="your_google_maps_key" \
  --restart unless-stopped \
  elastic-mcp-server:latest
```

### Using Docker Swarm

Create a stack file `docker-stack.yml`:

```yaml
version: '3.8'

services:
  elastic-mcp-server:
    image: elastic-mcp-server:latest
    ports:
      - "8001:8001"
    environment:
      - ES_URL=${ES_URL}
      - ES_API_KEY=${ES_API_KEY}
      - GOOGLE_MAPS_API_KEY=${GOOGLE_MAPS_API_KEY}
    deploy:
      replicas: 2
      restart_policy:
        condition: on-failure
    secrets:
      - es_api_key
      - google_maps_key

secrets:
  es_api_key:
    external: true
  google_maps_key:
    external: true
```

Deploy with:

```bash
docker stack deploy -c docker-stack.yml elastic-mcp
```

### Using Kubernetes

Create a deployment:

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: elastic-mcp-server
spec:
  replicas: 2
  selector:
    matchLabels:
      app: elastic-mcp-server
  template:
    metadata:
      labels:
        app: elastic-mcp-server
    spec:
      containers:
      - name: elastic-mcp-server
        image: elastic-mcp-server:latest
        ports:
        - containerPort: 8001
        env:
        - name: ES_URL
          valueFrom:
            secretKeyRef:
              name: elastic-mcp-secrets
              key: es-url
        - name: ES_API_KEY
          valueFrom:
            secretKeyRef:
              name: elastic-mcp-secrets
              key: es-api-key
        - name: GOOGLE_MAPS_API_KEY
          valueFrom:
            secretKeyRef:
              name: elastic-mcp-secrets
              key: google-maps-key
        livenessProbe:
          httpGet:
            path: /sse
            port: 8001
          initialDelaySeconds: 30
          periodSeconds: 10
        readinessProbe:
          httpGet:
            path: /sse
            port: 8001
          initialDelaySeconds: 5
          periodSeconds: 5
```

## Security Considerations

### Environment Variables
- Never commit `.env` files to version control
- Use Docker secrets or Kubernetes secrets for sensitive data
- Rotate API keys regularly

### Container Security
- The container runs as a non-root user
- Minimal base image (Python slim)
- Health checks prevent unhealthy containers from serving traffic

### Network Security
- Only port 8001 is exposed
- Use reverse proxies (nginx, traefik) for additional security
- Consider using Docker networks for service-to-service communication

## Troubleshooting

### Container won't start
```bash
# Check logs
docker-compose logs

# Check environment variables
docker-compose config
```

### Health check failures
```bash
# Check if the server is responding
curl -v http://localhost:8001/sse

# Check container health
docker ps --format "table {{.Names}}\t{{.Status}}"
```

### Permission issues
```bash
# Fix file permissions
chmod +x docker-run.sh
chmod 600 .env
```

### Port conflicts
```bash
# Check what's using port 8001
lsof -i :8001

# Change port in docker-compose.yml
ports:
  - "8002:8001"  # Use port 8002 on host
```

## Monitoring

### Health Checks
The container includes health checks that verify the MCP server is responding:

```bash
# Check health status
docker ps --format "table {{.Names}}\t{{.Status}}"
```

### Logs
```bash
# Follow logs in real-time
docker-compose logs -f

# View recent logs
docker-compose logs --tail=100
```

### Metrics
Consider adding monitoring with:
- Prometheus metrics endpoint
- Application performance monitoring (APM)
- Container resource monitoring

## Development

### Building for Development
```bash
# Build with development dependencies
docker build -t elastic-mcp-server:dev .

# Run with volume mounts for development
docker run -it --rm \
  -p 8001:8001 \
  -v $(pwd):/app \
  -e ES_URL="your_url" \
  -e ES_API_KEY="your_key" \
  -e GOOGLE_MAPS_API_KEY="your_key" \
  elastic-mcp-server:dev
```

### Testing
```bash
# Run tests in container
docker-compose exec elastic-mcp-server python -m pytest

# Test API endpoints
curl -X POST http://localhost:8001/tools/get_properties_template_params
```

## Support

For issues with the Docker setup:
1. Check the troubleshooting section above
2. Review the logs: `docker-compose logs`
3. Verify environment variables are set correctly
4. Ensure Elasticsearch and Google Maps APIs are accessible 