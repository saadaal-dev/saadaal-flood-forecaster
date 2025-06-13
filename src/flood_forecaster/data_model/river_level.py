from dataclasses import dataclass

import pandas as pd
import pandera.pandas as pa
from pandera.typing import Series
from sqlalchemy import Column, Integer, String, DateTime, Float, Date

from . import Base


@dataclass
class HistoricalRiverLevel(Base):
    __tablename__ = 'historical_river_level'
    __table_args__ = {"schema": "flood_forecaster"}  # Specify the schema

    id = Column(Integer, primary_key=True)
    location_name = Column(String(100))
    date = Column(Date)
    level_m = Column(Float)


@dataclass
class PredictedRiverLevel(Base):
    __tablename__ = 'predicted_river_level'
    __table_args__ = {"schema": "flood_forecaster"}  # Specify the schema

    id = Column(Integer, primary_key=True)
    location_name = Column(String(100))
    date = Column(DateTime)
    level_m = Column(Integer)
    station_number = Column(String(50))
    ml_model_name = Column(String(100))
    forecast_days = Column(Integer, comment="Number of days into the future the forecast is for")
    risk_level = Column(String(50), comment="Risk level of the forecasted river level, e.g., 'Low', 'Medium', 'High'")

# TODO: add orm getters and setters


class StationDataFrameSchema(pa.DataFrameModel):
    """
    Schema for station data in ETL.
    """
    location: Series[str]
    date: Series[pd.Timestamp]
    level__m: Series[float]

    class Config:
        strict = True
        coerce = True
