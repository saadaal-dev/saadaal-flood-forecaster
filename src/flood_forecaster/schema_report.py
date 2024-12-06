from utils.database_helper import DatabaseConnection

if __name__ == "__main__":
    CONFIG_FILE_PATH = "../../config/config.ini"
    SCHEMA_NAME = "flood_forecaster"
    # SCHEMA_NAME = "public"

    # Initialize database connection
    db_conn = DatabaseConnection(CONFIG_FILE_PATH)

    schemas = db_conn.list_all_schemas()

    # Print schemas
    print("Schemas in the database:")
    for schema in schemas:
        print(f"- {schema}")

    # List all tables from a given schema
    tables = db_conn.list_tables(SCHEMA_NAME)
    print(f"Tables in schema {SCHEMA_NAME}:")
    for table, columns in tables:
        print(f"Table: {table}")
        for column in columns:
            print(f"  Column: {column['name']} | Type: {column['type']}")
