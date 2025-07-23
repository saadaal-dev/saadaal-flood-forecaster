import datetime
from typing import List, Optional
from functools import partial

import openmeteo_requests
import requests_cache
from openmeteo_sdk.WeatherApiResponse import WeatherApiResponse
from retry_requests import retry
from sqlalchemy.orm import Session
import pandas as pd

from src.flood_forecaster.data_ingestion.openmeteo.weather_location import get_weather_locations
from src.flood_forecaster.data_model.weather import HistoricalWeather
from src.flood_forecaster.data_model.station import Station
from src.flood_forecaster.data_ingestion.openmeteo.common import append_station_information, get_daily_data, get_station_data, start_database_connection
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


def manage_historical_forecast(config, stations, responses, database_connection):
    daily_dfs = []
    data_path = config.get_store_base_path()

    station = None
    for station, response in zip(stations, responses):
        print(f"Coordinates {response.Latitude()}°N {response.Longitude()}°E")
        print(f"Elevation {response.Elevation()} m asl")
        print(f"Timezone {response.Timezone()} {response.TimezoneAbbreviation()}")
        print(f"Timezone difference to GMT+0 {response.UtcOffsetSeconds()} s")

        daily_df = append_station_information(response, station, get_daily_data_historical)
        daily_dfs.append(daily_df)

    daily_combined = pd.concat(daily_dfs, ignore_index=True)

    if isinstance(station, Station):
        type = "station"
    else:
        type = "distinct"

    daily_filename = data_path + "historical__" + f"{type}_" + "weather_daily_{:%Y-%m-%d}.csv".format(
        datetime.datetime.now()
    )

    if config.use_database_weather().lower() == "true":
        # Convert each row in daily_combined DataFrame to ForecastWeather objects
        daily_combined = daily_combined.drop(columns=["forecast_latitude"])
        daily_combined = daily_combined.drop(columns=["forecast_longitude"])
        forecast_weather_objects = HistoricalWeather.from_dataframe(daily_combined)

        with database_connection.engine.connect() as conn:
            with Session(bind=conn) as session:
                session.add_all(forecast_weather_objects)
                session.commit()
                print(f"Inserted {len(forecast_weather_objects)} historical weather entries into the database.")
    else:
        daily_combined.to_csv(daily_filename)


def fetch_historical(config: Config):
    database_connection = start_database_connection(config)
    # get the max date from the db
    max_date = database_connection.get_max_date(HistoricalWeather)

    print(f"Max date in the database: {max_date}")
    get_station_function = partial(get_weather_locations, config.get_weather_location_metadata_path())

    get_station_data(
        config,
        get_station_function,
        partial(get_historical_weather, max_date=max_date),
        manage_historical_forecast, database_connection
    )


# Setup the Open-Meteo API client with cache and retry on error
cache_session = requests_cache.CachedSession(".cache", expire_after=-1)
retry_session = retry(cache_session, retries=5, backoff_factor=0.2)
openmeteo = openmeteo_requests.Client(session=retry_session)
