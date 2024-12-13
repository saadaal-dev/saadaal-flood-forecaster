import unittest
from unittest.mock import patch, mock_open
# import os
from flood_forecaster.utils.configuration import Config


class TestConfig(unittest.TestCase):
    def setUp(self):
        self.mock_config_content = """
        [database]
        dbname=testdb
        user=testuser
        host=localhost
        port=5432

        [openmeteo]
        api_url=https://api.open-meteo.com/v1/forecast
        """
        self.mock_file_path = "mock_config.ini"

    @patch("os.path.exists", return_value=True)  # Simulate file existence
    @patch("builtins.open", new_callable=mock_open, read_data="""[database]
    dbname=testdb
    user=testuser
    host=localhost
    port=5432
    """)
    def test_load_database_config(self, mock_file, mock_exists):
        config = Config(self.mock_file_path)
        db_config = config.load_database_config()
        self.assertEqual(db_config["dbname"], "testdb")
        self.assertEqual(db_config["user"], "testuser")
        self.assertEqual(db_config["host"], "localhost")
        self.assertEqual(db_config["port"], "5432")

    # @patch("flood_forecaster.utils.configuration.ConfigParser.read")  # target correct module
    @patch("os.path.exists", return_value=True)
    @patch("configparser.ConfigParser.read")
    def test_load_config_success(self, mock_read, mock_exists):
        config = Config(self.mock_file_path)
        mock_read.assert_called_once_with(self.mock_file_path)

    @patch("os.path.exists", return_value=False)
    def test_load_config_file_not_found(self, mock_exists):
        with self.assertRaises(FileNotFoundError):
            Config(self.mock_file_path)

    @patch("builtins.open", new_callable=mock_open, read_data="""
        [database]
        dbname=testdb
        user=testuser
        host=localhost
        port=5432
        
        [openmeteo]
        api_url=https://api.open-meteo.com/v1/forecast
    """)
    @patch("os.path.exists", return_value=True)  # Simulate file existence
    def test_load_openmeteo_config(self, mock_file, mock_exists):
        config = Config(self.mock_file_path)
        api_config = config.load_openmeteo_config()
        self.assertEqual(api_config["api_url"], "https://api.open-meteo.com/v1/forecast")
