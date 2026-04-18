#!/bin/bash
set -e

# Add current directory to PYTHONPATH so imports work
export PYTHONPATH="${PYTHONPATH}:/app"

# Seed database if it doesn't exist or is empty
python data/seed.py

# Start the MCP server
python src/main.py
