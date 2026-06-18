#!/bin/bash

# Recreate the python virtual environment and reinstall libs on macOS/linux.
# Chris Joakim, 2026

echo "Prune/ensure directories..." # legacy directory 
rm -rf .venv
rm -rf .coverage
rm -rf .pytest_cache
rm -rf htmlcov
mkdir -p out 
mkdir -p tmp 

echo "Creating a new virtual environment in .venv ..."
uv venv

echo "Activating the virtual environment ..."
source .venv/bin/activate

echo "Installing libraries ..."
uv pip install --editable .

echo "Listing the installed libraries ..."
uv pip list
