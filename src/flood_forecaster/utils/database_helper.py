import importlib
import os
import pkgutil

import pandas as pd
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.engine import URL
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.schema import CreateSchema

from src.flood_forecaster.utils.configuration import Config


class DatabaseConnection:
    def __init__(self, config: Config, db_password: str = None) -> None:
        """
        Initialize the database connection using parameters from a config file.

        :param config: Config object
        """
        config = config.load_data_database_config()
        self.dbname = config.get("dbname")
        self.user = config.get("user")
        self.host = config.get("host")
        self.port = int(config.get("port"))
        self.password = self._get_env_pwd() if db_password is None else db_password

        try:
            url = URL.create(
                drivername="postgresql",
                username=self.user,
                password=self.password,
                host=self.host,
                port=self.port,
                database=self.dbname
            )
            self.engine = create_engine(url)
            print(f"Connected to database '{self.dbname}'")
        except SQLAlchemyError as e:
            print(f"Failed to connect to database: {str(e)}")
            raise

    @staticmethod
    def _get_env_pwd():
        pwd = os.environ.get("POSTGRES_PASSWORD")
        if not pwd:
            raise ValueError("POSTGRES_PASSWORD environment variable not set.")
        return pwd

    def create_schema(self, schema_name: str) -> None:
        """
        Create a schema in the database using SQLAlchemy

        :param schema_name: Name of the schema to create
        """
        try:
            with self.engine.connect() as connection:
                connection.execute(CreateSchema(schema_name, if_not_exists=True))
                connection.commit()
                print(f"Schema '{schema_name}' created (or already exists).")
        except SQLAlchemyError as e:
            print(f"Error creating schema '{schema_name}': {str(e)}")

    def create_tables_from_data_model(self, schema_name: str, data_model_package: str) -> None:
        """
        Create tables in the specified schema using ORM models from the `data_model` package.

        :param schema_name: Name of the schema
        :param data_model_package: Name of the package containing ORM table models (e.g., 'data_model')
        """
        try:
            # Dynamically import all models from the specified package
            data_model = importlib.import_module(data_model_package)
            for _, module_name, _ in pkgutil.iter_modules(data_model.__path__):
                importlib.import_module(f"{data_model_package}.{module_name}")

            with self.engine.begin() as connection:
                # Set the search path to the specified schema
                connection.execute(text(f"SET search_path TO {schema_name};"))
                # Create all tables using metadata from imported models
                data_model.Base.metadata.create_all(bind=connection)
                print(f"Tables created in schema '{schema_name}'.")
        except SQLAlchemyError as e:
            print(f"Error creating tables in schema '{schema_name}': {str(e)}")

    def list_all_schemas(self) -> list:
        """
        List all schemas in the connected database.

        :return: List of schema names
        """
        try:
            inspector = inspect(self.engine)  # Use SQLAlchemy Inspector
            schemas = inspector.get_schema_names()
            print(f"Available schemas: {schemas}")
            return schemas
        except SQLAlchemyError as e:
            print(f"Error fetching schemas: {str(e)}")
            return []

    def list_schemas_stats(self) -> list:
        """
        List schemas in the current database with their owners, sizes, and table counts.

        :return: List of tuples (schema_name, schema_owner, schema_size, table_count)
        """
        try:
            query = """
                SELECT n.nspname AS schema_name,
                       pg_catalog.pg_get_userbyid(n.nspowner) AS schema_owner,
                       pg_size_pretty(pg_catalog.pg_total_relation_size(c.oid)) AS schema_size,
                       COUNT(t.tablename) AS table_count
                FROM pg_catalog.pg_namespace n
                LEFT JOIN pg_catalog.pg_class c ON c.relnamespace = n.oid
                LEFT JOIN pg_catalog.pg_tables t ON t.schemaname = n.nspname
                WHERE n.nspname NOT IN ('pg_catalog', 'information_schema')
                GROUP BY n.nspname, n.nspowner, c.oid
                ORDER BY n.nspname
            """
            with self.engine.connect() as connection:
                result = connection.execute(text(query))
                return [row for row in result]
        except SQLAlchemyError as e:
            print(f"Error listing schemas: {str(e)}")
            return []

    def list_tables(self, schema_name: str) -> list:
        """
        List tables in a given schema along with their columns and data types.

        :param schema_name: Name of the schema
        :return: List of tuples (table_name, list[columns with data types])
        """
        try:
            inspector = inspect(self.engine)
            tables = inspector.get_table_names(schema=schema_name)
            result = []
            for table in tables:
                columns = [
                    {"name": col["name"], "type": str(col["type"])}
                    for col in inspector.get_columns(table, schema=schema_name)
                ]
                result.append((table, columns))
            for table, columns in result:
                print(f"Table: {table}")
                for column in columns:
                    print(f"  Column: {column['name']} | Type: {column['type']}")
            return result
        except SQLAlchemyError as e:
            print(f"Error listing tables in schema '{schema_name}': {str(e)}")
            return []

    def list_catalog_info(self) -> list:
        """
        List schemas in the current database with their owners, sizes, and table counts.

        :return: List of tuples (schema_name, schema_owner, schema_size, table_count)
        """
        try:
            query = """
            SELECT
            n.nspname AS schema_name,
            pg_catalog.PG_GET_USERBYID(n.nspowner) AS schema_owner,
            (
                SELECT count(*) FROM pg_catalog.pg_tables WHERE schemaname = n.nspname
            ) AS table_count,
            (
                SELECT count(*) FROM pg_catalog.pg_views WHERE schemaname = n.nspname
            ) AS view_count,
            (
                SELECT count(*) FROM pg_catalog.pg_proc WHERE pronamespace = n.oid
            ) AS function_count
            FROM pg_catalog.pg_namespace n
            WHERE n.nspname NOT IN ('pg_catalog', 'information_schema')
            ORDER BY schema_name
            """
            with self.engine.connect() as connection:
                result = connection.execute(text(query))
                return [row for row in result]
        except SQLAlchemyError as e:
            print(f"Error listing schemas: {str(e)}")
            return []

    def fetch_table_to_csv(
        self,
        schema_name: str,
        table_name: str,
        data_download_path: str,
        force_overwrite: bool = False,
    ) -> None:
        """
        Fetch data from a table and download it as a CSV file to the specified folder.

        :param schema_name: Name of the schema
        :param table_name: Name of the table
        :param data_download_path: Directory to save the CSV file
        :param force_overwrite: If True, overwrite the file if it already exists. Default is False.
        """
        try:
            # Ensure the download path exists
            if not os.path.exists(data_download_path):
                print(f"Directory '{data_download_path}' does not exist. Creating it...")
                os.makedirs(data_download_path)

            # Build the output file path
            output_file_path = os.path.join(data_download_path, f"{schema_name}_{table_name}.csv")

            # Check if the file already exists
            if os.path.exists(output_file_path) and not force_overwrite:
                print(
                    f"File '{output_file_path}' already exists. Use force_overwrite=True to overwrite it."
                )
                return

            # Construct SQL query
            query = text(f'SELECT * FROM "{schema_name}"."{table_name}"')
            print(f"Executing query: {query.text}")

            with self.engine.connect() as connection:
                # Fetch data using Pandas
                df = pd.read_sql(query, con=connection)

                # Save the DataFrame to a CSV file
                df.to_csv(output_file_path, index=False)
                print(
                    f"Data from '{schema_name}.{table_name}' downloaded to '{output_file_path}'"
                )
        except SQLAlchemyError as e:
            print(
                f"Error fetching data from table '{schema_name}.{table_name}': {str(e)}"
            )
        except Exception as e:
            print(f"An unexpected error occurred: {str(e)}")
