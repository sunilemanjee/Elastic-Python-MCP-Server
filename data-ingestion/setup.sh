#!/bin/bash

# Create virtual environment if it doesn't exist
if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv venv
fi

# Activate virtual environment
source venv/bin/activate

# Upgrade pip
pip install --upgrade pip

# Install requirements
echo "Installing requirements..."
pip install -r requirements.txt

# Source the environment variables from parent directory
if [ -f "../env_config.sh" ]; then
    echo "Sourcing environment variables from parent directory..."
    source ../env_config.sh
else
    echo "Warning: env_config.sh not found in parent directory"
    echo "Please create it by copying env_config.template.sh and adding your credentials"
fi

echo "✅ Setup complete!"
echo ""
echo "To start using the script:"
echo "1. Run the ingestion script with options:"
echo "   ./run-ingestion.sh                    # Run everything (default)"
echo "   ./run-ingestion.sh --full-ingestion   # Complete pipeline"
echo "   ./run-ingestion.sh --searchtemplate   # Only create search templates"
echo "   ./run-ingestion.sh --reindex          # Only reindex (requires raw index)"
echo "   ./run-ingestion.sh --use-small-5k-dataset # Use smaller dataset"
echo "   ./run-ingestion.sh --use-500-dataset  # Use tiny dataset"
echo "   ./run-ingestion.sh --instruqt         # Use Instruqt workshop settings"
echo ""
echo "2. For help and all available options:"
echo "   ./run-ingestion.sh --help"
echo ""
echo "3. The script automatically handles virtual environment activation/deactivation" 