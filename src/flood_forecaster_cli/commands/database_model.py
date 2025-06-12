"""
Data modelling Commands
"""

import click
from src.flood_forecaster.utils.configuration import Config
from src.flood_forecaster.utils.database_helper import DatabaseConnection

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
