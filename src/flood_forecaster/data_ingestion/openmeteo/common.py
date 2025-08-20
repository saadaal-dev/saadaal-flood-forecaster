import datetime
from typing import List, Dict, Any

import pandas as pd
from openmeteo_sdk import WeatherApiResponse
from sqlalchemy.orm import Session

from flood_forecaster import DatabaseConnection
from flood_forecaster.data_ingestion.openmeteo.weather_location import get_weather_locations
from flood_forecaster.utils.configuration import Config


def fetch_openmeteo_data(openmeteo, url: str, params: Dict[str, Any]) -> List[WeatherApiResponse]:
    """Common function to fetch data from OpenMeteo API"""
    return openmeteo.weather_api(url, params=params, verify=False)


def prepare_weather_locations(config: Config) -> tuple[List[str], List[float], List[float]]:
    """Get weather locations and extract labels, latitudes, and longitudes"""
    weather_locations = get_weather_locations(config.get_weather_location_metadata_path())
    location_labels, latitudes, longitudes = zip(
        *[(location.label, location.latitude, location.longitude) for location in weather_locations])
    return list(location_labels), list(latitudes), list(longitudes)


def process_weather_responses(responses: List[WeatherApiResponse], location_labels: List[str],
                              parse_function) -> pd.DataFrame:
    """Process OpenMeteo responses into a combined DataFrame"""
    daily_dfs = []

    for i, response in enumerate(responses):
        print(f"Coordinates {response.Latitude()}°N {response.Longitude()}°E")
        print(f"Elevation {response.Elevation()} m asl")
        print(f"Timezone {response.Timezone()} {response.TimezoneAbbreviation()}")
        print(f"Timezone difference to GMT+0 {response.UtcOffsetSeconds()} s")

        # Parse response using the provided parsing function
        daily_data = parse_function(response)
        daily_data["location_name"] = location_labels[i]

        daily_dfs.append(pd.DataFrame(data=daily_data))

    return pd.concat(daily_dfs, ignore_index=True)


def persist_weather_data(config: Config, df: pd.DataFrame, filename: str,
                         weather_model_class, clear_existing: bool = False) -> None:
    """Common function to persist weather data to database or CSV"""
    if config.use_database_weather():
        db_client = DatabaseConnection(config)

        with db_client.engine.connect() as conn:
            with Session(bind=conn) as session:
                if clear_existing:
                    # Empty the table for forecast data to replace it with new data
                    print(f"Emptying the table for {weather_model_class.__name__} data...")
                    session.query(weather_model_class).delete()

                # Convert DataFrame to weather objects
                weather_objects = weather_model_class.from_dataframe(df)
                session.add_all(weather_objects)
                session.commit()
                print(f"Inserted {len(weather_objects)} {weather_model_class.__name__} values into the database.")
    else:
        save_dataframe_to_csv(config, df, filename)


def create_forecast_params(latitudes: List[float], longitudes: List[float]) -> Dict[str, Any]:
    """Create parameters for forecast API call"""
    return {
        "latitude": latitudes,
        "longitude": longitudes,
        "forecast_days": 16,
        "daily": [
            "temperature_2m_max",
            "temperature_2m_min",
            "precipitation_sum",
            "rain_sum",
            "precipitation_hours",
            "precipitation_probability_max",
            "wind_speed_10m_max",
        ]
    }


def create_historical_params(start_date: datetime.datetime, end_date: datetime.datetime,
                             latitudes: List[float], longitudes: List[float]) -> Dict[str, Any]:
    """Create parameters for historical API call"""
    return {
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
        ]
    }


def save_dataframe_to_csv(config, df, filename):
    data_path = config.get_store_base_path()
    basename = data_path + filename
    file = "{}_{:%Y-%m-%d}.csv".format(
        basename, datetime.datetime.now()
    )
    df.to_csv(file, index=False)


def parse_daily_weather(daily):
    # Process daily data. The order of variables needs to be the same as requested.
    daily_temperature_2m_max = daily.Variables(0).ValuesAsNumpy()
    daily_temperature_2m_min = daily.Variables(1).ValuesAsNumpy()
    daily_precipitation_sum = daily.Variables(2).ValuesAsNumpy()
    daily_rain_sum = daily.Variables(3).ValuesAsNumpy()
    daily_precipitation_hours = daily.Variables(4).ValuesAsNumpy()
    daily_data = {
        "date":
            pd.date_range(
                start=pd.to_datetime(daily.Time(), unit="s", utc=True),
                end=pd.to_datetime(daily.TimeEnd(), unit="s", utc=True),
                freq=pd.Timedelta(seconds=daily.Interval()),
                inclusive="left",
            ),
        "temperature_2m_max": daily_temperature_2m_max,
        "temperature_2m_min": daily_temperature_2m_min,
        "precipitation_sum": daily_precipitation_sum,
        "rain_sum": daily_rain_sum,
        "precipitation_hours": daily_precipitation_hours}
    return daily_data
