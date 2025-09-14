import datetime
import importlib
import os
import pkgutil
from typing import Optional

import pandas as pd
# import numpy as np
from dotenv import load_dotenv
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.engine import URL
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.schema import CreateSchema
from tabulate import tabulate

from flood_forecaster.data_model import Base
from flood_forecaster.utils.configuration import Config


class DatabaseConnection:
    def __init__(self, config: Config, db_password: Optional[str] = None) -> None:
        """
        Initialize the database connection using parameters from a config file.

        :param config: Config object
        """
        _config = config.load_data_database_config()
        self.dbname = _config.get("dbname")
        self.user = _config.get("user")
        self.host = _config.get("host")
        self.port = int(_config.get("port", 5432))
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
            print(f"Connected to database '{self.dbname}' in {self.host}")
        except SQLAlchemyError as e:
            print(f"Failed to connect to database: {str(e)}")
            raise

    @staticmethod
    def _get_env_pwd():
        load_dotenv()
        pwd = os.getenv("POSTGRES_PASSWORD")
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
                Base.metadata.drop_all(bind=connection)

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

    def empty_table(self, model):
        with self.engine.connect() as conn:
            conn.execute(model.__table__.delete())
            conn.commit()

    def get_max_date(self, model_class, date_column="date") -> Optional[datetime]:
        """
        Fetch the maximum date from the specified model class and date column.
        :param model_class: Class defined in /data_model, representing the table model (e.g., PredictedRiverLevel)
        :param date_column: Name of the date column in the table (default is 'date')
        :return: Maximum date as a datetime object (or None if no dates found)
        """
        with self.engine.connect() as conn:
            from sqlalchemy import func, select
            stmt = select(func.max(getattr(model_class, date_column)))
            result = conn.execute(stmt).scalar()
            return result

    def fetch_table_to_csv(
            self,
            schema_name: str,
            table_name: str,
            data_download_path: str,
            force_overwrite: bool = False,
            preview_rows: int = 20,  # limit rows for screen printing
            where_clause: str | None = None,
    ) -> None:
        """
        Fetch data from a table and download it as a CSV file to the specified folder.

        :param schema_name: Name of the schema
        :param table_name: Name of the table
        :param data_download_path: Directory to save the CSV file
        :param force_overwrite: If True, overwrite the file if it already exists. Default is False.
        :param preview_rows: Number of rows to pretty-print.
        :param where_clause: Optional SQL WHERE condition (without 'WHERE') to filter data.
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

            # Build SQL query dynamically
            query_str = f'SELECT * FROM "{schema_name}"."{table_name}"'
            if where_clause:
                query_str += f" WHERE {where_clause}"

            query = text(query_str)
            print(f"Executing query: {query.text}")

            with self.engine.connect() as connection:
                # Fetch data using Pandas
                df = pd.read_sql(query, con=connection)

                # Save the DataFrame to a CSV file
                df.to_csv(output_file_path, index=False)
                print(
                    f"Data from '{schema_name}.{table_name}' downloaded to '{output_file_path}'"
                )

                print("\nPreview of downloaded data:")
                print(tabulate(df.head(preview_rows), headers="keys", tablefmt="psql"))

        except SQLAlchemyError as e:
            print(
                f"Error fetching data from table '{schema_name}.{table_name}': {str(e)}"
            )
        except Exception as e:
            print(f"An unexpected error occurred: {str(e)}")

    def validate_table_data(
        self, schema_name: str, table_name: str, hard_limit: int = 100000
    ) -> None:
        """
        Validate table data: missing values, invalid values, outliers.
        Dynamically applies LIMIT if table is very large.
        """
        try:
            with self.engine.connect() as connection:
                # Count total rows
                count_query = text(f'SELECT COUNT(*) FROM "{schema_name}"."{table_name}"')
                total_rows = connection.execute(count_query).scalar()

                print(f"\nValidating table: {schema_name}.{table_name}")
                print(f"Total rows: {total_rows:,}")

                # Apply LIMIT if needed
                if total_rows > hard_limit:
                    query = text(f'SELECT * FROM "{schema_name}"."{table_name}" LIMIT {hard_limit}')
                    print(f"⚠️ Using LIMIT {hard_limit} for validation (large table)")
                else:
                    query = text(f'SELECT * FROM "{schema_name}"."{table_name}"')

                df = pd.read_sql(query, con=connection)

                # --- VALIDATIONS ---
                print("\nValidation results:")

                # Missing values
                nulls = df.isnull().sum()
                cols_with_nulls = nulls[nulls > 0]
                if not cols_with_nulls.empty:
                    print("⚠️ Missing values found:")
                    for col, n in cols_with_nulls.items():
                        print(f"   - {col}: {n} missing")
                else:
                    print("✅ No missing values detected")

                # Duplicate rows
                dup_count = df.duplicated().sum()
                if dup_count > 0:
                    print(f"⚠️ Duplicate rows: {dup_count}")
                else:
                    print("✅ No duplicate rows detected")

                # Outliers (basic numeric range check, e.g., z-score > 3)
                numeric_cols = df.select_dtypes(include=["int64", "float64"]).columns
                if not numeric_cols.empty:
                    zscores = (df[numeric_cols] - df[numeric_cols].mean()) / df[numeric_cols].std()
                    outlier_counts = (zscores.abs() > 3).sum()
                    if outlier_counts.sum() > 0:
                        print("⚠️ Outliers detected in numeric columns:")
                        for col, n in outlier_counts.items():
                            if n > 0:
                                print(f"   - {col}: {n} potential outliers")
                    else:
                        print("✅ No strong outliers detected")
                else:
                    print("\nNo numeric columns for outlier detection")

        except SQLAlchemyError as e:
            print(f"⚠️ Database error: {str(e)}")
        except Exception as e:
            print(f"⚠️ Unexpected error: {str(e)}")

    def validate_sensor_readings(self, schema_name: str = "public", table_name: str = "sensor_readings", hard_limit: int = 100000):
        """
        Specific validation for the sensor_readings table.
        Detects nulls, invalid values like '---', zeros where not expected, and out-of-range timestamps.
        """
        try:
            with self.engine.connect() as connection:
                # Count total rows
                count_query = text(f'SELECT COUNT(*) FROM "{schema_name}"."{table_name}"')
                total_rows = connection.execute(count_query).scalar()

                print(f"\nValidating table: {schema_name}.{table_name}")
                print(f"Total rows: {total_rows:,}")

                # Apply LIMIT if needed
                if total_rows > hard_limit:
                    query = text(f'SELECT * FROM "{schema_name}"."{table_name}" LIMIT {hard_limit}')
                    print(f"⚠️ Using LIMIT {hard_limit} for validation (large table)")
                else:
                    query = text(f'SELECT * FROM "{schema_name}"."{table_name}"')

                df = pd.read_sql(query, con=connection)

                print("\nSensor-specific validation results:")

                # Missing/null values
                nulls = df.isnull().sum()
                cols_with_nulls = nulls[nulls > 0]
                if not cols_with_nulls.empty:
                    print("⚠️ Missing values found:")
                    for col, n in cols_with_nulls.items():
                        print(f"   - {col}: {n} missing")
                else:
                    print("✅ No missing values (NULL)")

                # Look for invalid values in 'value' column
                if "value" in df.columns:
                    bad_values = df[df["value"].isin(["---", "", "NULL"])]
                    zeros = df[df["value"].astype(str).str.strip() == "0"]
                    if not bad_values.empty:
                        print(f"⚠️ Invalid values detected in 'value': {len(bad_values)} rows (---, empty, NULL)")
                    if not zeros.empty:
                        print(f"⚠️ '0' readings detected in 'value': {len(zeros)} rows (may be invalid depending on sensor)")
                    if bad_values.empty and zeros.empty:
                        print("✅ No invalid values in 'value'")

                # Timestamp sanity check
                if "reading_ts" in df.columns:
                    # Ensure tz-aware (convert tz-naive to UTC)
                    if pd.api.types.is_datetime64_any_dtype(df["reading_ts"]):
                        if df["reading_ts"].dt.tz is None:
                            df["reading_ts"] = df["reading_ts"].dt.tz_localize("UTC")
                        else:
                            df["reading_ts"] = df["reading_ts"].dt.tz_convert("UTC")

                        min_ts, max_ts = df["reading_ts"].min(), df["reading_ts"].max()
                        print(f"Timestamp range: {min_ts} → {max_ts}")

                        # Define timestamp comparison bounds
                        lower_bound = pd.Timestamp("1900-01-01", tz="UTC")
                        upper_bound = pd.Timestamp("2030-01-01", tz="UTC")

                        if min_ts < lower_bound or max_ts > upper_bound:
                            print("⚠️ Invalid timestamps detected")
                    else:
                        print("⚠️ reading_ts column not recognized as datetime")

                # Firmware version presence
                if "firmware" in df.columns:
                    firmware_nulls = df["firmware"].isnull().sum()
                    if firmware_nulls > 0:
                        print(f"⚠️ Missing firmware versions: {firmware_nulls}")
                    else:
                        print("✅ Firmware version present in all rows")

        except Exception as e:
            print(f"⚠️ Validation failed: {str(e)}")
