# Elasticsearch MCP Server

This is a Model Context Protocol (MCP) server implementation for Elasticsearch, designed to provide a standardized interface for interacting with Elasticsearch services.

## Demo

Watch a demo of this MCP server in action, integrated with Azure OpenAI and Elasticsearch:

https://videos.elastic.co/watch/1qQtsuYSdeXGpvdhfYosnn

This demo showcases:
- Integration with Azure OpenAI for natural language processing
- Elasticsearch for semantic search and property data storage
- Real-time property search and recommendations
- Location-based search capabilities

Related repositories:
- [Elastic Azure OpenAI MCP](https://github.com/sunilemanjee/Elastic_Azure_OpenAI_MCP/tree/main/mcp_aoai) - Azure OpenAI integration with Elasticsearch


## Prerequisites

- Python 3.8 or higher
- Node.js 16 or higher
- Elasticsearch Serverless instance with:
  - ELSER inference endpoint configured
  - Properties index created
  - Search template configured
- Google Maps API key (for geocoding functionality)

## Data Setup

Before running the server, you need to:
1. Create an Elasticsearch Serverless instance
2. Configure the ELSER inference endpoint
3. Create the properties index and search template

You can use this [Colab notebook](https://colab.research.google.com/drive/1hy6XiWBrNiXMQvpjf-Bwd6FSd76aijPt?usp=sharing) to:
- Ingest sample properties data
- Create the required search template
- Configure the ELSER inference endpoint

## Setup

1. Clone the repository:
```bash
git clone <repository-url>
cd Elastic-Python-MCP-Server
```

2. Set up the Python virtual environment:
```bash
./setup_venv.sh
```

3. Configure environment variables:
```bash
# Copy the template configuration file
cp env_config.template.sh env_config.sh

# Edit env_config.sh with your actual configuration values
nano env_config.sh  # or use your preferred editor
```

Required environment variables:
- `ES_URL`: Your Elasticsearch Serverless URL
- `ES_API_KEY`: Your Elasticsearch API key
- `GOOGLE_MAPS_API_KEY`: Your Google Maps API key
- `PROPERTIES_SEARCH_TEMPLATE`: Search template ID (default: "properties-search-template")
- `ELSER_INFERENCE_ID`: ELSER inference endpoint ID (default: ".elser-2-elasticsearch")
- `ES_INDEX`: Elasticsearch index name (default: "properties")

## Running the Server

Start the server using the provided script:
```bash
./run_server.sh
```

The server will start on port 8001 by default. You can verify it's running by checking:
```bash
curl -v http://localhost:8001/sse
```

## Available Tools

The server provides the following tools:

1. `get_properties_template_params`: Get required parameters for the properties search template
2. `geocode_location`: Convert location strings to geo_points using Google Maps API
3. `search_template`: Execute pre-defined Elasticsearch search templates with parameter normalization

## Security Note

The `env_config.sh` file contains sensitive configuration data and is excluded from version control. Always use the template file (`env_config.template.sh`) as a base and create your own local configuration.

## License

This project is licensed under the Apache License 2.0 - see the LICENSE file for details.