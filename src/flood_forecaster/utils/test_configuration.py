from unittest import TestCase

from src.flood_forecaster.utils.configuration import load_database_config, load_openmeteo_config


class Test(TestCase):
    def test_load_database_config(self):
        conf = load_database_config("../../../config/config.ini")
        self.assertEqual(conf.get("dbname"), "postgres")

    def test_load_openmeteo_config(self):
        conf = load_openmeteo_config("../../../config/config.ini")
        self.assertEqual(conf["api_url"], "https://api.open-meteo.com/v1/forecast")
