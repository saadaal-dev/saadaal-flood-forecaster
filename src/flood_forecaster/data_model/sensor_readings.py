from dataclasses import dataclass

import pandas as pd
import pandera.pandas as pa
from pandera.typing import Series
from sqlalchemy import Column, Integer, String, DateTime

from . import Base


@dataclass
class SensorReading(Base):
    """
    ORM model for public.sensor_readings — IoT sensor telemetry ingested from field devices.
    Lives in the 'public' schema (shaqodoon application DB), not in 'flood_forecaster'.
    """
    __tablename__ = 'sensor_readings'
    __table_args__ = {"schema": "public"}

    id = Column(Integer, primary_key=True)
    station_id = Column(String(64))
    sensor_id = Column(String(32))
    sensor_meaning = Column(String(128))
    reading_ts = Column(DateTime)
    value = Column(String(64))          # raw VARCHAR — may contain "---", "-999.99", "NULL", ""
    original_date = Column(String(16))  # raw date string from device firmware
    original_time = Column(String(16))  # raw time string from device firmware
    firmware = Column(String(64))
    ingested_at = Column(DateTime)


class SensorReadingDataFrameSchema(pa.DataFrameModel):
    """
    Pandera schema for raw rows from public.sensor_readings.
    """
    station_id: Series[str]
    sensor_id: Series[str] = pa.Field(nullable=True)
    sensor_meaning: Series[str] = pa.Field(nullable=True)
    reading_ts: Series[pd.Timestamp]
    value: Series[str] = pa.Field(nullable=True)
    original_date: Series[str] = pa.Field(nullable=True)
    original_time: Series[str] = pa.Field(nullable=True)
    firmware: Series[str] = pa.Field(nullable=True)
    ingested_at: Series[pd.Timestamp] = pa.Field(nullable=True)

    class Config:
        strict = False   # allow extra columns (e.g. id)
        coerce = True


class SensorRainfallDataFrameSchema(pa.DataFrameModel):
    """
    Pandera schema for cleaned, daily-aggregated sensor rainfall data.
    Column-compatible with WeatherDataFrameSchema so it can be used as a drop-in
    replacement or coalesced with Open-Meteo precipitation data in the inference pipeline.

    Columns:
        location         -- pipeline location label (mapped from sensor station_id via haversine)
        date             -- calendar date (daily aggregate)
        precipitation_sum  -- daily total rainfall in mm (sum of valid sensor readings)
        precipitation_hours -- number of hours with a valid rainfall reading that day
    """
    location: Series[str]
    date: Series[pd.Timestamp]
    precipitation_sum: Series[float] = pa.Field(ge=0.0)
    precipitation_hours: Series[int] = pa.Field(ge=0)

    class Config:
        strict = True
        coerce = True
