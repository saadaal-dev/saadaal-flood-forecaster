import datetime
from typing import List, Optional

import openmeteo_requests
import requests_cache
from openmeteo_sdk.WeatherApiResponse import WeatherApiResponse
from retry_requests import retry

from src.flood_forecaster.data_ingestion.openmeteo.common import get_daily_data
from src.flood_forecaster.utils.configuration import Config


# Get the historical weather data for specific locations
def get_historical_weather(latitudes: List[float], longitudes: List[float], config: Config, max_date: Optional[datetime.datetime] = None):
    # Make sure all required weather variables are listed here
    # The order of variables in hourly or daily is important to assign them correctly below
    url = config.get_openmeteo_api_archive_url()
    end_date = datetime.datetime.now() - datetime.timedelta(days=1)
    if max_date is not None:
        start_date = max_date + datetime.timedelta(days=1)  # FIXME this creates duplicates
    else:
        start_date = end_date - datetime.timedelta(days=10 * 365)

    print("Fetching historical weather data from Open-Meteo API...")
    print(f"Start date: {start_date.strftime('%Y-%m-%d')}, End date: {end_date.strftime('%Y-%m-%d')}")
    if start_date > end_date:
        print("You have the most updated data in the historical weather :)")
        return None

    print("Using max_date for historical weather data:", start_date)
    params = {
        "latitude": latitudes,
        "longitude": longitudes,
        "start_date": start_date.strftime("%Y-%m-%d"),
        # FIXME: having issue resolving the historical data for yesterday... (API returns empty values)
        "end_date": end_date.strftime("%Y-%m-%d"),
        "daily": [
            "temperature_2m_max",
            "temperature_2m_min",
            "precipitation_sum",
            "rain_sum",
            "precipitation_hours",
        ],
        "timezone": "auto",
    }
    responses = openmeteo.weather_api(url, params=params, verify=False)
    return responses


def get_daily_data_historical(response: WeatherApiResponse) -> Optional[dict]:
    return get_daily_data(response, forecast=False)


# Setup the Open-Meteo API client with cache and retry on error
cache_session = requests_cache.CachedSession(".cache", expire_after=-1)
retry_session = retry(cache_session, retries=5, backoff_factor=0.2)
openmeteo = openmeteo_requests.Client(session=retry_session)
