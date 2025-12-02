"""
Data ingestion Commands
"""

from typing import Optional
import click

from flood_forecaster.utils.configuration import Config

from flood_forecaster_cli.commands.common import common_options, create_openmeteo_client
from flood_forecaster.data_ingestion.openmeteo.historical_weather import fetch_historical
from flood_forecaster.data_ingestion.openmeteo.forecast_weather import fetch_forecast


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
@click.argument("type", type=click.Choice(["forecast", "historical"]), required=True)
@click.option('-e', '--empty-table', is_flag=True, help="If set, the table will be emptied before inserting new data")
@click.option('--dry-run', is_flag=True, help="If set, only prints the duplicates without deleting them. See [HOTFIX-DUPLICATES-HISTORICAL-WEATHER].")
@common_options
def fetch_openmeteo(configuration: Config, type: str, empty_table: bool = False, dry_run: bool = False):
    """
    Fetch weather data from Open-Meteo API.

    USAGE:
    flood_forecaster_cli data_ingestion fetch-openmeteo [forecast|historical] [--configfile <path>]

    :param configuration: Configuration object containing settings.
    :param type: Type of data to fetch, either 'forecast' or 'historical'.
    """
    click.echo(f"Fetching {type} data from Open-Meteo API...")

    openmeteo = create_openmeteo_client()

    if type == "forecast":
        fetch_forecast(configuration, openmeteo)
    else:
        fetch_historical(configuration, openmeteo)
        
        # INTERNAL: Remove duplicate historical weather entries from the database
        #           This is a quick fix to remove duplicates from the database
        #           [HOTFIX-DUPLICATES-HISTORICAL-WEATHER]
        from flood_forecaster.data_ingestion.openmeteo.historical_weather import remove_duplicates_historical_weather_from_db
        remove_duplicates_historical_weather_from_db(configuration, dry_run=dry_run)


@data_ingestion.command("fetch-river-data", help="Fetch river levels from SWALIM API")
@common_options
def fetch_river_data(configuration: Config):
    """
    Fetch river level data from SWALIM API.

    USAGE:
    flood_forecaster_cli data_ingestion fetch-river-data [--configfile <path>]

    :param configuration: Configuration object containing settings.
    """
    click.echo("Fetching river data from SWALIM API...")
    from flood_forecaster.data_ingestion.swalim.river_level_api import fetch_latest_river_data, insert_river_data
    historical_river_levels = fetch_latest_river_data(configuration)

    if historical_river_levels:
        new_river_levels_count = insert_river_data(historical_river_levels, configuration, avoid_duplicates=True)
        print(f"Inserted {new_river_levels_count} river levels into the database.")
    else:
        click.echo("No new river data fetched.")


@data_ingestion.command("fetch-river-data-from-csv", help="Fetch river levels from CSV file (SNRFA and SWALIM exports)")
@click.argument('location_name', type=str, required=True)
@click.option('--snrfa-file', '-a', type=click.Path(exists=True), help="Path to the SNRFA CSV file (archive).")
@click.option('--swalim-file', '-l', type=click.Path(exists=True), help="Path to the SWALIM CSV file (live portal).")
@common_options
def fetch_river_data_from_csv(configuration: Config, location_name: str, snrfa_file: Optional[str] = None, swalim_file: Optional[str] = None):
    """
    Fetch river level data from CSV files (SNRFA and SWALIM exports).

    SNRFA: Somali National River Flow Archive, which contains historical river level data. URL: https://snrfa.so/rivers/levels
    SWALIM: FAO-SWALIM (Somalia Water and Land Information Management) provides recent river level data. URL: https://frrims.faoswalim.org/rivers/levels

    USAGE:
    flood_forecaster_cli data_ingestion fetch-river-data-from-csv [--snrfa-file <path>] [--swalim-file <path>] [--configfile <path>] <location_name>

    :param location_name: Name of the river location to fetch data for.
    :param snrfa_file: Path to the SNRFA CSV file.
    :param swalim_file: Path to the SWALIM CSV file.
    :param configuration: Configuration object containing settings.
    """
    from flood_forecaster.data_ingestion.swalim.river_level_api import load_river_data_from_csvs
    load_river_data_from_csvs(configuration, location_name, snrfa_file, swalim_file)


@data_ingestion.command("fetch-river-data-from-chart-api", help="Fetch river levels from SWALIM API")
@click.argument('location_name', type=str, required=True)
@click.option('-o', '--output', type=click.Path(), help="Output file path to save the fetched data in CSV format.")
@common_options
def fetch_river_data_from_chart_api(configuration: Config, location_name: str, output: Optional[str] = None):
    """
    Fetch river level data from SWALIM API for a specific location (chart API).

    USAGE:
    flood_forecaster_cli data_ingestion fetch-river-data-from-api <location_name> [--configfile <path>]

    :param location_name: Name of the river location to fetch data for.
    :param configuration: Configuration object containing settings.
    """
    if not output:
        # default output file name in format <location_name>_river_levels_as_at_<date>_<time>.csv
        # location name (lowercase with spaces replaced by underscores),
        # date and time in format YYYYMMDD_HHMMSS
        import datetime
        swalim_raw_data_dir = configuration.load_data_csv_config()["swalim_raw_data_dir"]
        if not swalim_raw_data_dir.endswith('/'):
            swalim_raw_data_dir += '/'
        output = f"{swalim_raw_data_dir}{location_name.lower().replace(' ', '_')}_river_levels_as_at_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"

    from flood_forecaster.data_ingestion.swalim.river_level_api import fetch_river_data_from_chart_api
    river_levels = fetch_river_data_from_chart_api(configuration, location_name)
    if not river_levels.empty:
        click.echo(f"Fetched {len(river_levels)} river levels for {location_name}.")
        river_levels.to_csv(output, index=False)
        click.echo(f"Data saved to {output}.")
    else:
        click.echo(f"No river data found for {location_name}.")


@data_ingestion.command("show-latest-swalim-river-csv", help="Get the latest SWALIM river levels CSV file (printed to console)")
@click.argument('location_name', type=str, required=True)
@common_options
def show_latest_swalim_river_csv(configuration: Config, location_name: str):
    """
    Get the latest SWALIM river levels CSV file for a specific location.

    USAGE:
    flood_forecaster_cli data_ingestion show-latest-swalim-river-csv <location_name> [--configfile <path>]

    :param location_name: Name of the river location to fetch data for.
    :param configuration: Configuration object containing settings.
    """
    from flood_forecaster.data_ingestion.swalim.river_level_api import get_latest_swalim_river_csv
    csv_content = get_latest_swalim_river_csv(configuration, location_name)
    click.echo(csv_content)


@data_ingestion.command("show-latest-snrfa-river-csv", help="Get the latest SNRFA river levels CSV file (printed to console)")
@click.argument('location_name', type=str, required=True)
@common_options
def show_latest_snrfa_river_csv(configuration: Config, location_name: str):
    """
    Get the latest SNRFA river levels CSV file for a specific location.

    USAGE:
    flood_forecaster_cli data_ingestion show-latest-snrfa-river-csv <location_name> [--configfile <path>]

    :param location_name: Name of the river location to fetch data for.
    :param configuration: Configuration object containing settings.
    """
    from flood_forecaster.data_ingestion.swalim.river_level_api import get_latest_snrfa_river_csv
    csv_content = get_latest_snrfa_river_csv(configuration, location_name)
    click.echo(csv_content)


# INTERNAL: Remove duplicate historical weather entries from the database
#           This is a quick fix to remove duplicates from the database
#           [HOTFIX-DUPLICATES-HISTORICAL-WEATHER]
@data_ingestion.command("remove-duplicates-historical-weather", help="INTERNAL: Remove duplicate historical weather entries from the database")
@click.option('--dry-run', is_flag=True, help="If set, only prints the duplicates without deleting them.")
@common_options
def remove_duplicates_historical_weather(configuration: Config, dry_run: bool = True):
    """
    Remove duplicate historical weather entries from the database based on date and location.
    This command checks for duplicate entries and removes them if found.
    :param configuration: Configuration object containing settings.
    :param dry_run: If True, only prints the duplicates without deleting them.
    """
    from flood_forecaster.data_ingestion.openmeteo.historical_weather import remove_duplicates_historical_weather_from_db
    remove_duplicates_historical_weather_from_db(configuration, dry_run=dry_run)
