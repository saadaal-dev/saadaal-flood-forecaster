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
    python3 -m venv "$VENV_PATH"
fi

# Activate the virtual environment for package installation
echo "Activating virtual environment..."
if [ -f "$VENV_PATH/bin/activate" ]; then
    source "$VENV_PATH/bin/activate"
elif [ -f "$VENV_PATH/Scripts/activate" ]; then
    source "$VENV_PATH/Scripts/activate"
else
    echo "Could not find activation script in $VENV_PATH"
    exit 1
fi
echo "Virtual environment activated $VIRTUAL_ENV"



# Clean up any previous builds
echo "Cleaning up previous builds..."
rm -rf $REPOSITORY_ROOT_PATH/build/
rm -rf $REPOSITORY_ROOT_PATH/*.egg-info/

# Install the flood forecaster package in editable mode
echo "Installing flood-forecaster package in editable mode..."
pip3 install -e $REPOSITORY_ROOT_PATH

# Ensure the script is executable
chmod +x "$REPOSITORY_ROOT_PATH"/scripts/amadeus_saadaal_flood_forecaster.sh

echo "Installation completed successfully!"
echo "To use the CLI, activate the virtual environment first:"
echo "  source .venv/bin/activate"
echo "Then try: flood-cli --help"
