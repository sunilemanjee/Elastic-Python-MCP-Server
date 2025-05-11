# Elasticsearch MCP Server

This is a Python-based MCP (Model Control Protocol) server that provides an interface for searching and analyzing property data using Elasticsearch. The server was converted from a Jupyter notebook to a standalone Python script.

## Features

- **Property Search**: Search for properties using various criteria including:
  - Location (with geocoding support)
  - Price range
  - Number of bedrooms/bathrooms
  - Square footage
  - Property features
  - Tax and maintenance costs

- **Geocoding Integration**: Uses Google Maps API to convert location strings into geographic coordinates

- **Elasticsearch Integration**: 
  - Connects to Elasticsearch Serverless
  - Uses ELSER (Elastic Learned Sparse Encoder) for semantic search
  - Supports custom search templates

## Project Structure

```
.
├── data-ingestion/        # Scripts for setting up and populating Elasticsearch
│   ├── data/             # Local data directory for property data
│   ├── ingest-properties.py  # Main ingestion script
│   ├── requirements.txt   # Python dependencies
│   ├── setup.sh          # Setup script
│   └── README.md         # Data ingestion documentation
├── elastic_mcp_server.py  # Main MCP server
├── env_config.sh         # Environment configuration
├── env_config.template.sh # Environment configuration template
├── requirements.txt      # Python dependencies
└── README.md            # This file
```

## Data Ingestion

Before running the MCP server, you need to set up and populate your Elasticsearch instance with property data. This is handled by the scripts in the `data-ingestion` folder:

1. Navigate to the data-ingestion directory:
```bash
cd data-ingestion
```

2. Follow the setup instructions in the [data-ingestion README](data-ingestion/README.md) to:
   - Set up the Python environment
   - Configure Elasticsearch
   - Download and ingest the property data

## Requirements

- Python 3.x
- Elasticsearch Serverless instance
- Google Maps API key
- Required Python packages (see requirements.txt)

## Environment Variables

The following environment variables need to be configured:

- `ES_URL`: Your Elasticsearch Serverless URL
- `ES_API_KEY`: Your Elasticsearch API key
- `GOOGLE_MAPS_API_KEY`: Your Google Maps API key
- `PROPERTIES_SEARCH_TEMPLATE`: Search template ID (default: "properties-search-template")
- `ELSER_INFERENCE_ID`: ELSER inference endpoint ID (default: ".elser-2-elasticsearch")
- `ES_INDEX`: Elasticsearch index name (default: "properties")
- `MCP_PORT`: Port number for the MCP server (default: 8001)

## Running the Server

1. Set up your environment variables in `env_config.sh`
2. Run the server:
```bash
./run_server.sh
```

The server will start on port 8001 by default. You can verify it's running by checking:
```bash
curl -v http://localhost:8001/sse
```

## API Endpoints

The server provides several MCP tools:

1. `get_properties_template_params`: Returns the required parameters for the properties search template
2. `geocode_location`: Converts a location string into geographic coordinates
3. `search_template`: Performs property searches using the configured search template

## Search Parameters

The search template supports the following parameters:
- `query`: Main search query (mandatory)
- `latitude`: Geographic latitude coordinate
- `longitude`: Geographic longitude coordinate
- `bathrooms`: Number of bathrooms
- `tax`: Real estate tax amount
- `maintenance`: Maintenance fee amount
- `square_footage`: Property square footage
- `home_price`: Maximum home price
- `features`: Home features (e.g., *pool*updated kitchen*)

## License

Copyright Elasticsearch B.V. and contributors
SPDX-License-Identifier: Apache-2.0
