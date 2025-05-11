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
echo "1. Activate the virtual environment:"
echo "   source venv/bin/activate"
echo ""
echo "2. Run the ingestion script:"
echo "   python ingest-properties.py"
echo ""
echo "3. When you're done, deactivate the virtual environment:"
echo "   deactivate" 