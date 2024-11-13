#!/bin/bash

set -e
# This script prepares the environment for running the python scripts
# to execute 

# The base path is the root of the project
# Script to be executed from the root of the project
# with bash install/install.sh

SCRIPT_DIR=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )

BASE_PATH="$SCRIPT_DIR/.."

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

echo "Virtual environment activated at: $VENV_PATH with $VIRTUAL_ENV"	

# Install the required packages
pip3 install -r $SCRIPT_DIR/../openmeteo/requirements.txt
pip3 install -r $SCRIPT_DIR/../data-extractor/requirements.txt