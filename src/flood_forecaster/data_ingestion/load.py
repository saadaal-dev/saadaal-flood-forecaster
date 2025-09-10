# Methods to load the data from the database
import json
from datetime import date, datetime, timedelta
from typing import Iterable, Optional

import pandas as pd
import pandera.pandas as pa
from sqlalchemy import select

from src.flood_forecaster.data_model.river_level import HistoricalRiverLevel, StationDataFrameSchema
from src.flood_forecaster.data_model.weather import HistoricalWeather, ForecastWeather, WeatherDataFrameSchema
from src.flood_forecaster.utils.configuration import Config, DataSourceType
from src.flood_forecaster.utils.database_helper import DatabaseConnection


pat = pa.typing


# TODO: make date_begin and date_end optional, so that it is uniform with __load_csv
@pa.check_types
def load_history_weather_db(
    config: Config, locations: Iterable[str], date_begin: date, date_end: date
) -> pat.DataFrame[WeatherDataFrameSchema]:
    """
    Loads the history weather data from the database and returns it as a pandas dataframe
    :param config:
    :param locations:
    :param date_begin:
    :param date_end:
    :return: pandas dataframe
    """
    print(f"Loading history weather data from database for locations {locations} from {date_begin} to {date_end} (inclusives)")

    # QUICKFIX: transform dates into datetimes for DB interaction
    #           ignoring time information in date_begin and date_end
    _date_begin = pd.to_datetime(date_begin).replace(hour=0, minute=0, second=0, microsecond=0)
    _date_end = pd.to_datetime(date_end).replace(hour=0, minute=0, second=0, microsecond=0) + timedelta(days=1)

    stmt = (select(HistoricalWeather)
            .where(HistoricalWeather.location_name.in_(locations))
            .where(HistoricalWeather.date >= _date_begin)
            .where(HistoricalWeather.date <= _date_end))
    database = DatabaseConnection(config)
    df = pd.read_sql(stmt, database.engine)  # type: ignore (ensured by pandera)
    print(f"Loaded {len(df)} rows from the database")

    df['date'] = pd.to_datetime(df['date'], utc=True)  # TODO: verify UTC / timezone management
    df['date'] = df['date'].dt.date  # convert datetime to date
    df = df.rename(columns={
        "location_name": "location",
    })
    # Keep only relevant columns
    df = df[["location", "date", "precipitation_sum", "precipitation_hours"]]
    # df = df.dropna(subset=["precipitation_sum", "precipitation_hours"], how="any")  # drop rows with NaN in these columns
    df = df.fillna({
        "precipitation_sum": 0.0,  # fill NaN with 0.0 for precipitation_sum
        "precipitation_hours": 0.0,  # fill NaN with 0.0 for precipitation_hours
    })

    # Validate that we have data for all locations
    if not set(locations).issubset(set(df['location'].unique())):
        missing_locations = set(locations) - set(df['location'].unique())
        raise ValueError(f"Missing weather history data for locations: {missing_locations}")
    
    # Validate that we have data for all dates in the range
    all_dates = pd.date_range(start=date_begin, end=date_end).date
    unique_dates = df['date'].unique()
    if not set(all_dates).issubset(set(unique_dates)):
        missing_dates = set(all_dates) - set(unique_dates)

        # # FIXME: missing values
        # raise ValueError(f"Missing history weather data for dates: {missing_dates}")
        print("WARNING: Missing history weather data for dates:")
        for missing_date in sorted(missing_dates):
            print(f"  - {missing_date}")

        if date_end not in unique_dates:
            print(f"WARNING: Last date ({date_end}) is missing, it will be filled with forecast data later")

    return df  # type: ignore (ensured by pandera)


@pa.check_types
def load_forecast_weather_db(
    config: Config, locations: Iterable[str], date_begin: date, date_end: date
) -> pat.DataFrame[WeatherDataFrameSchema]:
    print(f"Loading forecast weather data from database for locations {locations} from {date_begin} to {date_end} (inclusives)")

    # QUICKFIX: transform dates into datetimes for DB interaction
    #           ignoring time information in date_begin and date_end
    _date_begin = pd.to_datetime(date_begin).replace(hour=0, minute=0, second=0, microsecond=0)
    _date_end = pd.to_datetime(date_end).replace(hour=0, minute=0, second=0, microsecond=0) + timedelta(days=1)

    stmt = (select(ForecastWeather)
            .where(ForecastWeather.location_name.in_(locations))
            .where(ForecastWeather.date >= _date_begin)
            .where(ForecastWeather.date < _date_end))
    database = DatabaseConnection(config)
    df = pd.read_sql(stmt, database.engine)  # type: ignore (ensured by pandera)
    print(f"Loaded {len(df)} rows from the database")
    
    df['date'] = pd.to_datetime(df['date'], utc=True)  # TODO: verify UTC / timezone management
    df['date'] = df['date'].dt.date  # convert datetime to date
    df = df.rename(columns={
        "location_name": "location",
    })
    # Keep only relevant columns
    df = df[["location", "date", "precipitation_sum", "precipitation_hours"]]

    # Validate that we have data for all locations
    if not set(locations).issubset(set(df['location'].unique())):
        missing_locations = set(locations) - set(df['location'].unique())
        raise ValueError(f"Missing weather forecast data for locations: {missing_locations}")
    
    # Validate that we have data for all dates in the range
    all_dates = pd.date_range(start=date_begin, end=date_end).date
    unique_dates = df['date'].unique()
    if not set(all_dates).issubset(set(unique_dates)):
        missing_dates = set(all_dates) - set(unique_dates)
        raise ValueError(f"Missing weather forecast data for dates: {missing_dates}")

    return df  # type: ignore (ensured by pandera)


@pa.check_types
def load_river_level_db(
    config: Config, locations: Iterable[str], date_begin: date, date_end: date
) -> pat.DataFrame[StationDataFrameSchema]:
    print(f"Loading river level data from database for locations {locations} from {date_begin} to {date_end} (inclusives)")

    stmt = (select(HistoricalRiverLevel)
            .where(HistoricalRiverLevel.location_name.in_(locations))
            .where(HistoricalRiverLevel.date >= date_begin)
            .where(HistoricalRiverLevel.date <= date_end))
    database = DatabaseConnection(config)
    df = pd.read_sql(stmt, database.engine)  # type: ignore (ensured by pandera)
    print(f"Loaded {len(df)} rows from the database")
    df['date'] = pd.to_datetime(df['date'], utc=True)  # TODO: verify UTC / timezone management
    df['date'] = df['date'].dt.date  # convert datetime to date
    df = df.rename(columns={
        "level_m": "level__m",
        "location_name": "location",
    })
    df = df.drop(columns=["id"])  # drop id column, not needed for the analysis

    # Validate that we have data for all locations
    if not set(locations).issubset(set(df['location'].unique())):
        missing_locations = set(locations) - set(df['location'].unique())
        raise ValueError(f"Missing river level data for locations: {missing_locations}")
    
    # Validate that we have data for all dates in the range
    all_dates = pd.date_range(start=date_begin, end=date_end).date
    if not set(all_dates).issubset(set(df['date'].unique())):
        missing_dates = set(all_dates) - set(df['date'].unique())
        
        # # FIXME: missing values
        # raise ValueError(f"Missing river level data for dates: {missing_dates}")
        print("WARNING: Missing river level data for dates:")
        for missing_date in sorted(missing_dates):
            print(f"  - {missing_date}")

    return df  # type: ignore (ensured by pandera)


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
def load_weather_csv(path, start_date: Optional[date] = None, end_date: Optional[date] = None) -> pat.DataFrame[WeatherDataFrameSchema]:
    """
    Load weather data from a csv file and return a dataframe
    
    Dataframe columns:
        - location: str
        - date: datetime
        - precipitation_sum: float
        - precipitation_hours: float
    """
    csv = __load_csv(path, start_date, end_date, datefmt="%Y-%m-%d %H:%M:%S%z")

    # Keep only date part of the datetime and without timezone information
    csv["date"] = pd.to_datetime(csv["date"]).dt.floor("D").dt.tz_localize(None)

    csv = csv[["location", "date", "precipitation_sum", "precipitation_hours"]]

    return csv  # type: ignore (ensured by pandera)


@pa.check_types
def load_history_weather_csv(
    config: Config, locations: Iterable[str], start_date: Optional[date] = None, end_date: Optional[date] = None
) -> pat.DataFrame[WeatherDataFrameSchema]:
    """
    Load historical weather data
    
    Dataframe columns:
        - location: str
        - date: datetime
        - precipitation_sum: float
        - precipitation_hours: float
    """
    print(f"Loading history weather data from database for locations {locations} from {start_date} to {end_date} (inclusives)")
    path = config.load_data_csv_config()["weather_history_data_path"]
    return load_weather_csv(path, start_date, end_date).loc[lambda df: df["location"].isin(locations)]


@pa.check_types
def load_forecast_weather_csv(
    config: Config, locations: Iterable[str], start_date: Optional[date] = None, end_date: Optional[date] = None
) -> pat.DataFrame[WeatherDataFrameSchema]:
    print(f"Loading weather forecast data from database for locations {locations} from {start_date} to {end_date} (inclusives)")
    path = config.load_data_csv_config()["weather_forecast_data_path"]
    return load_weather_csv(path, start_date, end_date).loc[lambda df: df["location"].isin(locations)]


@pa.check_types
def load_river_level_csv(
    config: Config, locations: Iterable[str], start_date: Optional[date] = None, end_date: Optional[date] = None
) -> pat.DataFrame[StationDataFrameSchema]:
    """
    Load a station csv file and return a dataframe

    Dataframe columns:
        - location: str
        - date: datetime
        - level__m: float
    """
    print(f"Loading river level data from database for locations {locations} from {start_date} to {end_date} (inclusives)")
    path = config.load_data_csv_config()["river_stations_data_path"]
    df = __load_csv(path, start_date, end_date, datefmt="%d/%m/%Y").loc[lambda df: df["location"].isin(locations)]  # type: ignore (ensured by pandera)
    df = df[["location", "date", "level__m"]]
    return df  # type: ignore (ensured by pandera)


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


def __load(load_fns: dict, config: Config, locations: Iterable[str], date_begin: date, date_end: date) -> pat.DataFrame:
    data_source_type = config.get_data_source_type()
    if data_source_type not in load_fns:
        raise ValueError(f"Unsupported data source type {data_source_type}, check config file")

    return load_fns[data_source_type](config, locations, date_begin, date_end)


@pa.check_types
def load_history_weather(
    config: Config, locations: Iterable[str], date_begin: date, date_end: date
) -> pat.DataFrame[WeatherDataFrameSchema]:
    return __load(__WEATHER_HISTORY_LOAD_FNS, config, locations, date_begin, date_end)


@pa.check_types
def load_forecast_weather(
    config: Config, locations: Iterable[str], date_begin: date, date_end: date
) -> pat.DataFrame[WeatherDataFrameSchema]:
    return __load(__WEATHER_FORECAST_LOAD_FNS, config, locations, date_begin, date_end)


@pa.check_types
def load_river_level(
    config: Config, locations: Iterable[str], date_begin: date, date_end: date
) -> pat.DataFrame[StationDataFrameSchema]:
    return __load(__RIVER_LEVEL_LOAD_FNS, config, locations, date_begin, date_end)


def load_modelling_weather(
    config: Config, locations: Iterable[str]
) -> pat.DataFrame[WeatherDataFrameSchema]:
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


def load_modelling_river_levels(
    config: Config, locations: Iterable[str]
) -> pat.DataFrame[StationDataFrameSchema]:
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
def load_inference_weather(
    config: Config, locations: Iterable[str], date=datetime.now()
) -> pat.DataFrame[WeatherDataFrameSchema]:
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

    weather_lag_days = json.loads(model_config["weather_lag_days"])

    # load historical weather data for the last max(WEATHER_LAG) days
    # min_date: datetime = date - max(config.get("model", "WEATHER_LAG_DAYS"))
    min_date = date - timedelta(days=max(weather_lag_days))

    # max_date: datetime = date - min(config.get("model", "WEATHER_LAG_DAYS")-1
    # LAG=0 is the current day, so it is part of the forecast
    max_date = date - timedelta(days=min(weather_lag_days))

    today = datetime.now().date()

    # if max_date is in the future, we will need to load forecast data
    # exclude today from historical data
    # else, we will only load historical data
    if max_date >= today:
        history_max_date = today - timedelta(days=1)
    else:
        history_max_date = max_date

    # TODO: REVIEW: odd logic
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

        return pd.concat(acc, axis=0, ignore_index=True)  # type: ignore (ensured by pandera)
    else:
        return history_df  # type: ignore (ensured by pandera)


@pa.check_types
def load_inference_river_levels(
    config: Config, locations: Iterable[str], date=datetime.now()
) -> pat.DataFrame[StationDataFrameSchema]:
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
        ignore_index=True
    )

    return df  # type: ignore (ensured by pandera)
