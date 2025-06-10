from dataclasses import dataclass

from sqlalchemy import Column, Integer, String, DateTime, Float, Date

from . import Base, mapper_registry


@mapper_registry.mapped
@dataclass
class HistoricalRiverLevel(Base):
    __tablename__ = 'historical_river_level'
    __table_args__ = {"schema": "flood_forecaster"}  # Specify the schema

    id = Column(Integer, primary_key=True)
    location_name = Column(String(100))
    date = Column(Date)
    level_m = Column(Float)
    station_number = Column(String(50))


@mapper_registry.mapped
@dataclass
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
