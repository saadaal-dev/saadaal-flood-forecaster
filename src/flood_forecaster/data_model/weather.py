from dataclasses import dataclass

from sqlalchemy import Column, Float, String, DateTime, Integer
import pandas as pd
import pandera.pandas as pa
from pandera.typing import Series

from . import Base

@dataclass
class HistoricalWeather(Base):
    __tablename__ = 'historical_weather'

    id = Column(Integer, primary_key=True)
    location_name = Column(String(100))
    date = Column(DateTime)
    temperature_2m_max = Column(Float)
    temperature_2m_min = Column(Float)
    precipitation_sum = Column(Float)
    rain_sum = Column(Float)
    precipitation_hours = Column(Float)


@dataclass
class ForecastWeather(Base):
    __tablename__ = 'forecast_weather'

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

# TODO: add orm getters and setters


class WeatherDataFrameSchema(pa.DataFrameModel):
    """
    Schema for weather data in ETL.
    """
    location: Series[str]
    date: Series[pd.Timestamp]
    precipitation_sum: Series[float]
    precipitation_hours: Series[float]

    class Config:
        strict = True
        coerce = True
