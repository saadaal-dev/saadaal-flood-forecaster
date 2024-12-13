# Methods to load the data from the database
from datetime import datetime

import pandas as pd
from sqlalchemy import select

from src.flood_forecaster.data_model.river_level import HistoricalRiverLevel, PredictedRiverLevel
from src.flood_forecaster.data_model.weather import HistoricalWeather, ForecastWeather
from src.flood_forecaster.utils.configuration import Config
from src.flood_forecaster.utils.database_helper import DatabaseConnection


def load_history_weather_db(config: Config, location: str, date_begin: datetime, date_end: datetime):
    """
    Loads the history weather data from the database and returns it as a pandas dataframe
    :param config:
    :param location:
    :param date_begin:
    :param date_end:
    :return: pandas dataframe
    """
    stmt = (select(HistoricalWeather)
            .where(HistoricalWeather.location_name == location)
            .where(HistoricalWeather.date > date_begin)
            .where(HistoricalWeather.date < date_end))
    database = DatabaseConnection(config)
    return pd.read_sql(stmt, database.engine)


def load_forecast_weather_db(config: Config, location: str, date_begin: datetime, date_end: datetime):
    stmt = (select(ForecastWeather)
            .where(ForecastWeather.location_name == location)
            .where(ForecastWeather.date > date_begin)
            .where(ForecastWeather.date < date_end))
    database = DatabaseConnection(config)
    return pd.read_sql(stmt, database.engine)


def load_river_level_db(config: Config, location: str, date_begin: datetime, date_end: datetime):
    stmt = (select(HistoricalRiverLevel)
            .where(HistoricalRiverLevel.location_name == location)
            .where(HistoricalRiverLevel.date > date_begin)
            .where(HistoricalRiverLevel.date < date_end))
    database = DatabaseConnection(config)
    return pd.read_sql(stmt, database.engine)


def insert_predicted_river_level_db(config: Config, predicted_river_level: PredictedRiverLevel):
    # TODO: Implement this function and move
    pass

# TODO unify function already done that loads from csv (preprocess.py)
#  fn that returns a df from date_begin to date_end. priority to historical data,
#  filling with forecast data for the days that are not in the historical table (future days)
