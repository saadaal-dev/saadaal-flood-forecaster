#!/bin/bash

set -e

REPOSITORY_ROOT_PATH=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )
echo "Working in repository root path: $REPOSITORY_ROOT_PATH"

# Check if REPOSITORY_ROOT_PATH exists
if [ ! -d "$REPOSITORY_ROOT_PATH" ]; then
    echo "The directory $REPOSITORY_ROOT_PATH does not exists."
    exit 1
fi

# Ensure the logs directory exists
LOGS_PATH="$REPOSITORY_ROOT_PATH/logs"
if [ ! -d "$LOGS_PATH" ]; then
    echo "The logs directory does not exist. Creating it."
    mkdir -p "$LOGS_PATH"
fi

# The virtual environment path
VENV_PATH=$REPOSITORY_ROOT_PATH/.venv

# Check if venv directory exists
if [ ! -d "$VENV_PATH" ]; then
    echo "The virtual environment directory does not exist. Creating it."
    python3.10 -m venv "$VENV_PATH"
fi

# Activate the virtual environment for package installation
source "$VENV_PATH"/bin/activate
echo "Virtual environment activated $VIRTUAL_ENV"

# Install the required packages
pip3 install -r $REPOSITORY_ROOT_PATH/requirements.txt

# Ensure the script is executable
chmod +x "$REPOSITORY_ROOT_PATH"/scripts/amadeus_saadaal_flood_forecaster.sh