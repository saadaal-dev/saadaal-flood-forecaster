import datetime
from typing import List, Dict, Any, Optional

import numpy as np
import pandas as pd
from openmeteo_sdk import VariableWithValues
from openmeteo_sdk import VariablesWithTime
from openmeteo_sdk import WeatherApiResponse
from sqlalchemy.dialects.postgresql import insert
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
        # print(f"Coordinates {response.Latitude()}°N {response.Longitude()}°E")
        # print(f"Elevation {response.Elevation()} m asl")
        # print(f"Timezone {response.Timezone()} {response.TimezoneAbbreviation()}")
        # print(f"Timezone difference to GMT+0 {response.UtcOffsetSeconds()} s")

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

    # Log DataFrame info before persisting
    print(f"DEBUG: Attempting to save {len(df)} rows to {weather_model_class.__name__}")
    if len(df) > 0:
        print(f"DEBUG: Date range: {df['date'].min()} to {df['date'].max()}")
        print(f"DEBUG: Unique locations: {df['location_name'].unique().tolist()}")
        print(f"DEBUG: Sample data:\n{df.head(3)}")

    with db_client.engine.connect() as conn:
        with Session(bind=conn) as session:
            try:
                if clear_existing:
                    # Empty the table for forecast data to replace it with new data
                    print(f"Emptying the table for {weather_model_class.__name__} data...")
                    session.query(weather_model_class).delete()

                # Convert DataFrame to weather objects
                df = df.drop(columns=["forecast_latitude"])
                df = df.drop(columns=["forecast_longitude"])

                # Persist to database - Use UPSERT for both historical and forecast to handle unique constraints
                table = weather_model_class.__table__
                data = df.to_dict(orient="records")

                print(f"DEBUG: Preparing upsert for {len(data)} records")

                insert_stmt = insert(table).values(data)
                update_dict = {c.name: insert_stmt.excluded[c.name] for c in table.columns if c.name != "id"}
                upsert_stmt = insert_stmt.on_conflict_do_update(
                    index_elements=["location_name", "date"],
                    set_=update_dict
                )
                result = session.execute(upsert_stmt)
                session.commit()

                print(f"DEBUG: Upsert executed, rows affected: {result.rowcount}")
                print(f"Upserted {len(df)} {weather_model_class.__name__} values into the database.")

                # Verify the data was actually written
                from sqlalchemy import select, func
                verify_stmt = select(func.count()).select_from(table).where(
                    table.c.date >= df['date'].min()
                )
                count_result = session.execute(verify_stmt).scalar()
                print(f"DEBUG: Verification - Found {count_result} total rows with date >= {df['date'].min()}")


            except Exception as e:
                print(f"ERROR: Failed to save {weather_model_class.__name__} to database: {e}")
                print(f"ERROR: Exception type: {type(e).__name__}")
                import traceback
                traceback.print_exc()
                session.rollback()
                raise


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
