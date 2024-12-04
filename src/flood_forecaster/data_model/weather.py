from sqlalchemy import Column, Float, String, DateTime, Integer
from sqlalchemy.orm import declarative_base


Base = declarative_base()


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