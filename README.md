# Elasticsearch MCP Server

This is a Python-based MCP (Model Control Protocol) server that provides an interface for searching and analyzing property data using Elasticsearch. The server was converted from a Jupyter notebook to a standalone Python script.

Watch a demo of the property search system in action:

https://github.com/user-attachments/assets/df498631-fb16-4ba5-b1fd-c14670213d73

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

Before running the MCP server, you need to set up and populate your Elasticsearch instance with property data. This is handled by the scripts in the `data-ingestion` folder.  Follow the setup instructions in the [data-ingestion README](data-ingestion/README.md) to:
   - Set up the Python environment
   - Configure Elasticsearch
   - Download and ingest the property data


## Make your API key Read Only

The data ingestion section created a key with broader server privleges like creating indices and search template scripts.  You can further restrict that API key by editing the existing key's security privileges or making a new key with the following:

```json
{
  "mcp_server_read_only": {
    "cluster": [
      "monitor"
    ],
    "indices": [
      {
        "names": [
          "properties", "properties_raw"
        ],
        "privileges": [
          "read",
          "view_index_metadata"
        ],
        "allow_restricted_indices": false
      }
    ],
    "applications": [],
    "run_as": [],
    "metadata": {},
    "transient_metadata": {
      "enabled": true
    }
  }
}
```


## Requirements

- Python 3.x
- Elasticsearch Serverless instance
- Google Maps API key
- Required Python packages (see requirements.txt)

## Setting Up Required Services

### Creating a Google Maps API Key

1. Go to the [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project or select an existing one
3. Enable the following APIs:
   - Geocoding API
   - Maps JavaScript API
4. Create credentials:
   - Go to "APIs & Services" > "Credentials"
   - Click "Create Credentials" > "API Key"
   - Copy the generated API key
5. (Optional) Restrict the API key to only the required APIs

### Setting Up Elasticsearch Serverless

1. Go to [Elastic Cloud](https://cloud.elastic.co/)
2. Sign up or log in to your account
3. Under "Serverless projects", select "Create serverless project"
4. Choose your preferred cloud provider and region
5. Click "Create deployment"
6. Once created, within Kibana "Getting Started" you'll get an Elastic URL
7. Create an API key with the required privileges (see [Data Ingestion README](data-ingestion/README.md) for details)

## Environment Variables

The following environment variables need to be configured in `env_config.sh`:

- `ES_URL`: Your Elasticsearch Serverless URL
- `ES_API_KEY`: Your Elasticsearch API key
- `GOOGLE_MAPS_API_KEY`: Your Google Maps API key
- `PROPERTIES_SEARCH_TEMPLATE`: Search template ID (default: "properties-search-template")
- `ELSER_INFERENCE_ID`: ELSER inference endpoint ID (default: ".elser-2-elasticsearch")
- `ES_INDEX`: Elasticsearch index name (default: "properties")
- `MCP_PORT`: Port number for the MCP server (default: 8001)

## Setup

1. Clone the repository:
```bash
git clone https://github.com/sunilemanjee/Elastic-Python-MCP-Server.git
cd Elastic-Python-MCP-Server
```

2. If you did not already in the data ingestion instructions, create and configure your environment variables:
```bash
# Copy the template file
cp env_config.template.sh env_config.sh

# Edit env_config.sh with your credentials
nano env_config.sh  # or use your preferred editor
```

3. Set up the Python virtual environment:
```bash
# Create virtual environment
python3 -m venv venv

# Activate virtual environment
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

4. Source your environment variables:
```bash
source env_config.sh
```

## Running the Server

1. Run the server:
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
