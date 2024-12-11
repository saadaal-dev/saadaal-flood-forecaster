from datetime import datetime, timedelta
import json
from typing import Dict, List
import numpy as np
import pandas as pd
import pandera as pa
from pandera.typing import Series

from ..utils.configuration import StationMapping


DEFAULT_STATION_LAG_DAYS = [1, 3, 7, 14]
DEFAULT_WEATHER_LAG_DAYS = [1, 3, 7, 14] + [0, -2, -6]
DEFAULT_FORECAST_DAYS = 1


class StationDataFrameSchema(pa.DataFrameModel):
    """
    Schema for station data.
    """
    location: Series[str]
    date: Series[pd.Timestamp]
    level__m: Series[float]

    class Config:
        strict = True
        coerce = True


class WeatherDataFrameSchema(pa.DataFrameModel):
    """
    Schema for weather data.
    """
    location: Series[str]
    date: Series[pd.Timestamp]
    precipitation_sum: Series[float]
    precipitation_hours: Series[float]

    class Config:
        strict = True
        coerce = True


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


def __load_csv(path, start_date=None, end_date=None, datefmt="%Y-%m-%d"):
    df = pd.read_csv(path)
    # convert date column to datetime and drop time information
    df["date"] = pd.to_datetime(df["date"], format=datefmt).dt.floor("D")

    if start_date is not None:
        # Ensure start_date is in the same timezone as df["date"]
        start_date = pd.to_datetime(start_date).tz_localize(df["date"].dt.tz)
        df = df[df["date"] >= start_date]
    if end_date is not None:
        # Ensure end_date is in the same timezone as df["date"]
        end_date = pd.to_datetime(end_date).tz_localize(df["date"].dt.tz)
        df = df[df["date"] <= end_date]

    return df


def load_weather_csv(path, start_date=None, end_date=None):
    """
    Load weather data
    
    Dataframe columns:
        - location: str
        - date: datetime
        - precipitation_sum: float
        - precipitation_hours: float
    """
    return __load_csv(path, start_date, end_date, datefmt="%Y-%m-%d %H:%M:%S%z")
    

def load_history_weather_csv(path, start_date=None, end_date=None):
    """
    Load historical weather data
    
    Dataframe columns:
        - location: str
        - date: datetime
        - precipitation_sum: float
        - precipitation_hours: float
    """
    return load_weather_csv(path, start_date, end_date)


def load_forecast_weather_csv(path, start_date=None, end_date=None):
    return load_weather_csv(path, start_date, end_date)


def load_inference_weather_csv(settings, locations=None, date=datetime.now()):
    """
    Load weather data for inference

    Dataframe columns:
        - location: str
        - date: datetime
        - precipitation_sum: float
        - precipitation_hours: float
    """

    # WARNING: the logic below is probably incorrect

    # load historical weather data for the last max(WEATHER_LAG) days
    # min_date: datetime = date - max(settings.get("model", "WEATHER_LAG_DAYS"))
    min_date = date - timedelta(days=max(json.loads(settings.get("model", "WEATHER_LAG_DAYS"))))

    # max_date: datetime = date - min(settings.get("model", "WEATHER_LAG_DAYS")-1
    # LAG=0 is the current day, so it is part of the forecast
    max_date = date - timedelta(days=min(json.loads(settings.get("model", "WEATHER_LAG_DAYS"))))

    today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)

    # if max_date is in the future, we will need to load forecast data
    # exclude today from historical data
    # else, we will only load historical data
    if max_date >= today:
        history_max_date = today - timedelta(days=1)
    else:
        history_max_date = max_date

    print("Loading historical data from", min_date, "to", history_max_date)
    history_df = load_history_weather_csv(settings.get("csv", "WEATHER_HISTORY_DATA_PATH"), min_date, history_max_date)
    if locations is not None:
        history_df = history_df[history_df["location"].isin(locations)]

    # load forecast weather data for the next min(WEATHER_LAG) days (forecast are negative lag) if necessary
    if max_date > today:
        print("Loading forecast data")
        forecast_df = load_forecast_weather_csv(settings.get("csv", "WEATHER_FORECAST_DATA_PATH"), date, max_date)

        # filter locations
        if locations is not None:
            forecast_df = forecast_df[forecast_df["location"].isin(locations)]

        return pd.concat([history_df, forecast_df], axis=0)
    else:
        return history_df


# def load_inference_weather_db(settings, locations, date=datetime.now()):
#     # load historical weather data for the last max(WEATHER_LAG) days
#     history_df = load_history_weather_db(settings, location, date - max(settings.WEATHER_LAG_DAYS), date)

#     # load forecast weather data for the next min(WEATHER_LAG) days (forecast are negative lag)
#     forecast_df = load_forecast_weather_db(settings, location, date, date - min(settings.WEATHER_LAG_DAYS))

#     return pd.concat([history_df, forecast_df], axis=0)


def load_station_csv(path, start_date=None, end_date=None):
    """
    Load a station csv file and return a dataframe

    Dataframe columns:
        - location: str
        - date: datetime
        - level__m: float
    """
    return __load_csv(path, start_date, end_date, datefmt="%d/%m/%Y")


def load_inference_station_csv(settings, locations=None, date=datetime.now()):
    """
    Load station data for inference

    Dataframe columns:
        - location: str
        - date: datetime
        - level__m: float
    """
    min_date = date - timedelta(days=max(json.loads(settings.get("model", "WEATHER_LAG_DAYS"))))
    max_date = date - timedelta(days=1)
    df = load_station_csv(settings.get("csv", "RIVER_STATIONS_DATA_PATH"), min_date, max_date)
    if locations is not None:
        df = df[df["location"].isin(locations)]
    
    # for each location, append row with empty values and index = date
    # this row is to ensure that the last day is included (corresponding to the date of the inference)
        df = pd.concat([df, pd.DataFrame([{"location": location, "date": date, "level__m": 0.0} for location in locations])], ignore_index=True)
    
    return df
