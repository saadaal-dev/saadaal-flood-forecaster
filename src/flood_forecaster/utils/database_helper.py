import configparser
import os
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.engine import URL
from sqlalchemy.exc import SQLAlchemyError


class DatabaseConnection:
    def __init__(self, config_file_path: str) -> None:
        """
        Initialize the database connection using parameters from a config file.

        :param config_file_path: Path to the configuration file
        """
        self.config = self._load_config(config_file_path)
        self.dbname = self.config.get("database", "dbname")
        self.user = self.config.get("database", "user")
        self.host = self.config.get("database", "host")
        self.port = self.config.get("database", "port")
        self.password = os.environ.get("POSTGRES_PASSWORD")

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
    def _load_config(config_file_path: str) -> configparser.ConfigParser:
        """
        Load configuration from the given file path.

        :param config_file_path: Path to the configuration file
        :return: ConfigParser object
        """
        if not os.path.exists(config_file_path):
            raise FileNotFoundError(f"Config file '{config_file_path}' not found.")
        
        config = configparser.ConfigParser()
        config.read(config_file_path)
        return config

    def create_schema(self, schema_name: str) -> None:
        """
        Create a schema in the database.
        
        :param schema_name: Name of the schema to create
        """
        try:
            with self.engine.connect() as connection:
                connection.execute(text(f"CREATE SCHEMA IF NOT EXISTS {schema_name};"))
                print(f"Schema '{schema_name}' created (or already exists).")
        except SQLAlchemyError as e:
            print(f"Error creating schema '{schema_name}': {str(e)}")

    def create_tables(self, schema_name: str, base) -> None:
        """
        Create tables in the specified schema using ORM models.

        :param schema_name: Name of the schema
        :param base: SQLAlchemy Base containing ORM models
        """
        try:
            with self.engine.begin() as connection:
                connection.execute(text(f"SET search_path TO {schema_name};"))
                base.metadata.create_all(bind=connection)
                print(f"Tables created in schema '{schema_name}'.")
        except SQLAlchemyError as e:
            print(f"Error creating tables in schema '{schema_name}': {str(e)}")

    def list_db_schemas(self) -> list:
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
                ORDER BY n.nspname;
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
            return result
        except SQLAlchemyError as e:
            print(f"Error listing tables in schema '{schema_name}': {str(e)}")
            return []

