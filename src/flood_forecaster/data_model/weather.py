from dataclasses import dataclass

from sqlalchemy import Column, Float, String, DateTime, Integer

from . import Base, mapper_registry


@mapper_registry.mapped
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


@mapper_registry.mapped
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
