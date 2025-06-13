
"""
Data ingestion Commands
"""

import click
from src.flood_forecaster.utils.configuration import Config
# from flood_forecaster.utils.database_helper import DatabaseConnection

from .common import common_options
from src.flood_forecaster.data_ingestion.openmeteo.common import fetch_forecast,fetch_historical


# Group for Data Ingestion Operations
@click.group()
def data_ingestion():
    """
    Commands for data ingestion
    """


@data_ingestion.command("load-csv", help="Load data from csv file to db schema.table")
@click.option("--file_path", "-f", required=True, help="Path to file")
@click.option('--schema', '-s', required=True, help='Target database schema.')
@click.option('--table', '-t', required=True, help='Target database table.')
@common_options
def load_csv(configuration: Config, file_path: str, schema_name: str, table_name: str):
    """Load a CSV file into the database."""
    click.echo(f"Place holder for sample data ingestion cmd to load from CSV to {schema_name}.{table_name}- not yet implemented.")
    # ToDO: Implement CSV loading logic




@data_ingestion.command("fetch-openmeteo", help="Fetch data from Open-Meteo API")
@click.option("--type", "-t", type=click.Choice(["forecast", "historical"]), required=True, help="Type of data to fetch: forecast or historical")
@common_options
def fetch_openmeteo(configuration: Config, type: str):
    """Fetch weather data from Open-Meteo API."""
    if type == "forecast":
        result = fetch_forecast(configuration)
    else:
        result = fetch_historical(configuration)
    click.echo(f"Fetched data: {result}")