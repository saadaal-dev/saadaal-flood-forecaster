from unittest import TestCase

from src.flood_forecaster.utils.configuration import Config

CONFIG_FILE_PATH = "../../../config/config.ini"


class Test(TestCase):
    config = Config(CONFIG_FILE_PATH)

    def test_load_database_config(self):
        conf = self.config.load_database_config()
        self.assertEqual(conf.get("dbname"), "postgres")

    def test_load_openmeteo_config(self):
        conf = self.config.load_openmeteo_config()
        self.assertEqual(conf["api_url"], "https://api.open-meteo.com/v1/forecast")
