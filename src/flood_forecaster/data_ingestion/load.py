# Methods to load the data from the database
import json
from datetime import date, datetime, timedelta
from typing import Iterable, Optional

import numpy as np
import pandas as pd
import pandera.pandas as pa
from sqlalchemy import select, func

from flood_forecaster.data_model.river_level import HistoricalRiverLevel, StationDataFrameSchema
from flood_forecaster.data_model.weather import HistoricalWeather, ForecastWeather, WeatherDataFrameSchema
from flood_forecaster.data_model.sensor_readings import SensorReading, SensorRainfallDataFrameSchema
from flood_forecaster.utils.configuration import Config, DataSourceType
from flood_forecaster.utils.database_helper import DatabaseConnection
from flood_forecaster.utils.logging_config import get_logger
from flood_forecaster.utils.geo import build_sensor_location_mapping


pat = pa.typing
logger = get_logger(__name__)


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
    logger.info(
        f"Loading history weather data from database for locations {locations} from {date_begin} to {date_end} (inclusives)")

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
    logger.info(f"Loaded {len(df)} rows from the database")

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
    
    # RESILIENCY: drop duplicate entries (if any)
    df_count = len(df)
    df = df.drop_duplicates(subset=["location", "date"], keep="last")
    if len(df) < df_count:
        logger.warning(f"Dropped {df_count - len(df)} duplicate weather entries")

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
        logger.warning("WARNING: Missing history weather data for dates:")
        for missing_date in sorted(missing_dates):
            logger.warning(f"  - {missing_date}")

        if date_end not in unique_dates:
            logger.warning(f"WARNING: Last date ({date_end}) is missing, it will be filled with forecast data later")

    return df  # type: ignore (ensured by pandera)


@pa.check_types
def load_forecast_weather_db(
    config: Config, locations: Iterable[str], date_begin: date, date_end: date
) -> pat.DataFrame[WeatherDataFrameSchema]:
    logger.info(
        f"Loading forecast weather data from database for locations {locations} from {date_begin} to {date_end} (inclusives)")

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
    logger.info(f"Loaded {len(df)} rows from the database")

    df['date'] = pd.to_datetime(df['date'], utc=True)  # TODO: verify UTC / timezone management
    df['date'] = df['date'].dt.date  # convert datetime to date
    df = df.rename(columns={
        "location_name": "location",
    })
    # Keep only relevant columns
    df = df[["location", "date", "precipitation_sum", "precipitation_hours"]]
    
    # RESILIENCY: drop forecast duplicate entries (if any)
    df_count = len(df)
    df = df.drop_duplicates(subset=["location", "date"], keep="last")
    if len(df) < df_count:
        logger.warning(f"Dropped {df_count - len(df)} duplicate forecast weather entries")

    # Validate that we have data for all locations
    if not set(locations).issubset(set(df['location'].unique())):
        missing_locations = set(locations) - set(df['location'].unique())
        logger.error(f"ERROR: Missing weather forecast data for locations: {missing_locations}")
        logger.debug(f"DEBUG: Requested locations: {sorted(locations)}")
        logger.debug(f"DEBUG: Available locations in DB: {sorted(df['location'].unique().tolist())}")
        logger.debug(f"DEBUG: Query date range: {date_begin} to {date_end}")
        logger.debug(
            f"DEBUG: Available date range in results: {df['date'].min() if len(df) > 0 else 'N/A'} to {df['date'].max() if len(df) > 0 else 'N/A'}")

        # Check what data exists for these missing locations
        db = DatabaseConnection(config)
        with db.engine.connect() as conn:
            for loc in missing_locations:
                stmt = select(func.max(ForecastWeather.date)).where(ForecastWeather.location_name == loc)
                max_date = conn.execute(stmt).scalar()
                logger.debug(f"DEBUG: Last forecast date for '{loc}': {max_date}")

        raise ValueError(f"Missing weather forecast data for locations: {missing_locations}")
    
    # Validate that we have data for all dates in the range
    all_dates = pd.date_range(start=date_begin, end=date_end).date
    unique_dates = df['date'].unique()
    if not set(all_dates).issubset(set(unique_dates)):
        missing_dates = set(all_dates) - set(unique_dates)

        # Changed from ERROR to WARNING - allow fill logic to handle missing dates
        logger.warning(f"WARNING: Missing weather forecast data for dates: {sorted(missing_dates)}")
        logger.debug(f"DEBUG: Expected {len(all_dates)} dates from {date_begin} to {date_end}")
        logger.debug(f"DEBUG: Got {len(unique_dates)} unique dates")
        logger.debug(f"DEBUG: Data by location:")
        for loc in locations:
            loc_data = df[df['location'] == loc]
            if len(loc_data) > 0:
                logger.debug(
                    f"  - {loc}: {len(loc_data)} rows, dates {loc_data['date'].min()} to {loc_data['date'].max()}")
            else:
                logger.debug(f"  - {loc}: NO DATA")
        logger.warning(f"WARNING: Missing dates will be filled by interpolation in load_inference_weather()")
        # Don't raise - let the fill logic handle it

    return df  # type: ignore (ensured by pandera)


@pa.check_types
def load_river_level_db(
    config: Config, locations: Iterable[str], date_begin: date, date_end: date
) -> pat.DataFrame[StationDataFrameSchema]:
    logger.debug(
        f"Loading river level data from database for locations {locations} from {date_begin} to {date_end} (inclusives)")

    stmt = (select(HistoricalRiverLevel)
            .where(HistoricalRiverLevel.location_name.in_(locations))
            .where(HistoricalRiverLevel.date >= date_begin)
            .where(HistoricalRiverLevel.date <= date_end))
    database = DatabaseConnection(config)
    df = pd.read_sql(stmt, database.engine)  # type: ignore (ensured by pandera)
    logger.info(f"Loaded {len(df)} rows from the database")
    df['date'] = pd.to_datetime(df['date'], utc=True)  # TODO: verify UTC / timezone management
    df['date'] = df['date'].dt.date  # convert datetime to date
    df = df.rename(columns={
        "level_m": "level__m",
        "location_name": "location",
    })
    df = df.drop(columns=["id"])  # drop id column, not needed for the analysis

    # RESILIENCY: drop duplicate entries (if any)
    df_count = len(df)
    df = df.drop_duplicates(subset=["location", "date"], keep="last")
    if len(df) < df_count:
        logger.debug(f"Dropped {df_count - len(df)} duplicate river level entries")

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
        logger.warning("WARNING: Missing river level data for dates:")
        for missing_date in sorted(missing_dates):
            logger.warning(f"  - {missing_date}")

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
    logger.debug(
        f"Loading history weather data from database for locations {locations} from {start_date} to {end_date} (inclusives)")
    path = config.load_data_csv_config()["weather_history_data_path"]
    return load_weather_csv(path, start_date, end_date).loc[lambda df: df["location"].isin(locations)]


@pa.check_types
def load_forecast_weather_csv(
    config: Config, locations: Iterable[str], start_date: Optional[date] = None, end_date: Optional[date] = None
) -> pat.DataFrame[WeatherDataFrameSchema]:
    logger.debug(
        f"Loading weather forecast data from database for locations {locations} from {start_date} to {end_date} (inclusives)")
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
    logger.debug(
        f"Loading river level data from database for locations {locations} from {start_date} to {end_date} (inclusives)")
    path = config.load_data_csv_config()["river_stations_data_path"]
    df = __load_csv(path, start_date, end_date, datefmt="%d/%m/%Y").loc[lambda df: df["location"].isin(locations)]  # type: ignore (ensured by pandera)
    df = df[["location", "date", "level__m"]]
    return df  # type: ignore (ensured by pandera)


_SENSOR_INVALID_VALUES = frozenset({"---", "", "null", "-999.99", "0", "0.0"})


def _clean_sensor_value(series: pd.Series) -> pd.Series:
    """
    Clean the raw VARCHAR 'value' column from public.sensor_readings.
    Casts to float, replacing known sentinel strings and true nulls with NaN.
    Negative values (except valid small negatives) are also dropped.

    Known invalid sentinels: '---', '', 'NULL', '-999.99', '0', '0.0'
    """
    cleaned = series.str.strip().str.lower()
    cleaned = cleaned.where(~cleaned.isin(_SENSOR_INVALID_VALUES), other=float("nan"))
    numeric = pd.to_numeric(cleaned, errors="coerce")
    # drop implausible negatives (sensor error codes below -100)
    numeric = numeric.where(numeric >= -100, other=float("nan"))
    return numeric


@pa.check_types
def load_sensor_rainfall_db(
    config: Config, locations: Iterable[str], date_begin: date, date_end: date
) -> pat.DataFrame[SensorRainfallDataFrameSchema]:
    """
    Load daily rainfall totals from public.sensor_readings for the given date range,
    filtered to rows whose sensor_meaning contains the configured rainfall keyword.

    Steps:
      1. Build sensor_id → location mapping via haversine nearest-neighbour.
      2. Query public.sensor_readings filtered by station_id, sensor_meaning, and reading_ts.
      3. Clean the raw VARCHAR 'value' column via _clean_sensor_value().
      4. Aggregate to daily totals per pipeline location.

    Returns a DataFrame[SensorRainfallDataFrameSchema] with columns:
        location, date, precipitation_sum, precipitation_hours
    """
    sensor_config = config.load_sensor_config()
    sensor_stations_path = sensor_config["sensor_stations_file"]
    forecast_locations_path = config.load_static_data_config()["weather_location_data_path"]
    max_distance_km = float(sensor_config.get("sensor_max_distance_km", 50))
    rainfall_keyword = sensor_config.get("rainfall_sensor_meaning", "Rainfall")

    # Build station_id → location label mapping restricted to the requested locations
    station_to_location = build_sensor_location_mapping(
        sensor_stations_path, forecast_locations_path, max_distance_km=max_distance_km
    )
    # Keep only sensor stations that map to one of the requested locations
    relevant_station_ids = [
        sid for sid, loc in station_to_location.items() if loc in set(locations)
    ]
    if not relevant_station_ids:
        logger.warning(f"No sensor stations found within {max_distance_km} km of locations {list(locations)}.")
        return pd.DataFrame(columns=["location", "date", "precipitation_sum", "precipitation_hours"])

    _date_begin = pd.to_datetime(date_begin).replace(hour=0, minute=0, second=0, microsecond=0)
    _date_end = pd.to_datetime(date_end).replace(hour=23, minute=59, second=59, microsecond=0)

    stmt = (
        select(SensorReading)
        .where(SensorReading.station_id.in_(relevant_station_ids))
        .where(SensorReading.sensor_meaning.ilike(f"%{rainfall_keyword}%"))
        .where(SensorReading.reading_ts >= _date_begin)
        .where(SensorReading.reading_ts <= _date_end)
    )
    database = DatabaseConnection(config)
    df = pd.read_sql(stmt, database.engine)
    logger.info(f"Loaded {len(df)} raw sensor rainfall rows from public.sensor_readings")

    if df.empty:
        logger.warning("No sensor rainfall data found for the given date range and stations.")
        return pd.DataFrame(columns=["location", "date", "precipitation_sum", "precipitation_hours"])

    # Clean value column
    df = df.copy()
    df["value_clean"] = _clean_sensor_value(df["value"])
    df = df.dropna(subset=["value_clean"]).copy()

    # Map station_id → pipeline location label
    df["location"] = df["station_id"].map(station_to_location)
    df = df.dropna(subset=["location"]).copy()

    # Parse reading_ts and aggregate to daily totals
    df["reading_ts"] = pd.to_datetime(df["reading_ts"], utc=True)
    df["date"] = df["reading_ts"].dt.date
    df["date"] = pd.to_datetime(df["date"])

    agg = (
        df.groupby(["location", "date"], as_index=False)
        .agg(
            precipitation_sum=("value_clean", "sum"),
            precipitation_hours=("value_clean", "count"),
        )
    )

    logger.info(f"Aggregated to {len(agg)} daily sensor rainfall rows")
    return agg  # type: ignore (ensured by pandera)


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


def __river_level_df_without_missing_dates(df: pd.DataFrame, location: str, date_begin: date, date_end: date):
    """
    Processes a DataFrame containing StationDataFrameSchema data to ensure that
    it includes entries for all dates within a specified range for the specified location.
    The input DataFrame is expected to have the following columns:
        - location: str
        - date: datetime
        - level__m: float
    It can contain multiple locations and may have missing dates for the specified location.
    This function will return a DataFrame that includes all dates from date_begin to date_end
    for the specified location ONLY, filling in any missing dates with a value.

    :param df: Input DataFrame with river level data.
    :param location: The location to filter and ensure complete date coverage.
    :param date_begin: The start date of the range (inclusive).
    :param date_end: The end date of the range (inclusive).
    :return: A DataFrame with complete date coverage for the specified location.
    """
    # fill values with the last available value
    # NOTE: This might not work well for all models, as it assumes that the last available value
    #       is a good approximation for the missing value.
    #       It is a good fit here since we are not relying on missing values in the training data.
    #       Doing so in the training data might lead to unexpected results, as the model might
    #       not understand that missing values are filled with the last available value.
    
    # ALTERNATIVE:
    # # fill values with 0
    # # NOTE: Requires that missing values are managed also in training data so that model understands that missing values are 0.
    #         This might might not work well for all models.
    #         A KNN-based model might work better with NaN values, as it can interpolate missing values based on the nearest neighbors.

    # Create a complete date range from date_begin to date_end
    all_dates = pd.date_range(start=date_begin, end=date_end)

    # Filter the DataFrame for the specified location
    location_df = df[df['location'] == location].copy()

    # add missing dates
    # TODO: might not handle all cases (e.g., first value is missing)
    missing_dates = all_dates.difference(location_df['date'].to_list())
    missing_df = pd.DataFrame({
        "date": missing_dates,
        "location": [location] * len(missing_dates),
        "level__m": [np.nan] * len(missing_dates)  # fill with NaN for now
    })
    # Exclude empty frames before concat to avoid pandas FutureWarning about
    # all-NA entries changing dtype inference behaviour in a future version.
    frames = [f for f in [location_df, missing_df] if not f.empty]
    location_df = pd.concat(frames, ignore_index=True).sort_values(by=['location', 'date'])

    # fill values with the last available value
    # Call infer_objects to avoid FutureWarning about object-dtype downcasting
    # being deprecated on ffill/bfill.
    location_df = location_df.ffill(axis=0).infer_objects(copy=False)

    # fill remaining NaN values with backward fill
    # case first value(s) are NaN
    location_df = location_df.bfill(axis=0).infer_objects(copy=False)

    # Guard: if level__m is still all-NaN after both fills, the entire location window
    # was empty — raise a clear error rather than letting pandera emit a cryptic SchemaError.
    if location_df['level__m'].isna().any():
        raise ValueError(
            f"No river level data found for location '{location}' between {date_begin} and {date_end}; "
            "it contains only null values and cannot be gap-filled. "
            "Ensure the database has at least one valid reading for this period."
        )

    return location_df


@pa.check_types
def load_river_level(
    config: Config, locations: Iterable[str], date_begin: date, date_end: date, fill_missing_dates: bool = False
) -> pat.DataFrame[StationDataFrameSchema]:
    """
    Load river level data
    Dataframe columns:
        - location: str
        - date: datetime
        - level__m: float
    
    If fill_missing_dates is True, the function will ensure that the returned DataFrame contains entries for all dates
    within the specified range for each location, filling in any missing dates with the last available value.
    This is EXPERIMENTAL and might not work well for all models.
    """

    df = __load(__RIVER_LEVEL_LOAD_FNS, config, locations, date_begin, date_end)

    # HOTFIX: make resilient to NaN values in DB
    df = df.dropna()

    if not fill_missing_dates:
        return df
    
    # Ensure that we have data for all dates in the range for each location
    stations_date_range = pd.date_range(start=date_begin, end=date_end).date
    _filled_dfs = []
    for station in locations:
        location = station
        _expected_len = len(stations_date_range)
        _actual_df = df[df['location'] == location]

        if len(_actual_df) == _expected_len:
            _filled_dfs.append(_actual_df)
        else:
            logger.warning(
                f"WARNING: Missing river level data for location {location}. Expected {len(stations_date_range)} entries, got {len(_actual_df)}. Filling missing dates.")
            _filled_dfs.append(__river_level_df_without_missing_dates(df, location, date_begin, date_end))

    return pd.concat(_filled_dfs, ignore_index=True).sort_values(by=['location', 'date'])  # type: ignore (ensured by pandera)


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


def __weather_df_without_missing_dates(df: pd.DataFrame, location: str, date_begin: date, date_end: date):
    """
    Processes a DataFrame containing WeatherDataFrameSchema data to ensure that
    it includes entries for all dates within a specified range for the specified location.
    The input DataFrame is expected to have the following columns:
        - location: str
        - date: datetime
        - precipitation_sum: float
        - precipitation_hours: float
    It can contain multiple locations and may have missing dates for the specified location.
    This function will return a DataFrame that includes all dates from date_begin to date_end
    for the specified location ONLY, filling in any missing dates with 0.0 values.

    :param df: Input DataFrame with weather data.
    :param location: The location to filter and ensure complete date coverage.
    :param date_begin: The start date of the range (inclusive).
    :param date_end: The end date of the range (inclusive).
    :return: A DataFrame with complete date coverage for the specified location.
    """
    # Create a complete date range from date_begin to date_end
    all_dates = pd.date_range(start=date_begin, end=date_end)

    # Filter the DataFrame for the specified location
    location_df = df[df['location'] == location].copy()

    # add missing dates
    missing_dates = all_dates.difference(location_df['date'].to_list())
    location_df = pd.concat([
        location_df,
        pd.DataFrame({
            "date": missing_dates,
            "location": [location] * len(missing_dates),
            "precipitation_sum": [np.nan] * len(missing_dates),
            "precipitation_hours": [np.nan] * len(missing_dates)
        })
    ], ignore_index=True).sort_values(by=['location', 'date'])

    # fill values with the last available value
    location_df = location_df.ffill(axis=0)

    # fill remaining NaN values with 0.0
    # case first value(s) are NaN
    location_df = location_df.fillna({
        "precipitation_sum": 0.0,
        "precipitation_hours": 0.0
    })

    return location_df


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
    df = None
    # load historical weather data for the last max(WEATHER_LAG) days if necessary
    if min_date < today:
        logger.debug("Loading inference data (history) from", min_date, "to", history_max_date)
        history_df = load_history_weather(config, locations, min_date, history_max_date)
        if locations is not None:
            acc.append(history_df[history_df["location"].isin(locations)])
        if max_date < today:
            # only historical data is needed
            df = history_df

    # load forecast weather data for the next min(WEATHER_LAG) days (forecast are negative lag) if necessary
    if max_date >= today:
        logger.debug("Loading inference data (forecast) from", date, "to", max_date)
        forecast_df = load_forecast_weather(config, locations, date, max_date)

        # filter locations
        if locations is not None:
            acc.append(forecast_df[forecast_df["location"].isin(locations)])

        df = pd.concat(acc, axis=0, ignore_index=True)
    
    # remove PyLance warning about df possibly being None
    if df is None:
        raise ValueError("No weather data, this should never happen")
    
    # Fill missing dates for each location
    _filled_dfs = []
    for location in locations:
        _expected_len = (max_date - min_date).days + 1
        _actual_df = df[df['location'] == location]

        if len(_actual_df) == _expected_len:
            _filled_dfs.append(_actual_df)
        else:
            logger.warning(
                f"WARNING: Missing weather data for location {location}. Expected {_expected_len} entries, got {len(_actual_df)}. Filling missing dates.")
            _filled_dfs.append(__weather_df_without_missing_dates(df, location, min_date, max_date))

    df = pd.concat(_filled_dfs, ignore_index=True).sort_values(by=['location', 'date'])

    return df  # type: ignore (ensured by pandera)


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
    df = load_river_level(
        config, locations, min_date, max_date,
        fill_missing_dates=True  # EXPERIMENTAL: fill missing dates with last available value (might not work well for all models)
    )

    # for each location, append row with empty values and index = date
    # this row is to ensure that the last day is included (corresponding to the date of the inference)
    df = pd.concat(
        [df, pd.DataFrame([{"location": location, "date": date, "level__m": 0.0} for location in locations])],
        ignore_index=True
    )

    return df  # type: ignore (ensured by pandera)


@pa.check_types
def load_inference_sensor_rainfall(
    config: Config, locations: Iterable[str], date=datetime.now()
) -> pat.DataFrame[SensorRainfallDataFrameSchema]:
    """
    Load sensor rainfall data for inference from public.sensor_readings.

    Mirrors load_inference_weather() in date-window logic: uses the same weather_lag_days
    from config to build the historical window. Sensor data is real-time only (no forecast arm).

    Dataframe columns:
        - location: str   (mapped from sensor station_id via haversine)
        - date: datetime
        - precipitation_sum: float  (daily rainfall total in mm)
        - precipitation_hours: int  (number of valid hourly readings that day)
    """
    date = date.date()

    model_config = config.load_model_config()
    weather_lag_days = json.loads(model_config["weather_lag_days"])

    min_date = date - timedelta(days=max(weather_lag_days))
    # Sensor data is historical only — cap at yesterday
    max_date = min(date - timedelta(days=min(weather_lag_days)), datetime.now().date() - timedelta(days=1))

    logger.info(f"Loading sensor rainfall inference data from {min_date} to {max_date}")
    df = load_sensor_rainfall_db(config, locations, min_date, max_date)

    if df.empty:
        return df  # type: ignore

    # Gap-fill each location using the same helper as load_inference_weather
    _filled_dfs = []
    for location in locations:
        _expected_len = (max_date - min_date).days + 1
        _actual_df = df[df["location"] == location]
        if len(_actual_df) == _expected_len:
            _filled_dfs.append(_actual_df)
        else:
            logger.warning(
                f"Missing sensor rainfall data for location {location}. "
                f"Expected {_expected_len} entries, got {len(_actual_df)}. Filling missing dates."
            )
            _filled_dfs.append(__weather_df_without_missing_dates(df, location, min_date, max_date))

    return pd.concat(_filled_dfs, ignore_index=True).sort_values(by=["location", "date"])  # type: ignore
