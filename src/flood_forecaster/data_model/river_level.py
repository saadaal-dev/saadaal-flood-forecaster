from sqlalchemy import Column, Integer, String, DateTime
from . import Base

# from sqlalchemy.orm import declarative_base

# Base = declarative_base()


class HistoricalRiverLevel(Base):
    __tablename__ = 'historical_river_level'
    __table_args__ = {"schema": "flood_forecaster"}  # Specify the schema

    id = Column(Integer, primary_key=True)
    location_name = Column(String(100))
    date = Column(DateTime)
    level_m = Column(Integer)
    station_number = Column(String(50))


class PredictedRiverLevel(Base):
    __tablename__ = 'predicted_river_level'

    id = Column(Integer, primary_key=True)
    location_name = Column(String(100))
    date = Column(DateTime)
    level_m = Column(Integer)
    station_number = Column(String(50))
    ml_model_name = Column(String(100))
    forecast_days = Column(Integer, comment="Number of days into the future the forecast is for")

# TODO: add orm getters and setters
