"""
Data modelling Commands
"""

from datetime import datetime

import click
import pandas as pd
from flood_forecaster.data_ingestion.load import load_history_weather_db, load_sensor_rainfall_db
from flood_forecaster.utils.configuration import Config
from flood_forecaster.utils.geo import build_sensor_location_mapping
from flood_forecaster.utils.database_helper import DatabaseConnection
from .common import common_options


@click.group
def database_model():
    """
    Manage Database Schema Operations
    """


@database_model.command("list-db-schemas", help="List all schemas from given database")
@common_options
def list_db_schemas(
    configuration: Config
):
    # Initialize database connection
    db_conn = DatabaseConnection(configuration)

    schemas = db_conn.list_all_schemas()

    # Print list of schemas
    click.echo("Schemas in the database:")
    for schema in schemas:
        click.echo(f"- {schema}")


@database_model.command("list-tables-from-schema", help="List all tables from given schema")
@click.option("--schema-name", "-s", required=True, help="Schema name")
@common_options
def list_tables_from_schema(
    configuration: Config, schema_name: str
):
    # Initialize database connection
    db_conn = DatabaseConnection(configuration)
    # List all tables from a given schema
    tables = db_conn.list_tables(schema_name)
    click.echo(f"Tables in schema {schema_name}:")
    for table, columns in tables:
        click.echo(f"Table: {table}")
        for column in columns:
            click.echo(f"  Column: {column['name']} | Type: {column['type']}")


@database_model.command("fetch-table-to-csv", help="Fetch table data to CSV")
@click.option("--schema-name", "-s", required=True, help="Schema name")
@click.option("--table-name", "-t", required=True, help="Table name")
@click.option("--data-download-path", "-d", required=True, help="Data download path")
@click.option("--force-overwrite", is_flag=True, default=False, help="Overwrite if file exists")
@click.option("--preview-rows", "-p", default=20, help="Number of rows to pretty-print in the console")
@click.option("--where", "-w", help="Optional WHERE clause, like 'sensor_meaning LIKE ''%Rainfall%'''")
@common_options
def fetch_table_to_csv(
    configuration: Config, schema_name: str, table_name: str, data_download_path: str, force_overwrite: bool, preview_rows: int, where: str | None,
):
    # Initialize database connection
    db_conn = DatabaseConnection(configuration)
    # Fetch table data and write to CSV
    db_conn.fetch_table_to_csv(schema_name, table_name, data_download_path, force_overwrite, preview_rows, where)


@database_model.command("validate-sensor-readings", help="Validate table data")
@click.option("--schema-name", "-s", default="public", help="Schema name")
@click.option("--table-name", "-t", default="sensor_readings", help="Table name")
@common_options
def validate_sensor_readings(configuration: Config, schema_name: str, table_name: str):
    db_conn = DatabaseConnection(configuration)
    db_conn.validate_sensor_readings(schema_name, table_name)


@database_model.command("validate-table-data", help="Validate table data")
@click.option("--schema-name", "-s", default="public", help="Schema name")
@click.option("--table-name", "-t", default="sensor_readings", help="Table name")
@common_options
def validate_table_data(configuration: Config, schema_name: str, table_name: str):
    db_conn = DatabaseConnection(configuration)
    issues = db_conn.validate_table_data(schema_name, table_name)
    print("\nValidation issues:", issues)


@database_model.command(
    "compare-sensor-weather",
    help=(
        "Compare IoT sensor rainfall (public.sensor_readings) against Open-Meteo "
        "historical precipitation for a given location and date range. "
        "Prints a side-by-side table of sensor_precip_mm vs openmeteo_precip_mm "
        "with delta_mm, and optionally saves the result to CSV.\n\n"
        "Example:\n\n"
        "  flood-cli database-model compare-sensor-weather \\\n"
        "    --location bay__baydhaba \\\n"
        "    --date-from 2025-01-01 --date-to 2025-01-31"
    ),
)
@click.option(
    "--location", "-l",
    required=True,
    multiple=True,
    help="Pipeline location label (repeatable). E.g. --location bay__baydhaba",
)
@click.option(
    "--date-from",
    required=True,
    type=click.DateTime(formats=["%Y-%m-%d"]),
    help="Start date (inclusive), format YYYY-MM-DD",
)
@click.option(
    "--date-to",
    required=True,
    type=click.DateTime(formats=["%Y-%m-%d"]),
    help="End date (inclusive), format YYYY-MM-DD",
)
@click.option(
    "--output", "-o",
    default=None,
    type=click.Path(),
    help="Optional path to save the comparison as CSV",
)
@common_options
def compare_sensor_weather(
    configuration: Config,
    location: tuple,
    date_from: datetime,
    date_to: datetime,
    output: str | None,
):
    d_from = date_from.date()
    d_to = date_to.date()

    # Resolve any sensor station labels (e.g. "Elbarde") to pipeline forecast location labels
    # (e.g. "bakool__ceel_barde") so that both loaders receive consistent location keys.
    sensor_config = configuration.load_sensor_config()
    static_config = configuration.load_static_data_config()
    station_to_location = build_sensor_location_mapping(
        sensor_config["sensor_stations_file"],
        static_config["weather_location_data_path"],
        max_distance_km=float(sensor_config.get("sensor_max_distance_km", 50)),
    )
    locations = []
    for loc in location:
        if loc in station_to_location:
            mapped = station_to_location[loc]
            print(f"Resolved sensor station '{loc}' → forecast location '{mapped}'")
            locations.append(mapped)
        else:
            locations.append(loc)
    # Deduplicate while preserving order (two stations can map to the same forecast location)
    seen: set = set()
    locations = [loc for loc in locations if not (loc in seen or seen.add(loc))]  # type: ignore[func-returns-value]

    print(f"Loading sensor rainfall for {locations} from {d_from} to {d_to}...")
    sensor_df = load_sensor_rainfall_db(configuration, locations, d_from, d_to)

    print(f"Loading Open-Meteo historical weather for {locations} from {d_from} to {d_to}...")
    weather_df = load_history_weather_db(configuration, locations, d_from, d_to)

    sensor_df["date"] = pd.to_datetime(sensor_df["date"])
    weather_df["date"] = pd.to_datetime(weather_df["date"])

    merged = (
        sensor_df.rename(columns={"precipitation_sum": "sensor_precip_mm", "precipitation_hours": "sensor_hours"})
        .merge(
            weather_df.rename(columns={"precipitation_sum": "openmeteo_precip_mm", "precipitation_hours": "openmeteo_hours"}),
            on=["location", "date"],
            how="outer",
        )
        .sort_values(["location", "date"])
        .reset_index(drop=True)
    )
    merged["delta_mm"] = merged["sensor_precip_mm"] - merged["openmeteo_precip_mm"]

    _W = 80
    print(f"\n{'─' * _W}")
    print(f"{'location':<25} {'date':<12} {'sensor_precip_mm':>18} {'openmeteo_precip_mm':>20} {'delta_mm':>10}")
    print(f"{'─' * _W}")
    for _, row in merged.iterrows():
        s = f"{row['sensor_precip_mm']:.2f}" if pd.notna(row.get("sensor_precip_mm")) else "N/A"
        w = f"{row['openmeteo_precip_mm']:.2f}" if pd.notna(row.get("openmeteo_precip_mm")) else "N/A"
        d = f"{row['delta_mm']:.2f}" if pd.notna(row.get("delta_mm")) else "N/A"
        print(f"{str(row['location']):<25} {str(row['date'].date()):<12} {s:>18} {w:>20} {d:>10}")
    print(f"{'─' * _W}")
    sensor_count = int((~merged["sensor_precip_mm"].isna()).sum())
    weather_count = int((~merged["openmeteo_precip_mm"].isna()).sum())
    print(f"{len(merged)} rows | {sensor_count} sensor, {weather_count} Open-Meteo")

    if output:
        merged.to_csv(output, index=False)
        print(f"\nSaved comparison to {output}")
