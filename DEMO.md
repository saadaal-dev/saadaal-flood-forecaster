
# SETUP

## Historical river data

**WARNING**:
Exporting historical river data is a manual process.

It is possible to use data from the [Somalia National River Flow Archive (SNRFA)](https://snrfa.faoswalim.org/stations/) or the [Somalia Water and Land Information Management (SWALIM)](https://frrims.faoswalim.org/rivers/levels) websites.
The archive will be considered as the primary source of data, while the SWALIM website will be used as a secondary source to fill empty values when available.

The data is available on the [Somalia National River Flow Archive (SNRFA)](https://snrfa.faoswalim.org/stations/) website. You can download the data as CSV files for each station.
The data is avaible on the [Somalia Water and Land Information Management (SWALIM)](https://frrims.faoswalim.org/rivers/levels) website. You can download the data as CSV files for each station.

Import data from CSV files into the database

`python -m src.flood_forecaster_cli data-ingestion fetch-river-data-from-csv -a data/raw/SNRFA/snrfa_level_data-belet_weyne-20250621.csv -l data/raw/SWALIM/belet_weyne_river_levels_as_at_2025621_164528.csv "Belet Weyne"`

## Historical weather data

Import data from Open-Meteo API

`python -m src.flood_forecaster_cli data-ingestion fetch-openmeteo historical`


# EXECUTION

This step assumes that the database is already populated with historical river and weather data.
Here we want to fetch the latest data from the SWALIM API and Open-Meteo API, and then run the flood forecaster.

## Fetch current river data

Load the latest river data from SWALIM API (table on website)

`python -m src.flood_forecaster_cli data-ingestion fetch-river-data`

## Fetch weather data

Fetch forecast data from Open-Meteo API

`python -m src.flood_forecaster_cli data-ingestion fetch-openmeteo forecast`

## Run ML model to predict the river level in 7 days



# My demo

```bash
# Fetch river data from SNRFA and SWALIM CSV files for Dollow station
python -m src.flood_forecaster_cli data-ingestion fetch-river-data-from-csv -a data/raw/SNRFA/snrfa_level_data-dollow-20250621.csv -l data/raw/SWALIM/dollow_river_levels_as_at_2025621_155521.csv "Dollow"

# Fetch the latest weather data from Open-Meteo API
# WARNING: historical weather data might miss the latest value... (yesterday value)
python -m src.flood_forecaster_cli data-ingestion fetch-openmeteo forecast
python -m src.flood_forecaster_cli data-ingestion fetch-openmeteo historical

# Build the ML model
python -m src.flood_forecaster_cli ml build-model -f 7 -m Prophet_001 "Dollow"

# Run the ML model to predict the river level in 7 days
python -m src.flood_forecaster_cli ml infer -f 7 -m Prophet_001 -o database "Dollow"
# Alternative to output to STDOUT
# python -m src.flood_forecaster_cli ml infer -f 7 -m Prophet_001 "Dollow"

# Run the risk assessment on all unmarked predictions
python -m src.flood_forecaster_cli risk-assessment
```

# My demo 2

```bash
# Assuming SNRFA data has been manually downloaded and placed in data/raw/SNRFA/

# Specify the target station name
STATION="Dollow"

# Fetch the historical river data from SWALIM API for $STATION station
python -m src.flood_forecaster_cli data-ingestion fetch-river-data-from-chart-api "$STATION"

# Define target files for importing river data
SNRFA_FILE=$(python -m src.flood_forecaster_cli data-ingestion show-latest-snrfa-river-csv "$STATION" | tail -n 1)
echo "SNRFA file: $SNRFA_FILE"
SWALIM_FILE=$(python -m src.flood_forecaster_cli data-ingestion show-latest-swalim-river-csv "$STATION" | tail -n 1)
echo "SWALIM file: $SWALIM_FILE"

# Import river data from CSV files into the database
python -m src.flood_forecaster_cli data-ingestion fetch-river-data-from-csv -a "$SNRFA_FILE" -l "$SWALIM_FILE" "$STATION"
python -m src.flood_forecaster_cli data-ingestion fetch-river-data

# Fetch the latest weather data from Open-Meteo API
# WARNING: historical weather data might miss the latest value... (yesterday value)
python -m src.flood_forecaster_cli data-ingestion fetch-openmeteo forecast
python -m src.flood_forecaster_cli data-ingestion fetch-openmeteo historical

# QUICK FIX: remove duplicate historical weather data if any
python -m src.flood_forecaster_cli data-ingestion remove-duplicates-historical-weather

# Build the ML model
python -m src.flood_forecaster_cli ml build-model -f 7 -m Prophet_001 "$STATION"

# Run the ML model to predict the river level in 7 days and save to database so we can run risk assessment
python -m src.flood_forecaster_cli ml infer -f 7 -m Prophet_001 -o database "$STATION"

# Run the risk assessment on all unmarked predictions
python -m src.flood_forecaster_cli risk-assessment
```










# PI25.2 Innovation Demo

Goal of the demo is to show how to use the CLI to:
1. fetch the latest river and weather data
2. build a machine learning model
3. run inference to predict river levels in 7 days
4. run risk assessment

```bash
# Assuming historical river data has already been imported into the database
# Assuming historical weather data has already been imported into the database

STATION="Belet Weyne"

# Fetch the latest river data from SWALIM API (table on website)
python -m src.flood_forecaster_cli data-ingestion fetch-river-data

# Fetch the latest weather data from Open-Meteo API (prediction + historical)
python -m src.flood_forecaster_cli data-ingestion fetch-openmeteo forecast
python -m src.flood_forecaster_cli data-ingestion fetch-openmeteo historical

# Build the ML model
python -m src.flood_forecaster_cli ml build-model -f 7 -m Prophet_001 "$STATION"

# Run the ML model to predict the river level in 7 days and save to database so we can run risk assessment
python -m src.flood_forecaster_cli ml infer -f 7 -m Prophet_001 -o database "$STATION"

# Run the risk assessment on all unmarked predictions
python -m src.flood_forecaster_cli risk-assessment
```
