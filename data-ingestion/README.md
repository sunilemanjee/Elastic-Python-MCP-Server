# Property Data Ingestion Script

This script sets up the property index and loads property data into an existing Elasticsearch instance for the intelligent property search demo.

## Overview

The script performs the following tasks:
1. Creates and configures the Elasticsearch property index
2. Downloads property data from a remote source
3. Creates search templates for property queries
4. Loads the data into the configured index

## Directory Structure

```
data-ingestion/
├── data/                  # Local data directory for property data
│   └── properties.json    # Downloaded property data
├── ingest-properties.py   # Main ingestion script
├── requirements.txt       # Python dependencies
├── setup.sh              # Setup script
├── run-ingestion.sh      # Script to run ingestion and update README
└── README.md             # This file
```

## Prerequisites

- Python 3.x
- An existing Elasticsearch Serverless instance
- Required Python packages (installed automatically by setup script):
  - elasticsearch==8.17.0
  - openai
  - streamlit
  - requests
  - python-dateutil

## Elasticsearch Configuration

### Setting Up Elasticsearch Serverless

1. Create an Elasticsearch Serverless instance at [cloud.elastic.co](https://cloud.elastic.co/)
2. Configure the API key with the following privileges:


```json
{
  "ingestion": {
    "cluster": [
      "monitor", "manage"
    ],
    "indices": [
      {
        "names": [
          "properties", "properties_raw"
        ],
        "privileges": [
          "all"
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

> **Note**: This API key configuration is for demo purposes only. In a production environment, you should follow proper security practices and limit the privileges to only what's necessary.  The main README in the source of this project has an example read-only setting to use after ingestion is complete.

## Setup

From a commandline terminal inside the ```data-ingestion``` folder:

1. Make the setup script executable:
```bash
chmod +x setup.sh
```

2. Run the setup script:
```bash
./setup.sh
```

This will:
- Create a Python virtual environment
- Install all required dependencies
- Source the environment variables from the parent directory
- Create the local data directory structure

## Configuration

The script uses the environment variables from the parent folder's `env_config.sh`. You can either:

1. Use an existing configuration:
```bash
source ../env_config.sh
```

2. Or create a new configuration by copying the template:
```bash
cp ../env_config.template.sh ../env_config.sh
# Edit env_config.sh with your credentials
source ../env_config.sh
```

Required environment variables:
- `ES_URL`: Your Elasticsearch Serverless URL
- `ES_API_KEY`: Your Elasticsearch API key
- `PROPERTIES_SEARCH_TEMPLATE`: Search template ID (default: "properties-search-template")
- `ELSER_INFERENCE_ID`: ELSER inference endpoint ID (default: ".elser-2-elasticsearch")
- `ES_INDEX`: Elasticsearch index name (default: "properties")

## Index Structure

The script creates the `properties` index with the following features:
- Semantic search capabilities using ELSER
- Property-specific field mappings
- Search template configuration

## Features

- Creates and configures the Elasticsearch property index with proper mappings
- Downloads property data from a remote source
- Sets up search templates for property queries
- Configures ELSER (Elastic Learned Sparse Encoder) for semantic search
- Handles bulk data ingestion with progress tracking

## Usage

1. Set up your environment variables using the parent folder's `env_config.sh`
2. Activate the virtual environment:
```bash
source venv/bin/activate
```

3. Run the ingestion script using the provided shell script:
```bash
./run-ingestion.sh
```

This script will:
- Activate the virtual environment
- Source the environment variables
- Run the Python ingestion script
- Update this README with the execution timestamp
- Deactivate the virtual environment

Alternatively, you can run the Python script directly:
```bash
python ingest-properties.py
```

4. When you're done, you can deactivate the virtual environment:
```bash
deactivate
```

## Note

This script was originally part of a Jupyter notebook and has been converted to a standalone Python script. It's designed to work with Elasticsearch Serverless and includes specific configurations for the property search demo. 