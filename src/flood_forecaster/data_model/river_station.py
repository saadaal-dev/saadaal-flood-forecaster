from sqlalchemy import Column, Integer, String, DateTime
from sqlalchemy.orm import declarative_base

Base = declarative_base()

class HistoricalRiverLevel(Base):
    __tablename__ = 'historical_river_level'

    id = Column(Integer, primary_key=True)
    location_name = Column(String(100))
    date = Column(DateTime)
    level_m = Column(Integer)
    station_number = Column(String(50))



class PredictedRiverStation(Base):
    __tablename__ = 'predicted_river_level'

    id = Column(Integer, primary_key=True)
    location_name = Column(String(100))
    date = Column(DateTime)
    level_m = Column(Integer)
    station_number = Column(String(50))

# TODO: add orm getters and setters