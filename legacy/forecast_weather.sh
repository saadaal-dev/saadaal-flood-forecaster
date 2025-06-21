#!/bin/bash

SCRIPT_DIR=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )

BASE_PATH="$SCRIPT_DIR/.."

source $BASE_PATH/data-extractor-venv/bin/activate

cd $BASE_PATH/openmeteo
python3 forecast_weather.py