import unittest
from unittest.mock import patch, MagicMock

from src.flood_forecaster.utils.database_helper import DatabaseConnection


# from sqlalchemy.exc import SQLAlchemyError


class TestDatabaseHelper(unittest.TestCase):
    def setUp(self):
        self.mock_config_data = {
            "dbname": "testdb",
            "user": "testuser",
            "host": "localhost",
            "port": "5432",
        }

    @patch("os.environ.get", return_value="testpassword")
    @patch("flood_forecaster.utils.database_helper.create_engine")
    @patch("flood_forecaster.utils.configuration.Config.get_database_config", return_value={
        "dbname": "testdb",
        "user": "testuser",
        "host": "localhost",
        "port": "5432",
    })
    def test_database_connection_success(self, mock_load_config, mock_create_engine, mock_env):
        # Mocking the Config object
        config = MagicMock()
        config.get_database_config.return_value = {
            "dbname": "testdb",
            "user": "testuser",
            "host": "localhost",
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

        # Verify create_engine was called - fails due to password obfuscation by SQLAlchemy
        # Extract the actual call argument
        args, _ = mock_create_engine.call_args

        # Assert the individual components of the connection URL
        self.assertEqual(args[0].drivername, "postgresql")
        self.assertEqual(args[0].username, "testuser")
        self.assertEqual(args[0].password, "testpassword")
        self.assertEqual(args[0].host, "localhost")
        self.assertEqual(args[0].port, 5432)
        self.assertEqual(args[0].database, "testdb")

    @patch("os.environ.get", return_value="testpassword")
    @patch("flood_forecaster.utils.database_helper.create_engine", side_effect=Exception("Mocked error"))
    @patch("flood_forecaster.utils.configuration.Config.get_database_config", return_value={
        "dbname": "testdb",
        "user": "testuser",
        "host": "localhost",
        "port": "5432",
    })
    def test_database_connection_failure(self, mock_load_config, mock_create_engine, mock_env):
        config = MagicMock()

        with self.assertRaises(Exception):
            DatabaseConnection(config)

    @patch("os.environ.get", return_value=None)
    def test_missing_env_password(self, mock_env):
        with self.assertRaises(ValueError):
            DatabaseConnection._get_env_pwd()
