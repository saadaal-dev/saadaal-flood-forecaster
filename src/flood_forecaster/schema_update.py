from utils.database_helper import DatabaseConnection
from data_model import Base

if __name__ == "__main__":
    CONFIG_FILE_PATH = "../../config/config.ini"
    SCHEMA_NAME = "flood_forecaster"

    # Initialize database connection
    db_conn = DatabaseConnection(CONFIG_FILE_PATH)

    # Create schema if not exists
    db_conn.create_schema(SCHEMA_NAME)

    # Create tables in the schema
    db_conn.create_tables(SCHEMA_NAME, Base)

    # List all tables from the given schema
    tables = db_conn.list_tables(SCHEMA_NAME)
    print(f"Tables in schema {SCHEMA_NAME}:")
    for table, columns in tables:
        print(f"Table: {table}")
        for column in columns:
            print(f"  Column: {column['name']} | Type: {column['type']}")
