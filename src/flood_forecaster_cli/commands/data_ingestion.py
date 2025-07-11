"""
Data ingestion Commands
"""

import click
import openmeteo_requests
import requests_cache
from retry_requests import retry

from src.flood_forecaster.data_ingestion.openmeteo.forecast_weather import fetch_forecast
from src.flood_forecaster.data_ingestion.openmeteo.historical_weather import fetch_historical
from src.flood_forecaster.data_ingestion.swalim.river_level_api import fetch_latest_river_data, insert_river_data
from src.flood_forecaster.utils.configuration import Config
from .common import common_options


# Group for Data Ingestion Operations
@click.group()
def data_ingestion():
    """
    Commands for data ingestion
    """


@data_ingestion.command("fetch-river-data", help="Fetch river levels from Swalim data source")
@common_options
def fetch_river_data(configuration: Config):
    river_levels = fetch_latest_river_data(configuration)
    insert_river_data(river_levels, configuration)


@data_ingestion.command("fetch-openmeteo", help="Fetch data from Open-Meteo API")
@click.option("--type", "-t", type=click.Choice(["forecast", "historical"]), required=True,
              help="Type of data to fetch: forecast or historical")
@common_options
def fetch_openmeteo(configuration: Config, type: str):
    """Fetch weather data from Open-Meteo API."""
    # Set up the Open-Meteo API client with cache and retry on error
    cache_session = requests_cache.CachedSession(".cache", expire_after=-1)
    retry_session = retry(cache_session, retries=5, backoff_factor=0.2)
    openmeteo = openmeteo_requests.Client(session=retry_session)

    if type == "forecast":
        fetch_forecast(configuration, openmeteo)
    else:
        # TODO add parameter to specify the date range for historical data
        fetch_historical(configuration, openmeteo)


@data_ingestion.command("load-csv", help="Load data from csv file to db schema.table")
@click.option("--file_path", "-f", required=True, help="Path to file")
@click.option('--schema', '-s', required=True, help='Target database schema.')
@click.option('--table', '-t', required=True, help='Target database table.')
@common_options
def load_csv(configuration: Config, file_path: str, schema_name: str, table_name: str):
    """Load a CSV file into the database."""
    click.echo(
        f"Place holder for sample data ingestion cmd to load from CSV to {schema_name}.{table_name}- not yet implemented.")
    # ToDO: Implement CSV loading logic
