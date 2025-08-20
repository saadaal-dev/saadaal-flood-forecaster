import unittest

import openmeteo_requests
import requests_cache
from retry_requests import retry

from flood_forecaster import Config
from flood_forecaster.data_ingestion.openmeteo.forecast_weather import fetch_forecast
from flood_forecaster.data_ingestion.openmeteo.historical_weather import fetch_historical


class TestOpenmeteo(unittest.TestCase):

    def test_fetch_openmeteo_forecast(self):
        # Test get forecast data from OpenMeteo API
        cache_session = requests_cache.CachedSession(".cache", expire_after=3600)
        retry_session = retry(cache_session, retries=5, backoff_factor=0.2)
        openmeteo = openmeteo_requests.Client(session=retry_session)

        # Mock configuration
        config = Config("src/tests/mock_config.ini")

        # Fetch forecast data
        forecast_data = fetch_forecast(config, openmeteo)

        self.assertEqual(len(forecast_data), 20 * 16)  # 20 locations, 16 days of forecast

    def test_fetch_openmeteo_historical(self):
        cache_session = requests_cache.CachedSession(".cache", expire_after=3600)
        retry_session = retry(cache_session, retries=5, backoff_factor=0.2)
        openmeteo = openmeteo_requests.Client(session=retry_session)

        # Mock configuration
        config = Config("src/tests/mock_config.ini")

        # Fetch forecast data
        historical_data = fetch_historical(config, openmeteo)
        if historical_data:
            self.assertGreater(len(historical_data), 20)  # At least 1 day of historical data for 20 locations


if __name__ == '__main__':
    unittest.main()
