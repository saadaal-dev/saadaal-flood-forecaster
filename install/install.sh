#!/bin/bash

set -e
# This script prepares the environment for running the python scripts

# The base path is the root of the project
# Set first arg as BASE_PATH if exists else default to /root/workv2
BASE_PATH="${1:-/root/workv2}"

# Check if BASE_PATH exists
if [ ! -d "$BASE_PATH" ]; then
    echo "The directory $BASE_PATH does not exists."
    exit 1
fi

# The virtual environment path
VENV_PATH=$BASE_PATH/data-extractor-venv

# Install virtual env
# apt install python3.8-venv

# Check if venv directory exists
if [ ! -d "$VENV_PATH" ]; then
    echo "The virtual environment directory does not exist. Creating it."
    python3 -m venv $VENV_PATH    
fi

# Activate the virtual environment
source $VENV_PATH/bin/activate

# Install the required packages
pip3 install -r ../openmeteo/requirements.txt
pip3 install -r ../data-extractor/requirements.txt