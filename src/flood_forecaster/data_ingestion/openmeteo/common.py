from typing import Optional

from openmeteo_sdk.WeatherApiResponse import WeatherApiResponse
from openmeteo_sdk.VariablesWithTime import VariablesWithTime
from openmeteo_sdk.VariableWithValues import VariableWithValues
import pandas as pd
import numpy as np

from src.flood_forecaster.utils.database_helper import DatabaseConnection
from src.flood_forecaster.utils.configuration import Config


def start_database_connection(config: Config):
    return DatabaseConnection(config)


def get_station_data(config: Config, get_data_function , get_forecast_function, manage_function, database_connection):
    print(f"Reading {get_data_function} data...")
    data = get_data_function()
    latitudes = [s.latitude for s in data]
    longitudes = [s.longitude for s in data]

    responses = get_forecast_function(latitudes, longitudes, config)
    if responses is not None:
        manage_function(config, data, responses, database_connection)


def append_station_information(response: WeatherApiResponse, station, function):
    # Get the daily data as a pandas DataFrame,
    daily_data = function(response)  # We will apply the function based on the type of data we want (actual or historical)

    # Check if the station is an object type "Station" or "distinct"

    daily_data["location_name"] = station.label
    
    df = pd.DataFrame(data=daily_data)
    print(f"Daily data for {station.label}")
    return df


def __get_variable_values_as_numpy(daily: VariablesWithTime, variable_index: int, variable_name: Optional[str]) -> np.ndarray:
    """
    Helper function to extract variable values as numpy array from daily data.
    """
    variable: Optional[VariableWithValues] = daily.Variables(variable_index)
    if variable is None:
        raise ValueError(f"Variable index {variable_index} {' (' + variable_name + ')' if variable_name else ''} not found in daily data.")
    return variable.ValuesAsNumpy()


def get_daily_data(response: WeatherApiResponse, forecast: bool) -> Optional[dict]:
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
