"""
Data modelling Commands
"""

import click
from flood_forecaster.utils.configuration import Config
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
    print("Schemas in the database:")
    for schema in schemas:
        print(f"- {schema}")


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
    print(f"Tables in schema {schema_name}:")
    for table, columns in tables:
        print(f"Table: {table}")
        for column in columns:
            print(f"  Column: {column['name']} | Type: {column['type']}")


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
    issues = db_conn.validate_sensor_readings(schema_name, table_name)
    print("\nValidation issues:", issues)


@database_model.command("validate-table-data", help="Validate table data")
@click.option("--schema-name", "-s", default="public", help="Schema name")
@click.option("--table-name", "-t", default="sensor_readings", help="Table name")
@common_options
def validate_table_data(configuration: Config, schema_name: str, table_name: str):
    db_conn = DatabaseConnection(configuration)
    issues = db_conn.validate_table_data(schema_name, table_name)
    print("\nValidation issues:", issues)
