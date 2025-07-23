from typing import List
import datetime
from functools import partial

import openmeteo_requests
import requests_cache
from openmeteo_sdk.WeatherApiResponse import WeatherApiResponse
from retry_requests import retry
from sqlalchemy.orm import Session
import pandas as pd

from src.flood_forecaster.data_ingestion.openmeteo.weather_location import get_weather_locations
from src.flood_forecaster.data_model.weather import ForecastWeather
from src.flood_forecaster.data_model.station import Station
from src.flood_forecaster.data_ingestion.openmeteo.common import append_station_information, get_daily_data, get_station_data, start_database_connection
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


def manage_weather_forecast(config, stations, responses, database_connection):
    daily_dfs = []
    data_path = config.get_store_base_path()

    station = None
    for station, response in zip(stations, responses):
        print(f"The Label is {station.label}")
        print(f"Coordinates {response.Latitude()}°N {response.Longitude()}°E")
        print(f"Elevation {response.Elevation()} m asl")
        print(f"Timezone {response.Timezone()} {response.TimezoneAbbreviation()}")
        print(f"Timezone difference to GMT+0 {response.UtcOffsetSeconds()} s")

        daily_df = append_station_information(response, station, get_daily_data_actual)
        daily_dfs.append(daily_df)

    daily_combined = pd.concat(daily_dfs, ignore_index=True)

    if isinstance(station, Station):
        type = "station"
    else:
        type = "distinct"

    basename = data_path + f"forecast_station_weather_{type}"
    daily_filename = "{}_daily_{:%Y-%m-%d}.csv".format(
        basename, datetime.datetime.now()
    )
    # add the logic to write to database

    if config.use_database_weather().lower() == "true":
        # Convert each row in daily_combined DataFrame to ForecastWeather objects
        daily_combined = daily_combined.drop(columns=["forecast_latitude"])
        daily_combined = daily_combined.drop(columns=["forecast_longitude"])
        forecast_weather_objects = ForecastWeather.from_dataframe(daily_combined)

        with database_connection.engine.connect() as conn:
            with Session(bind=conn) as session:
                session.add_all(forecast_weather_objects)
                session.commit()
                print(f"Inserted {len(forecast_weather_objects)} weather forecast entries into the database.")
            
    else:
        daily_combined.to_csv(daily_filename, index=False)


def fetch_forecast(config: Config):
    database_connection = start_database_connection(config)
    # Empty the table for the forecast weather data
    print("Emptying the table for the forecast weather data")
    database_connection.empty_table(ForecastWeather)
    get_station_function = partial(get_weather_locations, config.get_weather_location_metadata_path())

    get_station_data(config, get_station_function, get_weather_forecast, manage_weather_forecast, database_connection)


# Setup the Open-Meteo API client with cache and retry on error
cache_session = requests_cache.CachedSession(".cache", expire_after=3600)
retry_session = retry(cache_session, retries=5, backoff_factor=0.2)
openmeteo = openmeteo_requests.Client(session=retry_session)
