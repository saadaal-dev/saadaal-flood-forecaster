import datetime
import os
from typing import List

import openmeteo_requests
import pandas as pd
import requests_cache
from openmeteo_sdk import WeatherApiResponse
from retry_requests import retry

from flood_forecaster.utils.configuration import Config

def get_historical_weather(latitudes: List[float], longitudes: List[float], config: Config, max_date: datetime.datetime = None):
    # Make sure all required weather variables are listed here
    # The order of variables in hourly or daily is important to assign them correctly below
    url = config.get_openmeteo_api_archive_url()
    end_date = datetime.datetime.now() - datetime.timedelta(days=1)
    if max_date is not None:
        start_date = max_date + datetime.timedelta(days=1)  # max date in table +1
    else: 
        start_date = end_date - datetime.timedelta(days=3 * 365)

    if start_date > end_date:
        print("You have the most updated data in the forecast :)")
        return None

    print("Using max_date for historical weather data:", start_date)
    params = {
        "latitude": latitudes,
        "longitude": longitudes,
        "start_date": start_date.strftime("%Y-%m-%d"),
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


def get_daily_data_historical(response: WeatherApiResponse):
    # Process daily data. The order of variables needs to be the same as requested.
    daily = response.Daily()
    daily_temperature_2m_max = daily.Variables(0).ValuesAsNumpy()
    daily_temperature_2m_min = daily.Variables(1).ValuesAsNumpy()
    daily_precipitation_sum = daily.Variables(2).ValuesAsNumpy()
    daily_rain_sum = daily.Variables(3).ValuesAsNumpy()
    daily_precipitation_hours = daily.Variables(4).ValuesAsNumpy()

    daily_data = {
        "date": pd.date_range(
            start=pd.to_datetime(daily.Time(), unit="s", utc=True),
            end=pd.to_datetime(daily.TimeEnd(), unit="s", utc=True),
            freq=pd.Timedelta(seconds=daily.Interval()),
            inclusive="left",
        )
    }
    daily_data["forecast_latitude"] = response.Latitude()
    daily_data["forecast_longitude"] = response.Longitude()
    daily_data["temperature_2m_max"] = daily_temperature_2m_max
    daily_data["temperature_2m_min"] = daily_temperature_2m_min
    daily_data["precipitation_sum"] = daily_precipitation_sum
    daily_data["rain_sum"] = daily_rain_sum
    daily_data["precipitation_hours"] = daily_precipitation_hours
    return daily_data


# Setup the Open-Meteo API client with cache and retry on error
cache_session = requests_cache.CachedSession(".cache", expire_after=-1)
retry_session = retry(cache_session, retries=5, backoff_factor=0.2)
openmeteo = openmeteo_requests.Client(session=retry_session)
