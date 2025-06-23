# Property Data Ingestion

This script loads property data into Elasticsearch for the intelligent property search demo with advanced capabilities for data processing and semantic search.

## What This Does

1. **Creates** Elasticsearch indices with proper mappings (raw and processed)
2. **Downloads** property data from a remote source
3. **Sets up** search templates for property queries
4. **Processes** data with ELSER for semantic search capabilities
5. **Provides** modular operations for different use cases

## Quick Start

### Prerequisites
- Python 3.x
- Elasticsearch Serverless instance (see setup below)

### Setup & Run

1. **Make setup script executable:**
   ```bash
   chmod +x setup.sh
   ```

2. **Run setup:**
   ```bash
   ./setup.sh
   ```

3. **Run ingestion (choose your option):**
   ```bash
   # Run everything (default)
   ./run-ingestion.sh
   
   # Or run specific operations
   ./run-ingestion.sh --full-ingestion    # Complete pipeline
   ./run-ingestion.sh --searchtemplate    # Only create search templates
   ./run-ingestion.sh --reindex           # Only reindex (requires raw index)
   ./run-ingestion.sh --recreate-index    # Recreate index without processing
   ./run-ingestion.sh --use-small-dataset # Run everything with smaller dataset
   ```

## Command Line Options

The ingestion script supports several operation modes:

### `--searchtemplate`
- Only creates/updates search templates
- Useful for template development and testing
- Fastest operation

### `--full-ingestion`
- Runs the complete data ingestion pipeline
- Creates indices, downloads data, processes with ELSER
- Most comprehensive operation

### `--reindex`
- Only performs reindexing from raw to processed index
- **Recreates the properties index** to ensure clean state with latest mapping
- Requires existing raw index
- Useful for reprocessing data with ELSER

### `--recreate-index`
- Deletes and recreates the properties index
- Downloads and loads data without ELSER processing
- Useful for testing or when ELSER is not available

### `--use-small-dataset`
- Uses a smaller 5000-line dataset instead of the full 48,466-line dataset
- Runs the complete data ingestion pipeline with reduced data volume
- Useful for faster testing, development, and when full dataset is not needed
- Can be combined with other flags for specific operations

### Multiple Operations
You can combine flags to run multiple operations:
```bash
./run-ingestion.sh --searchtemplate --full-ingestion
./run-ingestion.sh --full-ingestion --reindex
./run-ingestion.sh --full-ingestion --use-small-dataset
./run-ingestion.sh --recreate-index --use-small-dataset
```

## Elasticsearch Setup

### 1. Create Elasticsearch Serverless Instance
- Go to [cloud.elastic.co](https://cloud.elastic.co/)
- Create a new Serverless instance

### 2. Create API Key
Create an API key with these privileges:

```json
{
  "ingestion": {
    "cluster": ["monitor", "manage"],
    "indices": [
      {
        "names": ["properties", "properties_raw"],
        "privileges": ["all"],
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

> **Security Note**: This configuration is for demo purposes. For production, use minimal required privileges. See the main project README for read-only settings after ingestion.

### 3. Configure Environment
Copy the template and add your credentials:

```bash
cp ../env_config.template.sh ../env_config.sh
# Edit env_config.sh with your ES_URL and ES_API_KEY
```

Required variables:
- `ES_URL`: Your Elasticsearch Serverless URL
- `ES_API_KEY`: Your Elasticsearch API key

Optional variables (have defaults):
- `PROPERTIES_SEARCH_TEMPLATE`: Search template ID
- `ELSER_INFERENCE_ID`: ELSER inference endpoint ID  
- `ES_INDEX`: Elasticsearch index name

## Directory Structure

```
data-ingestion/
├── data/                          # Downloaded property data
├── ingest-properties.py           # Main ingestion script with CLI options
├── requirements.txt               # Python dependencies
├── setup.sh                      # Setup script
├── run-ingestion.sh              # Run ingestion script with options
├── search-template.mustache      # Search template definition
├── raw-index-mapping.json        # Raw index mapping
├── properties-index-mapping.json # Processed index mapping
└── README.md                     # This file
```

## Manual Usage

If you prefer to run manually:

1. **Activate virtual environment:**
   ```bash
   source venv/bin/activate
   ```

2. **Source environment variables:**
   ```bash
   source ../env_config.sh
   ```

3. **Run the script with options:**
   ```bash
   # Run everything
   python ingest-properties.py
   
   # Or specific operations
   python ingest-properties.py --searchtemplate
   python ingest-properties.py --full-ingestion
   python ingest-properties.py --reindex
   python ingest-properties.py --recreate-index
   python ingest-properties.py --use-small-dataset
   ```

4. **Deactivate when done:**
   ```bash
   deactivate
   ```

## What Gets Created

The script creates two indices:

### `properties_raw`
- Raw property data without processing
- Used as source for ELSER processing
- Cleaned up after successful processing

### `properties`
- Final processed index with ELSER semantic fields
- Property-specific field mappings
- Search templates for queries
- Ready for semantic search

## Dataset Options

The script supports two dataset sizes:

### Full Dataset (Default)
- **Source**: `properties.json` (48,466 documents)
- **Use case**: Production and comprehensive testing
- **Processing time**: Longer due to larger volume
- **Command**: `./run-ingestion.sh` or `./run-ingestion.sh --full-ingestion`

### Small Dataset
- **Source**: `properties-filtered-5000-lines.json` (5,000 documents)
- **Use case**: Development, testing, and quick validation
- **Processing time**: Faster due to reduced volume
- **Command**: `./run-ingestion.sh --use-small-dataset`

Both datasets contain the same property data structure and are processed identically with ELSER semantic fields.

## Advanced Features

### ELSER Integration
- **Automatic deployment check** before processing
- **Semantic field generation** for natural language search
- **Retry logic** for reindex operations
- **Progress tracking** during long operations

### Performance Optimizations
- **Parallel bulk indexing** with configurable thread count
- **Chunked processing** to handle large datasets
- **Async reindexing** with progress monitoring
- **Error handling** and retry mechanisms

### Data Quality
- **JSON validation** during download
- **Document count verification** after processing
- **Automatic cleanup** of temporary data

## Troubleshooting

- **Permission errors**: Make sure `setup.sh` and `run-ingestion.sh` are executable
- **Environment issues**: Verify `env_config.sh` exists and has correct credentials
- **Elasticsearch connection**: Check your ES_URL and API key are correct
- **ELSER deployment**: Ensure ELSER is properly deployed before running semantic processing
- **Memory issues**: For large datasets, consider using `--use-small-dataset` or reducing chunk size in the script

## Dependencies

The setup script automatically installs:
- elasticsearch==8.17.0
- openai
- streamlit  
- requests
- python-dateutil

## Execution History

The script automatically tracks execution history in this README:

## Last Execution
Last run: 2025-06-20 20:42:58

## Last Reindex Operation
Last run: 2025-06-20 21:02:29

## Last Reindex Operation
Last run: 2025-06-20 21:02:39

## Last Reindex Operation
Last run: 2025-06-20 21:04:35

## Last Reindex Operation
Last run: 2025-06-20 21:05:31

## Last Reindex Operation
Last run: 2025-06-21 04:28:09

## Last Reindex Operation
Last run: 2025-06-21 06:14:51

## Last Reindex Operation
Last run: 2025-06-21 06:24:58

## Last Recreate Properties Index
Last run: 2025-06-21 06:29:18

## Last Recreate Properties Index
Last run: 2025-06-21 06:29:34

## Last Search Template Creation
Last run: 2025-06-21 06:29:49

## Last Search Template Creation
Last run: 2025-06-21 06:36:45
