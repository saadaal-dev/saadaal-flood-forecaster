#!/bin/bash

set -e
# This script prepares the environment for running the python scripts
# to execute 

# Database configuration
DB_NAME="postgres"
DB_USER="postgres"
DB_HOST="68.183.13.232"
DB_PORT="5432"

# Get the database password from environment variable
if [ -z "$POSTGRES_PASSWORD" ]; then
    echo "Error: POSTGRES_PASSWORD environment variable is not set."
    exit 1
fi
export PGPASSWORD="$POSTGRES_PASSWORD"

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
pip3 install -r $BASE_PATH/requirements.txt


# Check if database exists
if psql -U "$DB_USER" -h "$DB_HOST" -p "$DB_PORT" -lqt | cut -d \| -f 1 | grep -qw "$DB_NAME"; then
    echo "Database $DB_NAME already exists."
else
    echo "Database $DB_NAME does not exist. Creating it..."
    createdb -U "$DB_USER" -h "$DB_HOST" -p "$DB_PORT" "$DB_NAME"
    echo "Database $DB_NAME created."
fi