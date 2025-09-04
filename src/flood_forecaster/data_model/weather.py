from dataclasses import dataclass
from typing import List

import pandas as pd
import pandera.pandas as pa
from pandera.typing import Series
from sqlalchemy import Column, Float, String, DateTime, Integer

from . import Base


@dataclass
class HistoricalWeather(Base):
    __tablename__ = 'historical_weather'
    __table_args__ = {"schema": "flood_forecaster"}  # Specify the schema

    id = Column(Integer, primary_key=True)
    location_name = Column(String(100))
    date = Column(DateTime)
    temperature_2m_max = Column(Float)
    temperature_2m_min = Column(Float)
    precipitation_sum = Column(Float)
    rain_sum = Column(Float)
    precipitation_hours = Column(Float)

    @classmethod
    def from_dataframe(cls, df):
        """
        Convert a pandas DataFrame to a list of HistoricalWeather objects.
        """
        records = df.to_dict(orient="records")
        return [cls(**record) for record in records]

@dataclass
class ForecastWeather(Base):
    __tablename__ = 'forecast_weather'
    __table_args__ = {"schema": "flood_forecaster"}  # Specify the schema

    id = Column(Integer, primary_key=True)
    location_name = Column(String(100))
    date = Column(DateTime)
    temperature_2m_max = Column(Float)
    temperature_2m_min = Column(Float)
    precipitation_sum = Column(Float)
    rain_sum = Column(Float)
    precipitation_hours = Column(Float)
    precipitation_probability_max = Column(Float)
    wind_speed_10m_max = Column(Float)

    @classmethod
    def from_dataframe(cls, df):
        """
        Convert a pandas DataFrame to a list of ForecastWeather objects.
        """
        records = df.to_dict(orient="records")
        return [cls(**record) for record in records]


class HistoricalWeatherDataFrameSchema(pa.DataFrameModel):
    """
    Schema for historical weather data in ETL.
    Equivalent to the HistoricalWeather SQLAlchemy model.
    """
    location_name: Series[str]
    date: Series[pd.Timestamp]
    temperature_2m_max: Series[float]
    temperature_2m_min: Series[float]
    precipitation_sum: Series[float]
    rain_sum: Series[float]
    precipitation_hours: Series[float]

    class Config:
        strict = True
        coerce = True


class ForecastWeatherDataFrameSchema(pa.DataFrameModel):
    """
    Schema for forecast weather data in ETL.
    Equivalent to the ForecastWeather SQLAlchemy model.
    """
    location_name: Series[str]
    date: Series[pd.Timestamp]
    temperature_2m_max: Series[float]
    temperature_2m_min: Series[float]
    precipitation_sum: Series[float]
    rain_sum: Series[float]
    precipitation_hours: Series[float]
    precipitation_probability_max: Series[float]
    wind_speed_10m_max: Series[float]

    class Config:
        strict = True
        coerce = True


class WeatherDataFrameSchema(pa.DataFrameModel):
    """
    Schema for weather data in ETL.
    """
    location: Series[str]
    date: Series[pd.Timestamp]
    precipitation_sum: Series[float]
    precipitation_hours: Series[int]

    class Config:
        strict = True
        coerce = True


@dataclass
class StationMapping:
    """
    A data class to store metadata for a weather station.

    Attributes:
        location (str): The location of the weather station.
        river (str): The river associated with the weather station.
        upstream_stations (List[str]): A list of upstream stations related to the weather station.
        weather_locations (List[str]): A list of weather conditions relevant to the weather station.
    """
    location: str
    river: str
    upstream_stations: List[str]
    weather_locations: List[str]


@dataclass
class WeatherLocation:
    def __init__(self, label: str, region: str, district: str, latitude: float, longitude: float, remarks: str):
        self.label = label
        self.region = region
        self.district = district
        self.latitude = latitude
        self.longitude = longitude
        self.remarks = remarks
