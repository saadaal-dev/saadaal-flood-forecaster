#!/bin/bash

set -e
# This script prepares the environment for running the python scripts
# to execute 

# The base path is the root of the project
# Script to be executed from the root of the project
# with bash install/install.sh

REPOSITORY_ROOT_PATH=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )

# Check if REPOSITORY_ROOT_PATH exists
if [ ! -d "$REPOSITORY_ROOT_PATH" ]; then
    echo "The directory $REPOSITORY_ROOT_PATH does not exists."
    exit 1
fi

# The virtual environment path
VENV_PATH=$REPOSITORY_ROOT_PATH/venv

# Check if venv directory exists
if [ ! -d "$VENV_PATH" ]; then
    echo "The virtual environment directory does not exist. Creating it."
    python3 -m venv $VENV_PATH    
fi

# Activate the virtual environment
source $VENV_PATH/bin/activate

echo "Virtual environment activated at: $VENV_PATH with $VIRTUAL_ENV"	

# Install the required packages
pip3 install -r $REPOSITORY_ROOT_PATH/requirements.txt

# Create the CRON job to run every day at 07:00
CRON_JOB="0 7 * * *  ./$REPOSITORY_ROOT_PATH/scripts/amadeus_saadal_flood_forecaster.sh"