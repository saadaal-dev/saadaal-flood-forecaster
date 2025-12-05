from dataclasses import dataclass

import pandas as pd
import pandera.pandas as pa
from pandera.typing import Series
from sqlalchemy import Column, Integer, String, DateTime, Float, Date
from sqlalchemy.sql import func

from . import Base


@dataclass
class HistoricalRiverLevel(Base):
    __tablename__ = 'historical_river_level'
    __table_args__ = {"schema": "flood_forecaster"}  # Specify the schema

    id = Column(Integer, primary_key=True)
    location_name = Column(String(100))
    date = Column(Date)
    level_m = Column(Float)
    # station_number = Column(String(50))  # HOTFIX: commented out as it is not used in the current implementation and adds useless complexity


@dataclass
class PredictedRiverLevel(Base):
    __tablename__ = 'predicted_river_level'
    __table_args__ = {"schema": "flood_forecaster"}  # Specify the schema

    id = Column(Integer, primary_key=True)
    location_name = Column(String(100))
    date = Column(Date)  # Changed from DateTime to Date to store only date, not time
    level_m = Column(Float)
    station_number = Column(String(50))
    ml_model_name = Column(String(100))
    forecast_days = Column(Integer, comment="Number of days into the future the forecast is for")
    risk_level = Column(String(50), comment="Risk level of the forecasted river level, e.g., 'Low', 'Medium', 'High'")
    created_at = Column(DateTime, server_default=func.now(), nullable=False)
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now(), nullable=False)


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
