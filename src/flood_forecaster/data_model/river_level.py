from dataclasses import dataclass

import pandas as pd
import pandera.pandas as pa
from pandera.typing import Series
from sqlalchemy import Column, Integer, String, DateTime, Float, Date, Numeric
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


@dataclass
class RiverStationMetadata(Base):
    __tablename__ = 'river_station_metadata'
    __table_args__ = {"schema": "flood_forecaster"}  # Specify the schema

    station_number = Column(String(50))
    # DB table defines a UNIQUE constraint on station_name; use it as ORM primary key.
    station_name = Column(String(100), primary_key=True)
    river_name = Column(String(100))
    region = Column(String(100))
    status = Column(String(50))
    first_date = Column(Date)
    latitude = Column(Float)
    longitude = Column(Float)
    moderate_flood_risk_m = Column(Float, comment="River level in meters that indicates moderate flood risk")
    high_flood_risk_m = Column(Float, comment="River level in meters that indicates high flood risk")
    bankfull_m = Column(Float, comment="River level in meters that indicates bankfull conditions")
    maximum_depth_m = Column(Float, comment="Maximum recorded river depth in meters at this station")
    maximum_width_m = Column(Float, comment="Maximum recorded river width in meters at this station")
    maximum_flow_m = Column(Float, comment="Maximum recorded river flow in cubic meters per second at this station")
    elevation = Column(Float, comment="Elevation of the station in meters above sea level")
    swalim_internal_id = Column(Integer, comment="Internal ID used by SWALIM for this station")
    

@dataclass
class StationRiverData(Base):
    """Model for public schema station_river_data."""
    __tablename__ = 'station_river_data'
    __table_args__ = {"schema": "public"}  # Specify the schema

    id = Column(Integer, primary_key=True)
    station_id = Column(Integer)
    # Numeric supports decimal values; nullable allows missing readings from DB.
    reading = Column(Numeric, nullable=True)
    reading_date = Column(Date)
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
