from datetime import datetime, timedelta
import json
from typing import Dict, List
import numpy as np
import pandas as pd
import pandera as pa
from pandera.typing import Series

from ..utils.configuration import StationMapping
from ..data_ingestion.load import StationDataFrameSchema, WeatherDataFrameSchema


DEFAULT_STATION_LAG_DAYS = [1, 3, 7, 14]
DEFAULT_WEATHER_LAG_DAYS = [1, 3, 7, 14] + [0, -2, -6]
DEFAULT_FORECAST_DAYS = 1


ModellingDataFrameSchema = pa.DataFrameSchema({
    "location": pa.Column(str),
    "date": pa.Column(pa.DateTime),
    "level__m": pa.Column(float),
    "[a-zA-Z0-9_]+__lag\d+__level__m": pa.Column(pa.Float, regex=True),
    "[a-zA-Z0-9_]+__lag\d+__precipitation_sum": pa.Column(pa.Float, regex=True),
    "[a-zA-Z0-9_]+__lag\d+__precipitation_hours": pa.Column(pa.Float, regex=True),
    "[a-zA-Z0-9_]+__forecast\d+__precipitation_sum": pa.Column(pa.Float, regex=True),
    "[a-zA-Z0-9_]+__forecast\d+__precipitation_hours": pa.Column(pa.Float, regex=True),
    "month_sin": pa.Column(float),
    "month_cos": pa.Column(float),
    "dayofyear_sin": pa.Column(float),
    "dayofyear_cos": pa.Column(float),
    "y": pa.Column(float, nullable=True),
})
"""
Defining a pandera dynamic schema for the ML data.
This is the output of the preprocessing pipeline suitable for the ML model training/evaluation/inference.

Summary: 
 - location: str, 
 - date: datetime, 
 - level__m: float, 
 - {location}__lag{day}__level__m: float,
 - {location}__lag{day}__precipitation_sum: float, 
 - {location}__lag{day}__precipitation_hours: float,
 - {location}__forecast{day}__precipitation_sum: float,
 - {location}__forecast{day}__precipitation_hours: float
 - y: float

Where:
 - location can contain any alphanumeric character and "_"
 - day is a positive integer
 - forecast and lag are optional and are defined based on the input settings
"""

InferenceDataFrameSchema = ModellingDataFrameSchema.remove_columns(["y"])
"""
Schema for inference data (no target column).
"""


def preprocess_station(station_df: StationDataFrameSchema, lag_days=DEFAULT_STATION_LAG_DAYS, only_lag_columns=False):
    """
    Preprocess a single station dataframe:
     - add lagged values for the level__m column
    """

    if only_lag_columns:
        df = station_df[[]]
    else:
        df = station_df[["level__m"]]

    for lag_days in lag_days:
        df = df.merge(station_df[["level__m"]].shift(lag_days).add_prefix(f"lag{lag_days:02d}__"), left_index=True, right_index=True)
    
    return df


def preprocess_all_stations(ref_station_df: StationDataFrameSchema, upstream_station_dfs: Dict[str, StationDataFrameSchema], lag_days=DEFAULT_STATION_LAG_DAYS):
    # """
    # Preprocess all station dataframes:
    #  - add lagged values for the level__m column on all stations
    #  - remove rows with empty lagged values
    #  - merge all station data on a line (ref + upstreams)
    # """

    acc_df = preprocess_station(ref_station_df, lag_days, only_lag_columns=False).reset_index(level=(0,))

    for station, station_df in upstream_station_dfs.items():
        # standardize station column names (lowercase, remove spaces)
        station_prefix = station.lower().replace(" ", "_")

        df = preprocess_station(station_df.droplevel(0), lag_days, only_lag_columns=True).add_prefix(f"{station_prefix}__")

        # add station data without empty lag values
        acc_df = acc_df.merge(df[max(lag_days):], left_index=True, right_index=True)

    return acc_df


def preprocess_weather(weather_df: WeatherDataFrameSchema, lag_days=DEFAULT_WEATHER_LAG_DAYS):
    """
    Preprocess a single station dataframe:
     - add lagged values for the precipitation_sum and precipitation_hours columns

    NOTE: negative values are forecasts
    NOTE: assuming that the weather data is already sorted by station and date
    """
    # df = weather_df[["precipitation_sum", "precipitation_hours"]]
    df = weather_df[[]]  # keep only lag values in the final dataframe

    for l in lag_days:
        shift_df = weather_df[["precipitation_sum", "precipitation_hours"]].shift(l)
        if l <= 0:
            # NOTE: forecast values are negative or 0, 0 is today's forecast, -1 is tomorrow's forecast, etc.
            shift_df = shift_df.add_prefix(f"forecast{-l+1:02d}__")
        else:
            shift_df = shift_df.add_prefix(f"lag{l:02d}__")
        df = df.merge(shift_df, left_index=True, right_index=True)
    
    # QUICKFIX: make all columns float
    return df.astype(float)


def preprocess_all_weather(weather_dfs: Dict[str, WeatherDataFrameSchema], lag_days=DEFAULT_WEATHER_LAG_DAYS):
    acc_df = None
    for weather_location, weather_df in weather_dfs.items():
        # standardize station column names (lowercase, remove spaces)
        weather_location_prefix = weather_location.lower().replace(" ", "_")
        
        df = preprocess_weather(weather_df.droplevel(0), lag_days).add_prefix(f"{weather_location_prefix}__")

        if acc_df is None:
            acc_df = df
        else:
            # add weather data without empty lag values
            acc_df = acc_df.merge(df[max(lag_days):], left_index=True, right_index=True)

    return acc_df


def preprocess_diff(
    station_metadata: StationMapping, 
    stations_df: StationDataFrameSchema, weather_df: WeatherDataFrameSchema, 
    station_lag_days=DEFAULT_STATION_LAG_DAYS, weather_lag_days=DEFAULT_WEATHER_LAG_DAYS,
    forecast_days=DEFAULT_FORECAST_DAYS,
    infer=False,
) -> pd.DataFrame:
    """
    Preprocess the data for the ML model.
    
    The preprocessing steps include:
        - Extract reference station data
        - Extract upstream station data
        - Extract weather data
        - Preprocess data (add lagged values)
        - Aggregate data into final structure
        - Define target variable (y) as the difference between the current level and the lagged level
    """
    stations_df = stations_df.set_index(["location", "date"]).sort_index()
    weather_df = weather_df.set_index(["location", "date"]).sort_index()

    # extract reference station data
    ref_station_df = stations_df[stations_df.index.get_level_values("location") == station_metadata.location]

    # extract upstream station data
    upstream_station_dfs = {}
    for upstream_station in station_metadata.upstream_stations:
        upstream_station_df = stations_df[stations_df.index.get_level_values("location") == upstream_station]
        upstream_station_dfs[upstream_station] = upstream_station_df
    
    # extract weather data
    weather_dfs = {}
    for weather_condition in station_metadata.weather_locations:
        weather_location_df = weather_df[weather_df.index.get_level_values("location") == weather_condition]
        weather_dfs[weather_condition] = weather_location_df

    # preprocess data
    stations_df = preprocess_all_stations(ref_station_df, upstream_station_dfs, lag_days=station_lag_days)
    weathers_df = preprocess_all_weather(weather_dfs, lag_days=weather_lag_days)
    df = pd.merge(stations_df, weathers_df, left_index=True, right_index=True)
    df = df.reset_index()
    
    if not infer:
        if forecast_days > 1:
            # shift for output data of <forecast_days>-1 (-1 since y contains the next day prediction by default)
            shift = -forecast_days+1
            df['level__m'] = df['level__m'].shift(shift)

            # data usable for a forecast (without output label, only input data):
            # # forecast dates (last <forecast_days> days not available)
            # forecast_df = df[shift:]

            # remove null entries (last <forecast_days> days not available)
            df = df[:shift]
        
        # apply final structure
        df['y'] = df['level__m'] - df['lag01__level__m']
    
    # data augmentation: add date features
    df['month'] = df['date'].dt.month
    df['dayofyear'] = df['date'].dt.dayofyear

    # apply circular encoding to date features
    df['month_sin'] = df['month'].apply(lambda x: np.sin(2*np.pi*x/12))
    df['month_cos'] = df['month'].apply(lambda x: np.cos(2*np.pi*x/12))
    df['dayofyear_sin'] = df['dayofyear'].apply(lambda x: np.sin(2*np.pi*x/365))
    df['dayofyear_cos'] = df['dayofyear'].apply(lambda x: np.cos(2*np.pi*x/365))

    # # drop redundant date features
    # df = df.drop(columns=['month', 'dayofyear'])

    # QA
    count_total = len(df.index)
    # ignore y and level__m columns since they can contain NA values
    if infer:
        df = df.dropna(subset=[c for c in df.columns if c not in ["y", "level__m"]])
    else:
        df = df.dropna()
    count_na = count_total - len(df.index)
    if count_na > 0:
        print(f"WARNING: {count_na} rows with NA values were removed from the dataset.")

    if infer:
        InferenceDataFrameSchema.validate(df)
    else:
        ModellingDataFrameSchema.validate(df)

    return df
