import os
import unittest
from unittest.mock import patch, MagicMock

from flood_forecaster.utils.database_helper import DatabaseConnection


class TestDatabaseHelper(unittest.TestCase):
    def setUp(self):
        self.mock_config_data = {
            "dbname": "testdb",
            "user": "testuser",
            "port": "5432",
        }

    @patch("flood_forecaster.utils.database_helper.load_dotenv")
    @patch.dict(os.environ, {"DB_HOST": "localhost", "POSTGRES_PASSWORD": "testpassword"})
    @patch("flood_forecaster.utils.database_helper.create_engine")
    def test_database_connection_success(self, mock_create_engine, mock_dotenv):
        # Mocking the Config object
        config = MagicMock()
        config.load_data_database_config.return_value = {
            "dbname": "testdb",
            "user": "testuser",
            "port": "5432",
        }

        # Initialize the DatabaseConnection
        connection = DatabaseConnection(config)

        # Assert that attributes are correctly set
        self.assertEqual(connection.dbname, "testdb")
        self.assertEqual(connection.user, "testuser")
        self.assertEqual(connection.host, "localhost")
        self.assertEqual(connection.port, 5432)
        self.assertEqual(connection.password, "testpassword")

        # Verify create_engine was called
        # Extract the actual call argument
        args, _ = mock_create_engine.call_args

        # Assert the individual components of the connection URL
        self.assertEqual(args[0].drivername, "postgresql")
        self.assertEqual(args[0].username, "testuser")
        self.assertEqual(args[0].password, "testpassword")
        self.assertEqual(args[0].host, "localhost")
        self.assertEqual(args[0].port, 5432)
        self.assertEqual(args[0].database, "testdb")

    @patch("flood_forecaster.utils.database_helper.load_dotenv")
    @patch.dict(os.environ, {"DB_HOST": "localhost", "POSTGRES_PASSWORD": "testpassword"})
    @patch("flood_forecaster.utils.database_helper.create_engine", side_effect=Exception("Mocked error"))
    def test_database_connection_failure(self, mock_create_engine, mock_dotenv):
        config = MagicMock()
        config.load_data_database_config.return_value = {
            "dbname": "testdb",
            "user": "testuser",
            "port": "5432",
        }

        with self.assertRaises(Exception):
            DatabaseConnection(config)

    @patch("flood_forecaster.utils.database_helper.load_dotenv")
    @patch.dict(os.environ, {}, clear=True)
    def test_missing_env_password(self, mock_dotenv):
        with self.assertRaises(ValueError):
            DatabaseConnection._get_env_pwd()

    @patch("flood_forecaster.utils.database_helper.load_dotenv")
    @patch.dict(os.environ, {}, clear=True)
    def test_missing_env_db_host(self, mock_dotenv):
        with self.assertRaises(ValueError):
            DatabaseConnection._get_env_host()
