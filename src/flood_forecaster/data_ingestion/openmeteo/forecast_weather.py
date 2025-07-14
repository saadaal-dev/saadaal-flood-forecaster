from typing import List

import openmeteo_requests
import requests_cache
from openmeteo_sdk.WeatherApiResponse import WeatherApiResponse
from retry_requests import retry

from src.flood_forecaster.data_ingestion.openmeteo.common import get_daily_data
from src.flood_forecaster.utils.configuration import Config


# Get the weather forecast for specific locations
def get_weather_forecast(latitudes: List[float], longitudes: List[float], config: Config):
    url = config.get_openmeteo_api_url()
    params = {
        "latitude": latitudes,
        "longitude": longitudes,
        "hourly": ["temperature_2m", "precipitation_probability", "precipitation"],
        "daily": [
            "temperature_2m_max",
            "temperature_2m_min",
            "precipitation_sum",
            "rain_sum",
            "precipitation_hours",
            "precipitation_probability_max",
            "wind_speed_10m_max",
        ],
        "forecast_days": 16,  # Forecast for the next 15 days + today
        "timezone": "auto",
    }
    responses = openmeteo.weather_api(url, params=params, verify=False)
    return responses


def get_daily_data_actual(response: WeatherApiResponse):
    return get_daily_data(response, forecast=True)


# Setup the Open-Meteo API client with cache and retry on error
cache_session = requests_cache.CachedSession(".cache", expire_after=3600)
retry_session = retry(cache_session, retries=5, backoff_factor=0.2)
openmeteo = openmeteo_requests.Client(session=retry_session)
