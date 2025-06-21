#!/bin/bash

# Function to display usage
show_usage() {
    echo "Usage: $0 [OPTIONS]"
    echo ""
    echo "Options:"
    echo "  --searchtemplate    Run the search template creation part"
    echo "  --full-ingestion    Run the complete data ingestion pipeline (create indices, download data, process with ELSER)"
    echo "  --reindex           Run the reindex operation (requires existing raw index)"
    echo "  --recreate-index    Delete and recreate the properties index (no data processing)"
    echo "  -h, --help          Show this help message"
    echo ""
    echo "Multiple flags can be combined to run specific operations."
    echo "If no flags are provided, the entire script will run."
    echo ""
    echo "Examples:"
    echo "  $0                    # Run entire script"
    echo "  $0 --searchtemplate   # Only create search templates"
    echo "  $0 --full-ingestion   # Run complete data ingestion pipeline"
    echo "  $0 --reindex          # Only reindex (requires raw index to exist)"
    echo "  $0 --recreate-index   # Delete and recreate properties index"
    echo "  $0 --searchtemplate --full-ingestion  # Create search templates and run ingestion"
    echo "  $0 --full-ingestion --reindex         # Run ingestion and reindex"
}

# Parse command line arguments
SEARCHTEMPLATE_ONLY=false
FULL_INGESTION_ONLY=false
REINDEX_ONLY=false
RECREATE_INDEX_ONLY=false

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
        --reindex)
            REINDEX_ONLY=true
            shift
            ;;
        --recreate-index)
            RECREATE_INDEX_ONLY=true
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

# Source environment variables
source ../env_config.sh

# Build the command with appropriate flags
CMD="python ingest-properties.py"

# Check which flags were specified and build the command accordingly
if [ "$SEARCHTEMPLATE_ONLY" = true ] || [ "$FULL_INGESTION_ONLY" = true ] || [ "$REINDEX_ONLY" = true ] || [ "$RECREATE_INDEX_ONLY" = true ]; then
    # At least one flag was specified, so we'll run specific operations
    echo "Running specified operations:"
    
    if [ "$SEARCHTEMPLATE_ONLY" = true ]; then
        echo "  - Search template creation"
        CMD="$CMD --searchtemplate"
    fi
    
    if [ "$FULL_INGESTION_ONLY" = true ]; then
        echo "  - Complete data ingestion pipeline"
        CMD="$CMD --full-ingestion"
    fi
    
    if [ "$REINDEX_ONLY" = true ]; then
        echo "  - Reindex operation"
        CMD="$CMD --reindex"
    fi
    
    if [ "$RECREATE_INDEX_ONLY" = true ]; then
        echo "  - Recreate properties index"
        CMD="$CMD --recreate-index"
    fi
else
    echo "Running complete property data ingestion..."
fi

# Run the Python script with flags
$CMD

# Get the current timestamp
TIMESTAMP=$(date "+%Y-%m-%d %H:%M:%S")

# Update README.md with execution information
if [ "$SEARCHTEMPLATE_ONLY" = true ] && [ "$FULL_INGESTION_ONLY" = false ] && [ "$REINDEX_ONLY" = false ] && [ "$RECREATE_INDEX_ONLY" = false ]; then
    echo -e "\n## Last Search Template Creation\nLast run: $TIMESTAMP" >> README.md
elif [ "$FULL_INGESTION_ONLY" = true ] && [ "$SEARCHTEMPLATE_ONLY" = false ] && [ "$REINDEX_ONLY" = false ] && [ "$RECREATE_INDEX_ONLY" = false ]; then
    echo -e "\n## Last Complete Data Ingestion\nLast run: $TIMESTAMP" >> README.md
elif [ "$REINDEX_ONLY" = true ] && [ "$SEARCHTEMPLATE_ONLY" = false ] && [ "$FULL_INGESTION_ONLY" = false ] && [ "$RECREATE_INDEX_ONLY" = false ]; then
    echo -e "\n## Last Reindex Operation\nLast run: $TIMESTAMP" >> README.md
elif [ "$RECREATE_INDEX_ONLY" = true ] && [ "$SEARCHTEMPLATE_ONLY" = false ] && [ "$FULL_INGESTION_ONLY" = false ] && [ "$REINDEX_ONLY" = false ]; then
    echo -e "\n## Last Recreate Properties Index\nLast run: $TIMESTAMP" >> README.md
elif [ "$SEARCHTEMPLATE_ONLY" = true ] || [ "$FULL_INGESTION_ONLY" = true ] || [ "$REINDEX_ONLY" = true ] || [ "$RECREATE_INDEX_ONLY" = true ]; then
    echo -e "\n## Last Partial Execution\nLast run: $TIMESTAMP" >> README.md
    echo "Operations run:" >> README.md
    if [ "$SEARCHTEMPLATE_ONLY" = true ]; then 
        echo "  - Search template creation" >> README.md
    fi
    if [ "$FULL_INGESTION_ONLY" = true ]; then 
        echo "  - Complete data ingestion pipeline" >> README.md
    fi
    if [ "$REINDEX_ONLY" = true ]; then 
        echo "  - Reindex operation" >> README.md
    fi
    if [ "$RECREATE_INDEX_ONLY" = true ]; then 
        echo "  - Recreate properties index" >> README.md
    fi
else
    echo -e "\n## Last Full Execution\nLast run: $TIMESTAMP" >> README.md
fi

# Deactivate virtual environment
deactivate

echo "Operation complete! README.md has been updated with execution timestamp." 