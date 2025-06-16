#!/bin/bash

# Activate virtual environment
source venv/bin/activate

# Source environment variables
source ../env_config.sh

# Run the Python script
echo "Starting property data ingestion..."
python ingest-properties.py

# Get the current timestamp
TIMESTAMP=$(date "+%Y-%m-%d %H:%M:%S")

# Update README.md with execution information
echo -e "\n## Last Execution\nLast run: $TIMESTAMP" >> README.md

# Deactivate virtual environment
deactivate

echo "Ingestion complete! README.md has been updated with execution timestamp." 