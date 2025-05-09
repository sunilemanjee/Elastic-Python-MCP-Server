#!/bin/bash

# Create Python virtual environment for the MCP server
python3 -m venv venv

# Activate virtual environment
source venv/bin/activate

# Upgrade pip to latest version
pip install --upgrade pip

# Install required Python dependencies
pip install -r requirements.txt

echo "Virtual environment setup complete!"
echo "To activate the virtual environment, run: source venv/bin/activate"
echo "To start the server, run: ./run_server.sh" 