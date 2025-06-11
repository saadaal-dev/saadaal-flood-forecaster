import unittest

from src.flood_forecaster.data_ingestion.swalim.river_level_api import fetch_latest_river_data
from src.flood_forecaster.utils.configuration import Config


class TestConfig(unittest.TestCase):

    def test_fetch_latest_river_data(self):
        # Mock configuration
        config = Config("src/tests/mock_config.ini")
        historical_river_levels = fetch_latest_river_data(config)
        self.assertEqual(len(historical_river_levels), 7, "Expected to fetch 7 historical river levels")
        river_names = [i.location_name for i in historical_river_levels]
        self.assertIn("Luuq", river_names, "Expected river station Luuq to be present in the fetched data")
