# Methods to load the data from the database
import json
from datetime import datetime, timedelta
from typing import Iterable

import pandas as pd
import pandera.pandas as pa
import pandera.typing as pat
from sqlalchemy import select

from src.flood_forecaster.data_model.river_level import HistoricalRiverLevel, StationDataFrameSchema
from src.flood_forecaster.data_model.weather import HistoricalWeather, ForecastWeather, WeatherDataFrameSchema
from src.flood_forecaster.utils.configuration import Config, DataSourceType
from src.flood_forecaster.utils.database_helper import DatabaseConnection


@pa.check_types
def load_history_weather_db(config: Config, locations: Iterable[str], date_begin: datetime, date_end: datetime) -> \
        pat.DataFrame[WeatherDataFrameSchema]:
    """
    Loads the history weather data from the database and returns it as a pandas dataframe
    :param config:
    :param locations:
    :param date_begin:
    :param date_end:
    :return: pandas dataframe
    """
    stmt = (select(HistoricalWeather)
            .where(HistoricalWeather.location_name.in_(locations))
            .where(HistoricalWeather.date >= date_begin)
            .where(HistoricalWeather.date <= date_end))
    database = DatabaseConnection(config)
    return pd.read_sql(stmt, database.engine)


@pa.check_types
def load_forecast_weather_db(config: Config, locations: Iterable[str], date_begin: datetime, date_end: datetime) -> \
        pat.DataFrame[WeatherDataFrameSchema]:
    stmt = (select(ForecastWeather)
            .where(ForecastWeather.location_name.in_(locations))
            .where(ForecastWeather.date >= date_begin)
            .where(ForecastWeather.date <= date_end))
    database = DatabaseConnection(config)
    return pd.read_sql(stmt, database.engine)


@pa.check_types
def load_river_level_db(config: Config, locations: Iterable[str], date_begin: datetime, date_end: datetime) -> \
        pat.DataFrame[StationDataFrameSchema]:
    stmt = (select(HistoricalRiverLevel)
            .where(HistoricalRiverLevel.location_name.in_(locations))
            .where(HistoricalRiverLevel.date >= date_begin)
            .where(HistoricalRiverLevel.date <= date_end))
    database = DatabaseConnection(config)
    return pd.read_sql(stmt, database.engine)


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


@pa.check_types
def load_weather_csv(path, start_date=None, end_date=None) -> pat.DataFrame:
    """
    Load general weather data from a csv file and return a dataframe
    """
    csv = __load_csv(path, start_date, end_date, datefmt="%Y-%m-%d %H:%M:%S%z")
    
    if 'Unnamed: 0' in csv.columns:
        csv = csv.drop(columns=['Unnamed: 0'])

    # Keep only date part of the datetime and without timezone information
    csv["date"] = pd.to_datetime(csv["date"]).dt.floor("D").dt.tz_localize(None)

    return csv


@pa.check_types
def load_history_weather_csv(config: Config, locations: Iterable[str],
                             start_date=None, end_date=None) -> pat.DataFrame[WeatherDataFrameSchema]:
    """
    Load historical weather data
    
    Dataframe columns:
        - location: str
        - date: datetime
        - precipitation_sum: float
        - precipitation_hours: float
    """
    path = config.load_data_csv_config()["weather_history_data_path"]
    return load_weather_csv(path, start_date, end_date).loc[lambda df: df["location"].isin(locations)]


@pa.check_types
def load_forecast_weather_csv(config: Config, locations: Iterable[str], start_date=None, end_date=None) -> \
        pat.DataFrame[ForecastWeather]:
    path = config.load_data_csv_config()["weather_forecast_data_path"]
    return load_weather_csv(path, start_date, end_date).loc[lambda df: df["location"].isin(locations)]


@pa.check_types
def load_river_level_csv(config: Config, locations: Iterable[str],
                         start_date=None, end_date=None) -> pat.DataFrame[StationDataFrameSchema]:
    """
    Load a station csv file and return a dataframe

    Dataframe columns:
        - location: str
        - date: datetime
        - level__m: float
    """
    path = config.load_data_csv_config()["river_stations_data_path"]
    return __load_csv(path, start_date, end_date, datefmt="%d/%m/%Y").loc[lambda df: df["location"].isin(locations)]


@pa.check_types
def write_history_weather_csv(config: Config, df: pat.DataFrame[WeatherDataFrameSchema]) -> None:
    """
    Write historical weather dataframe to CSV.

    Expects dataframe with columns:
        - location: str
        - date: datetime
        - precipitation_sum: float
        - precipitation_hours: float
    """
    path = config.load_data_csv_config()["write_weather_history_data_path"]
    try:
        df.to_csv(path, index=False)
    except Exception as e:
        print(f"Error writing CSV to {path}: {e}")

@pa.check_types
def write_forecast_weather_csv(config: Config, df: pat.DataFrame[ForecastWeather]) -> None:
    """
    Write forecast weather dataframe to CSV.

    Expects dataframe with columns:
        - location_name: str
        - date: datetime
        - temperature_2m_max: float
        - temperature_2m_min: float
        - precipitation_sum: float
        - rain_sum: float
        - precipitation_hours: float
        - precipitation_probability_max: float
        - wind_speed_10m_max: float
    """

    path = config.load_data_csv_config()["write_forecast_weather_data_path"]
    try:
        df.to_csv(path, index=False)
    except Exception as e:
        print(f"Error writing CSV to {path}: {e}")

@pa.check_types
def write_river_level_csv(config: Config, df: pat.DataFrame[StationDataFrameSchema]) -> None:
    """
    Write river level dataframe to CSV.

    Dataframe columns:
        - location: str
        - date: datetime
        - level__m: float
    """
    path = config.load_data_csv_config()["write_river_level_data_path"]
    try:
        df.to_csv(path, index=False)
    except Exception as e:
        print(f"Error writing CSV to {path}: {e}")


@pa.check_types
def write_history_weather_db(config: Config, df: pat.DataFrame[WeatherDataFrameSchema]) -> None:
    """
    Write historical weather dataframe to the database.

    Expects dataframe with columns matching the HistoricalWeather model.
    This will append rows to the HistoricalWeather table.
    """
    database = DatabaseConnection(config)
    table_name = getattr(HistoricalWeather, "__tablename__", "historical_weather")

    try:
        df = df.copy()
        # Normalize datetime columns for DB insertion
        for col in df.columns:
            if pd.api.types.is_datetime64_any_dtype(df[col]):
                df[col] = pd.to_datetime(df[col])

        df.to_sql(name=table_name, con=database.engine, if_exists="append", index=False)
    except Exception as e:
        print(f"Error writing historical weather to DB table '{table_name}': {e}")

@pa.check_types
def write_forecast_weather_db(config: Config, df: pat.DataFrame[ForecastWeather]) -> None:
    """
    Write forecast weather dataframe to the database.

    Expects dataframe with columns matching the ForecastWeather model.
    This will append rows to the ForecastWeather table.
    """
    database = DatabaseConnection(config)
    table_name = getattr(ForecastWeather, "__tablename__", "forecast_weather")

    try:
        df = df.copy()
        # Normalize datetime columns for DB insertion
        for col in df.columns:
            if pd.api.types.is_datetime64_any_dtype(df[col]):
                df[col] = pd.to_datetime(df[col])

        df.to_sql(name=table_name, con=database.engine, if_exists="append", index=False)
    except Exception as e:
        print(f"Error writing forecast weather to DB table '{table_name}': {e}")

@pa.check_types
def write_river_level_db(config: Config, df: pat.DataFrame[StationDataFrameSchema]) -> None:
    """
    Write river level dataframe to the database.

    Expects dataframe with columns matching the HistoricalRiverLevel model.
    This will append rows to the HistoricalRiverLevel table.
    """
    database = DatabaseConnection(config)
    table_name = getattr(HistoricalRiverLevel, "__tablename__", "river_level")

    try:
        df = df.copy()
        # Normalize datetime columns for DB insertion
        for col in df.columns:
            if pd.api.types.is_datetime64_any_dtype(df[col]):
                df[col] = pd.to_datetime(df[col])

        df.to_sql(name=table_name, con=database.engine, if_exists="append", index=False)
    except Exception as e:
        print(f"Error writing river level to DB table '{table_name}': {e}")

__WEATHER_HISTORY_LOAD_FNS = {
    DataSourceType.CSV: load_history_weather_csv,
    DataSourceType.DATABASE: load_history_weather_db,
}

__WEATHER_FORECAST_LOAD_FNS = {
    DataSourceType.CSV: load_forecast_weather_csv,
    DataSourceType.DATABASE: load_forecast_weather_db,
}

__RIVER_LEVEL_LOAD_FNS = {
    DataSourceType.CSV: load_river_level_csv,
    DataSourceType.DATABASE: load_river_level_db,
}

__WEATHER_HISTORY_WRITE_FNS = {
    DataSourceType.CSV: write_history_weather_csv,
    DataSourceType.DATABASE: write_history_weather_db,
}

__WEATHER_FORECAST_WRITE_FNS = {
    DataSourceType.CSV: write_forecast_weather_csv,
    DataSourceType.DATABASE: write_forecast_weather_db,
}

__RIVER_LEVEL_WRITE_FNS = {
    DataSourceType.CSV: write_river_level_csv,
    DataSourceType.DATABASE: write_river_level_db,
}


def __load(load_fns: dict, config: Config, location: str, date_begin: datetime, date_end: datetime):
    data_source_type = config.get_data_source_type()
    if data_source_type not in load_fns:
        raise ValueError(f"Unsupported data source type {data_source_type}, check config file")

    return load_fns[data_source_type](config, location, date_begin, date_end)


@pa.check_types
def load_history_weather(config: Config, location: str,
                         date_begin: datetime, date_end: datetime) -> pat.DataFrame[WeatherDataFrameSchema]:
    return __load(__WEATHER_HISTORY_LOAD_FNS, config, location, date_begin, date_end)


@pa.check_types
def load_forecast_weather(config: Config, location: str,
                          date_begin: datetime, date_end: datetime) -> pat.DataFrame[WeatherDataFrameSchema]:
    return __load(__WEATHER_FORECAST_LOAD_FNS, config, location, date_begin, date_end)


@pa.check_types
def load_river_level(config: Config, location: str,
                     date_begin: datetime, date_end: datetime) -> pat.DataFrame[StationDataFrameSchema]:
    return __load(__RIVER_LEVEL_LOAD_FNS, config, location, date_begin, date_end)


def load_modelling_weather(config: Config, locations=None) -> pat.DataFrame[WeatherDataFrameSchema]:
    """
    Load weather data for modelling.
    For simplicity this includes only historical data.

    Dataframe columns:
        - location: str
        - date: datetime
        - precipitation_sum: float
        - precipitation_hours: float
    """
    # QUICKFIX: load historical data for the last 5 years
    min_date = datetime.now() - timedelta(days=5 * 365)

    return load_history_weather(config, locations, min_date, datetime.now())


def load_modelling_river_levels(config: Config, locations=None) -> pat.DataFrame[StationDataFrameSchema]:
    """
    Load station data for modelling

    Dataframe columns:
        - location: str
        - date: datetime
        - level__m: float
    """
    # QUICKFIX: load historical data for the last 5 years
    min_date = datetime.now() - timedelta(days=5 * 365)

    return load_river_level(config, locations, min_date, datetime.now())


#  fn that returns a df from date_begin to date_end. priority to historical data,
#  filling with forecast data for the days that are not in the historical table (future days)
@pa.check_types
def load_inference_weather(config: Config, locations=None,
                           date=datetime.now()) -> pat.DataFrame[WeatherDataFrameSchema]:
    """
    Load weather data for inference

    Dataframe columns:
        - location: str
        - date: datetime
        - precipitation_sum: float
        - precipitation_hours: float
    """

    # ignore time information in date
    date = date.date()

    model_config = config.load_model_config()

    # load historical weather data for the last max(WEATHER_LAG) days
    # min_date: datetime = date - max(config.get("model", "WEATHER_LAG_DAYS"))
    min_date = date - timedelta(days=max(json.loads(model_config["weather_lag_days"])))

    # max_date: datetime = date - min(config.get("model", "WEATHER_LAG_DAYS")-1
    # LAG=0 is the current day, so it is part of the forecast
    max_date = date - timedelta(days=min(json.loads(model_config["weather_lag_days"])))

    today = datetime.now().date()

    # if max_date is in the future, we will need to load forecast data
    # exclude today from historical data
    # else, we will only load historical data
    if max_date >= today:
        history_max_date = today - timedelta(days=1)
    else:
        history_max_date = max_date

    acc = []
    if min_date < today:
        print("Loading inference data (history) from", min_date, "to", history_max_date)
        history_df = load_history_weather(config, locations, min_date, history_max_date)
        if locations is not None:
            acc.append(history_df[history_df["location"].isin(locations)])

    # load forecast weather data for the next min(WEATHER_LAG) days (forecast are negative lag) if necessary
    if max_date >= today:
        print("Loading inference data (forecast) from", date, "to", max_date)
        forecast_df = load_forecast_weather(config, locations, date, max_date)

        # filter locations
        if locations is not None:
            acc.append(forecast_df[forecast_df["location"].isin(locations)])

        return pd.concat(acc, axis=0, ignore_index=True)
    else:
        return history_df


@pa.check_types
def load_inference_river_levels(config: Config, locations=None,
                                date=datetime.now()) -> pat.DataFrame[StationDataFrameSchema]:
    """
    Load station data for inference

    Dataframe columns:
        - location: str
        - date: datetime
        - level__m: float
    """
    # ignore time information in date
    date = date.date()

    model_config = config.load_model_config()
    min_date = date - timedelta(days=max(json.loads(model_config["river_station_lag_days"])))
    max_date = date - timedelta(days=1)
    df = load_river_level(config, locations, min_date, max_date)

    # for each location, append row with empty values and index = date
    # this row is to ensure that the last day is included (corresponding to the date of the inference)
    df = pd.concat(
        [df, pd.DataFrame([{"location": location, "date": date, "level__m": 0.0} for location in locations])],
        ignore_index=True)

    return df
