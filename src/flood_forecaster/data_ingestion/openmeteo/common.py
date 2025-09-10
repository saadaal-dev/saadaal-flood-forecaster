import datetime
from typing import List, Dict, Any, Optional

import numpy as np
import pandas as pd
from openmeteo_sdk.WeatherApiResponse import WeatherApiResponse
from openmeteo_sdk.VariablesWithTime import VariablesWithTime
from openmeteo_sdk.VariableWithValues import VariableWithValues
from sqlalchemy.orm import Session

from src.flood_forecaster import DatabaseConnection
from src.flood_forecaster.data_ingestion.openmeteo.weather_location import get_weather_locations
from src.flood_forecaster.utils.configuration import Config
from src.flood_forecaster.data_model.weather import ForecastWeather, HistoricalWeather


def fetch_openmeteo_data(openmeteo, url: str, params: Dict[str, Any]) -> List[WeatherApiResponse]:
    """Common function to fetch data from OpenMeteo API"""
    return openmeteo.weather_api(url, params=params, verify=False)


def prepare_weather_locations(config: Config) -> tuple[List[str], List[float], List[float]]:
    """Get weather locations and extract labels, latitudes, and longitudes"""
    weather_locations = get_weather_locations(config.get_weather_location_metadata_path())
    location_labels, latitudes, longitudes = zip(*[
        (location.label, location.latitude, location.longitude)
        for location in weather_locations
    ])
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


def persist_weather_data(
    config: Config,
    df: pd.DataFrame,
    filename: str,
    weather_model_class,
    clear_existing: bool = False
) -> None:
    """Common function to persist weather data to database or CSV"""
    if config.use_database_weather():
        save_dataframe_to_db(config, df, weather_model_class, clear_existing)
    else:
        save_dataframe_to_csv(config, df, filename)


def save_dataframe_to_db(
    config: Config,
    df: pd.DataFrame,
    weather_model_class,
    clear_existing: bool = False
) -> None:
    """
    Save DataFrame to database, optionally clearing existing data.

    :param config: Configuration object
    :param df: DataFrame containing weather data
    :param weather_model_class: Class representing the database model
           (i.e., HistoricalWeather or ForecastWeather)
    :param clear_existing: If True, clear existing data in the table before inserting new data
           Default is False.
    :return: None
    """
    db_client = DatabaseConnection(config)

    if getattr(weather_model_class, "__name__") not in ["HistoricalWeather", "ForecastWeather"]:
        raise ValueError(f"weather_model_class must be either HistoricalWeather or ForecastWeather, got {weather_model_class.__name__}")

    with db_client.engine.connect() as conn:
        with Session(bind=conn) as session:
            if clear_existing:
                # Empty the table for forecast data to replace it with new data
                print(f"Emptying the table for {weather_model_class.__name__} data...")
                session.query(weather_model_class).delete()

            # Convert DataFrame to weather objects
            df = df.drop(columns=["forecast_latitude"])
            df = df.drop(columns=["forecast_longitude"])
            weather_objects = weather_model_class.from_dataframe(df)

            # Persist to database
            session.add_all(weather_objects)
            session.commit()
            print(f"Inserted {len(weather_objects)} {weather_model_class.__name__} values into the database.")


def save_dataframe_to_csv(config, df, filename) -> None:
    """Save DataFrame to CSV file with timestamped filename"""
    data_path = config.get_store_base_path()
    basename = data_path + filename
    file = "{}_{:%Y-%m-%d}.csv".format(
        basename, datetime.datetime.now()
    )
    df.to_csv(file, index=False)


def __get_variable_values_as_numpy(daily: VariablesWithTime, variable_index: int, variable_name: Optional[str]) -> np.ndarray:
    """
    Helper function to extract variable values as numpy array from daily data.
    """
    variable: Optional[VariableWithValues] = daily.Variables(variable_index)
    if variable is None:
        raise ValueError(f"Variable index {variable_index} {' (' + variable_name + ')' if variable_name else ''} not found in daily data.")
    return variable.ValuesAsNumpy()


def parse_daily_data(response: WeatherApiResponse, forecast: bool) -> Optional[dict]:
    """
    Extract daily weather data from the WeatherApiResponse object.
    Returns a dictionary with date, latitude, longitude, and various weather variables.

    :param response: WeatherApiResponse object containing the weather data.
    :param forecast: Boolean indicating if the data is for forecast or historical (forecast data includes additional variables).
    :return: Dictionary with daily weather data as Numpy Arrays or None if no daily data is available.
    """
    daily = response.Daily()
    if daily is None:
        print("No daily data available in the response.")
        return None
    
    # Extract variables as numpy arrays
    # NOTE: the order of variables needs to be the same as requested.
    res = {
        "date": pd.date_range(
            start=pd.to_datetime(daily.Time(), unit="s", utc=True),
            end=pd.to_datetime(daily.TimeEnd(), unit="s", utc=True),
            freq=pd.Timedelta(seconds=daily.Interval()),
            inclusive="left",
        ),
        "forecast_latitude": response.Latitude(),
        "forecast_longitude": response.Longitude(),
        "temperature_2m_max": __get_variable_values_as_numpy(daily, 0, "temperature_2m_max"),
        "temperature_2m_min": __get_variable_values_as_numpy(daily, 1, "temperature_2m_min"),
        "precipitation_sum": __get_variable_values_as_numpy(daily, 2, "precipitation_sum"),
        "rain_sum": __get_variable_values_as_numpy(daily, 3, "rain_sum"),
        "precipitation_hours": __get_variable_values_as_numpy(daily, 4, "precipitation_hours"),
    }

    if forecast:
        res["precipitation_probability_max"] = __get_variable_values_as_numpy(daily, 5, "precipitation_probability_max")
        res["wind_speed_10m_max"] = __get_variable_values_as_numpy(daily, 6, "wind_speed_10m_max")
    
    return res
