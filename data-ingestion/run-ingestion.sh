#!/bin/bash

# Function to display usage
show_usage() {
    echo "Usage: $0 [OPTIONS]"
    echo ""
    echo "Options:"
    echo "  --searchtemplate    Run the search template creation part"
    echo "  --full-ingestion    Run the complete data ingestion pipeline (create indices, download data, process with ELSER)"
    echo "  --recreate-index    Delete and recreate the properties index (no data processing)"
    echo "  --use-small-5k-dataset Use the smaller 5000-line dataset instead of the full dataset"
    echo "  --use-500-dataset   Use the tiny 500-line dataset instead of the full dataset"
    echo "  --ingest-raw-500-dataset Use raw index mapping (no ELSER) with 500-line dataset"
    echo "  --instruqt          Use Instruqt workshop settings for Elasticsearch connection"
    echo "  --reingest-instruqt-with-endpoints Delete properties index, recreate with Instruqt mapping, and reingest 500-line dataset"
    echo "  -h, --help          Show this help message"
    echo ""
    echo "Multiple flags can be combined to run specific operations."
    echo "If no flags are provided, the entire script will run."
    echo ""
    echo "Examples:"
    echo "  $0                    # Run entire script"
    echo "  $0 --searchtemplate   # Only create search templates"
    echo "  $0 --full-ingestion   # Run complete data ingestion pipeline"
    echo "  $0 --recreate-index   # Delete and recreate properties index"
    echo "  $0 --use-small-5k-dataset # Run entire script with smaller dataset"
    echo "  $0 --use-500-dataset  # Run entire script with tiny dataset"
    echo "  $0 --ingest-raw-500-dataset # Run ingestion with raw index mapping and 500-line dataset"
    echo "  $0 --instruqt         # Run entire script with Instruqt workshop settings"
    echo "  $0 --searchtemplate --full-ingestion  # Create search templates and run ingestion"
    echo "  $0 --full-ingestion --use-small-5k-dataset # Run ingestion with smaller dataset"
    echo "  $0 --full-ingestion --use-500-dataset  # Run ingestion with tiny dataset"
    echo "  $0 --full-ingestion --instruqt        # Run ingestion with Instruqt workshop settings"
    echo "  $0 --reingest-instruqt-with-endpoints # Delete properties index, recreate with Instruqt mapping, and reingest 500-line dataset"
}

# Parse command line arguments
SEARCHTEMPLATE_ONLY=false
FULL_INGESTION_ONLY=false
RECREATE_INDEX_ONLY=false
USE_SMALL_DATASET=false
USE_TINY_DATASET=false
INGEST_RAW_500_DATASET=false
INSTRUQT_ONLY=false
REINGEST_INSTRUQT_WITH_ENDPOINTS=false

while [[ $# -gt 0 ]]; do
    case $1 in
        --searchtemplate)
            SEARCHTEMPLATE_ONLY=true
            shift
            ;;
        --full-ingestion)
            FULL_INGESTION_ONLY=true
            shift
            ;;
        --recreate-index)
            RECREATE_INDEX_ONLY=true
            shift
            ;;
        --use-small-5k-dataset)
            USE_SMALL_DATASET=true
            shift
            ;;
        --use-500-dataset)
            USE_TINY_DATASET=true
            shift
            ;;
        --ingest-raw-500-dataset)
            INGEST_RAW_500_DATASET=true
            shift
            ;;
        --instruqt)
            INSTRUQT_ONLY=true
            shift
            ;;
        --reingest-instruqt-with-endpoints)
            REINGEST_INSTRUQT_WITH_ENDPOINTS=true
            shift
            ;;
        -h|--help)
            show_usage
            exit 0
            ;;
        *)
            echo "Unknown option: $1"
            show_usage
            exit 1
            ;;
    esac
done

# Activate virtual environment
source venv/bin/activate

# Install/update requirements
echo "Installing/updating required packages..."
pip install -r requirements.txt

# Source environment variables
source ../env_config.sh

# Build the command with appropriate flags
CMD="python ingest-properties.py"

# Check which flags were specified and build the command accordingly
if [ "$SEARCHTEMPLATE_ONLY" = true ] || [ "$FULL_INGESTION_ONLY" = true ] || [ "$RECREATE_INDEX_ONLY" = true ]; then
    # At least one specific operation flag was specified, so we'll run specific operations
    echo "Running specified operations:"
    
    if [ "$SEARCHTEMPLATE_ONLY" = true ]; then
        echo "  - Search template creation"
        CMD="$CMD --searchtemplate"
    fi
    
    if [ "$FULL_INGESTION_ONLY" = true ]; then
        echo "  - Complete data ingestion pipeline"
        CMD="$CMD --full-ingestion"
    fi
    
    if [ "$RECREATE_INDEX_ONLY" = true ]; then
        echo "  - Recreate properties index"
        CMD="$CMD --recreate-index"
    fi
    
    if [ "$USE_SMALL_DATASET" = true ]; then
        echo "  - Use smaller dataset"
        CMD="$CMD --use-small-5k-dataset"
    fi
    
    if [ "$USE_TINY_DATASET" = true ]; then
        echo "  - Use tiny dataset"
        CMD="$CMD --use-500-dataset"
    fi
    
    if [ "$INGEST_RAW_500_DATASET" = true ]; then
        echo "  - Use raw index mapping with 500-line dataset"
        CMD="$CMD --ingest-raw-500-dataset"
    fi
    
    if [ "$INSTRUQT_ONLY" = true ]; then
        echo "  - Use Instruqt workshop settings"
        CMD="$CMD --instruqt"
    fi
    
    if [ "$REINGEST_INSTRUQT_WITH_ENDPOINTS" = true ]; then
        echo "  - Reingest Instruqt with endpoints"
        CMD="$CMD --reingest-instruqt-with-endpoints"
    fi
elif [ "$USE_SMALL_DATASET" = true ]; then
    # Only --use-small-5k-dataset was specified, run entire script with smaller dataset
    echo "Running complete property data ingestion with smaller dataset..."
    CMD="$CMD --use-small-5k-dataset"
    
    if [ "$INSTRUQT_ONLY" = true ]; then
        echo "  - Use Instruqt workshop settings"
        CMD="$CMD --instruqt"
    fi
    
    if [ "$REINGEST_INSTRUQT_WITH_ENDPOINTS" = true ]; then
        echo "  - Reingest Instruqt with endpoints"
        CMD="$CMD --reingest-instruqt-with-endpoints"
    fi
elif [ "$USE_TINY_DATASET" = true ]; then
    # Only --use-500-dataset was specified, run entire script with tiny dataset
    echo "Running complete property data ingestion with tiny dataset..."
    CMD="$CMD --use-500-dataset"
    
    if [ "$INSTRUQT_ONLY" = true ]; then
        echo "  - Use Instruqt workshop settings"
        CMD="$CMD --instruqt"
    fi
elif [ "$REINGEST_INSTRUQT_WITH_ENDPOINTS" = true ]; then
    # Only --reingest-instruqt-with-endpoints was specified
    echo "Running reingest Instruqt with endpoints operation..."
    CMD="$CMD --reingest-instruqt-with-endpoints"
elif [ "$INGEST_RAW_500_DATASET" = true ]; then
    # Only --ingest-raw-500-dataset was specified, run entire script with raw index mapping
    echo "Running complete property data ingestion with raw index mapping and 500-line dataset..."
    CMD="$CMD --ingest-raw-500-dataset"
    
    if [ "$INSTRUQT_ONLY" = true ]; then
        echo "  - Use Instruqt workshop settings"
        CMD="$CMD --instruqt"
    fi
elif [ "$INSTRUQT_ONLY" = true ]; then
    # Only --instruqt was specified, run entire script with Instruqt workshop settings
    echo "Running complete property data ingestion with Instruqt workshop settings..."
    CMD="$CMD --instruqt"
else
    echo "Running complete property data ingestion..."
fi

# Run the Python script with flags
$CMD

# Deactivate virtual environment
deactivate

echo "Operation complete!" 