# CONFIG_FILE_PATH = "../../../config/config.ini"

import unittest
from unittest.mock import patch, mock_open, MagicMock
# import os
from utils.configuration import Config
from utils.database_helper import DatabaseConnection
from sqlalchemy.exc import SQLAlchemyError


class TestConfig(unittest.TestCase):
    def setUp(self):
        self.mock_config_content = """[database]
        dbname=testdb
        user=testuser
        host=localhost
        port=5432
        """
        self.mock_file_path = "mock_config.ini"

    @patch("builtins.open", new_callable=mock_open, read_data="""[database]\ndbname=testdb\nuser=testuser\nhost=localhost\nport=5432\n""")
    def test_load_database_config(self, mock_file):
        config = Config(self.mock_file_path)
        db_config = config.load_database_config()
        self.assertEqual(db_config["dbname"], "testdb")
        self.assertEqual(db_config["user"], "testuser")
        self.assertEqual(db_config["host"], "localhost")
        self.assertEqual(db_config["port"], "5432")

    @patch("os.path.exists", return_value=True)
    @patch("configparser.ConfigParser.read")
    def test_load_config_success(self, mock_read, mock_exists):
        config = Config(self.mock_file_path)
        mock_read.assert_called_once_with(self.mock_file_path)

    @patch("os.path.exists", return_value=False)
    def test_load_config_file_not_found(self, mock_exists):
        with self.assertRaises(FileNotFoundError):
            Config(self.mock_file_path)


class TestDatabaseConnectionWithConfig(unittest.TestCase):
    def setUp(self):
        self.mock_config_data = {
            "dbname": "testdb",
            "user": "testuser",
            "host": "localhost",
            "port": "5432",
        }

    @patch("os.environ.get", return_value="testpassword")
    @patch("your_module.create_engine")
    @patch("utils.configuration.Config.load_database_config", return_value={
        "dbname": "testdb",
        "user": "testuser",
        "host": "localhost",
        "port": "5432",
    })
    def test_database_connection_success(self, mock_load_config, mock_create_engine, mock_env):
        config = MagicMock()
        config.load_database_config.return_value = self.mock_config_data
        connection = DatabaseConnection(config)

        self.assertEqual(connection.dbname, "testdb")
        self.assertEqual(connection.user, "testuser")
        self.assertEqual(connection.host, "localhost")
        self.assertEqual(connection.port, 5432)
        self.assertEqual(connection.password, "testpassword")
        mock_create_engine.assert_called_once()

    @patch("os.environ.get", return_value="testpassword")
    @patch("your_module.create_engine", side_effect=SQLAlchemyError("Mocked error"))
    @patch("utils.configuration.Config.load_database_config", return_value={
        "dbname": "testdb",
        "user": "testuser",
        "host": "localhost",
        "port": "5432",
    })
    def test_database_connection_failure(self, mock_load_config, mock_create_engine, mock_env):
        config = MagicMock()
        config.load_database_config.return_value = self.mock_config_data

        with self.assertRaises(SQLAlchemyError):
            DatabaseConnection(config)

    @patch("os.environ.get", return_value=None)
    def test_missing_env_password(self, mock_env):
        with self.assertRaises(ValueError):
            DatabaseConnection._get_env_pwd()
