from utils.configuration import Config
from utils.database_helper import DatabaseConnection
# from data_model import Base

if __name__ == "__main__":
    CONFIG_FILE_PATH = "../../config/config.ini"
    SCHEMA_NAME = "flood_forecaster"

    # Initialize database connection
    config = Config(CONFIG_FILE_PATH)
    db_conn = DatabaseConnection(config)

    # Create schema if not exists
    db_conn.create_schema(SCHEMA_NAME)
    DATA_MODEL_PACKAGE = "data_model"

    # Create tables in the schema
    db_conn.create_tables_from_data_model(SCHEMA_NAME, DATA_MODEL_PACKAGE)

    # List all tables from the given schema
    tables = db_conn.list_tables(SCHEMA_NAME)
    print(f"Tables in schema {SCHEMA_NAME}:")
    for table, columns in tables:
        print(f"Table: {table}")
        for column in columns:
            print(f"  Column: {column['name']} | Type: {column['type']}")
