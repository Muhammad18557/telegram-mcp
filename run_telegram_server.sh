#!/bin/bash

# Define the base directory and environment path
BASE_DIR="/Users/muhammadabdullah/Desktop/mcp/telegram-mcp"
ENV_PATH="$BASE_DIR/myenv"

# Check if the virtual environment exists
if [ ! -d "$ENV_PATH" ]; then
  python3 -m venv "$ENV_PATH"
  source "$ENV_PATH/bin/activate"
  pip install -r "$BASE_DIR/requirements.txt" > /dev/null 2>&1
else
  source "$ENV_PATH/bin/activate"
fi

# Run the MCP server
python "$BASE_DIR/telegram-mcp-server/main.py"