#!/bin/bash

BASE_PATH=/root/workv2

cd $BASE_PATH/data-extractor-venv
source bin/activate

cd $BASE_PATH/openmeteo
python3 forecast_weather.py