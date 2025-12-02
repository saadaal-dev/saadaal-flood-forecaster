import unittest

import openmeteo_requests

from flood_forecaster import Config
from flood_forecaster.data_ingestion.openmeteo.forecast_weather import fetch_forecast
from flood_forecaster.data_ingestion.openmeteo.historical_weather import fetch_historical
from flood_forecaster_cli.commands.common import create_openmeteo_client


class TestOpenmeteo(unittest.TestCase):
    openmeteo: openmeteo_requests.Client

    def beforeAll(self):
        # Test get forecast data from OpenMeteo API
        self.openmeteo = create_openmeteo_client(expire_after=3600)

    def test_fetch_openmeteo_forecast(self):
        # Mock configuration
        config = Config("src/tests/mock_config.ini")

        # Fetch forecast data
        forecast_data = fetch_forecast(config, self.openmeteo)

        self.assertEqual(len(forecast_data), 20 * 16)  # 20 locations, 16 days of forecast

    def test_fetch_openmeteo_historical(self):
        # Mock configuration
        config = Config("src/tests/mock_config.ini")

        # Fetch forecast data
        historical_data = fetch_historical(config, self.openmeteo)
        if historical_data is not None:
            self.assertGreater(len(historical_data), 20)  # At least 1 day of historical data for 20 locations
        else:
            self.fail("Expected to fetch historical weather data, but got None")


if __name__ == '__main__':
    unittest.main()
