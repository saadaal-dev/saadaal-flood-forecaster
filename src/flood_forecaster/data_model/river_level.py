from dataclasses import dataclass
import enum
from sqlalchemy import Column, Enum, Integer, String, DateTime
from . import Base

# from sqlalchemy.orm import declarative_base

# Base = declarative_base()

class AlertType(enum.Enum):
    normal = "normal"
    moderate = "moderate"
    high = "high"
    full = "full"

class HistoricalRiverLevel(Base):
    __tablename__ = 'historical_river_level'
    __table_args__ = {"schema": "flood_forecaster"}  # Specify the schema

    id = Column(Integer, primary_key=True)
    location_name = Column(String(100))
    date = Column(DateTime)
    level_m = Column(Integer)
    station_number = Column(String(50))


@dataclass
class PredictedRiverLevel(Base):
    __tablename__ = 'predicted_river_level'

    id = Column(Integer, primary_key=True)
    station_number = Column(String(50))
    location_name = Column(String(100))
    date = Column(DateTime)
    forecasted_date = Column(DateTime)
    level_m = Column(Integer)
    ml_model_name = Column(String(100))
    alert_type = Column(Enum(AlertType))

# TODO: add orm getters and setters
