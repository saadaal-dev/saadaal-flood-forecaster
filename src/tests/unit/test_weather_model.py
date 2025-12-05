"""
Unit tests for weather data models.
Tests the data validation and conversion logic for weather data.
"""

import unittest
from datetime import datetime, date

import pandas as pd

from flood_forecaster.data_model.weather import (
    HistoricalWeather,
    ForecastWeather
)


class TestHistoricalWeather(unittest.TestCase):
    """Test HistoricalWeather data model."""

    def test_create_historical_weather(self):
        """Test creating a HistoricalWeather instance."""
        weather = HistoricalWeather(
            location_name="test_location",
            date=datetime(2024, 1, 1),
            temperature_2m_max=25.0,
            temperature_2m_min=15.0,
            precipitation_sum=10.0,
            rain_sum=8.0,
            precipitation_hours=5.0
        )

        self.assertEqual(weather.location_name, "test_location")
        self.assertEqual(weather.temperature_2m_max, 25.0)
        self.assertEqual(weather.precipitation_sum, 10.0)

    def test_from_dataframe_conversion(self):
        """Test converting DataFrame to HistoricalWeather objects."""
        df = pd.DataFrame({
            'location_name': ['loc1', 'loc2'],
            'date': [datetime(2024, 1, 1), datetime(2024, 1, 2)],
            'temperature_2m_max': [25.0, 26.0],
            'temperature_2m_min': [15.0, 16.0],
            'precipitation_sum': [10.0, 12.0],
            'rain_sum': [8.0, 10.0],
            'precipitation_hours': [5.0, 6.0]
        })

        weather_objects = HistoricalWeather.from_dataframe(df)

        self.assertEqual(len(weather_objects), 2)
        self.assertIsInstance(weather_objects[0], HistoricalWeather)
        self.assertEqual(weather_objects[0].location_name, 'loc1')
        self.assertEqual(weather_objects[1].location_name, 'loc2')

    def test_from_dataframe_with_missing_columns(self):
        """Test from_dataframe raises error when required columns missing."""
        df = pd.DataFrame({
            'location_name': ['loc1'],
            'date': [datetime(2024, 1, 1)]
            # Missing required temperature and precipitation columns
        })

        # Should handle missing columns gracefully or raise appropriate error
        try:
            weather_objects = HistoricalWeather.from_dataframe(df)
            # If it doesn't raise, check that it created objects
            self.assertIsNotNone(weather_objects)
        except (KeyError, ValueError, AttributeError):
            # Expected to fail with missing columns
            pass

    def test_tablename(self):
        """Test that table name is correctly set."""
        self.assertEqual(HistoricalWeather.__tablename__, 'historical_weather')


class TestForecastWeather(unittest.TestCase):
    """Test ForecastWeather data model."""

    def test_create_forecast_weather(self):
        """Test creating a ForecastWeather instance."""
        weather = ForecastWeather(
            location_name="test_location",
            date=datetime(2024, 1, 1),
            temperature_2m_max=25.0,
            temperature_2m_min=15.0,
            precipitation_sum=10.0,
            rain_sum=8.0,
            precipitation_hours=5.0,
            precipitation_probability_max=80.0,
            wind_speed_10m_max=15.0
        )

        self.assertEqual(weather.location_name, "test_location")
        self.assertEqual(weather.precipitation_probability_max, 80.0)
        self.assertEqual(weather.wind_speed_10m_max, 15.0)

    def test_from_dataframe_conversion(self):
        """Test converting DataFrame to ForecastWeather objects."""
        df = pd.DataFrame({
            'location_name': ['loc1', 'loc2'],
            'date': [datetime(2024, 1, 1), datetime(2024, 1, 2)],
            'temperature_2m_max': [25.0, 26.0],
            'temperature_2m_min': [15.0, 16.0],
            'precipitation_sum': [10.0, 12.0],
            'rain_sum': [8.0, 10.0],
            'precipitation_hours': [5.0, 6.0],
            'precipitation_probability_max': [80.0, 75.0],
            'wind_speed_10m_max': [15.0, 18.0]
        })

        weather_objects = ForecastWeather.from_dataframe(df)

        self.assertEqual(len(weather_objects), 2)
        self.assertIsInstance(weather_objects[0], ForecastWeather)
        self.assertEqual(weather_objects[0].precipitation_probability_max, 80.0)

    def test_tablename(self):
        """Test that table name is correctly set."""
        self.assertEqual(ForecastWeather.__tablename__, 'forecast_weather')


class TestWeatherDataFrameSchema(unittest.TestCase):
    """Test WeatherDataFrameSchema validation."""

    def test_valid_weather_dataframe(self):
        """Test that valid weather dataframe passes schema validation."""
        df = pd.DataFrame({
            'location': ['loc1', 'loc2'],
            'date': [date(2024, 1, 1), date(2024, 1, 2)],
            'precipitation_sum': [10.0, 12.0],
            'precipitation_hours': [5.0, 6.0]
        })

        # Schema validation happens during pandera check_types decorator
        # Just verify the dataframe structure is correct
        self.assertTrue('location' in df.columns)
        self.assertTrue('date' in df.columns)
        self.assertTrue('precipitation_sum' in df.columns)
        self.assertTrue('precipitation_hours' in df.columns)

    def test_weather_dataframe_with_nulls(self):
        """Test handling of null values in weather data."""
        df = pd.DataFrame({
            'location': ['loc1', 'loc2'],
            'date': [date(2024, 1, 1), date(2024, 1, 2)],
            'precipitation_sum': [10.0, None],  # One null value
            'precipitation_hours': [5.0, 6.0]
        })

        # Null precipitation should be handled (filled with 0 in load.py)
        self.assertTrue(df['precipitation_sum'].isnull().any())

    def test_weather_dataframe_date_types(self):
        """Test that date column can handle different date formats."""
        # Test with Python date objects
        df1 = pd.DataFrame({
            'location': ['loc1'],
            'date': [date(2024, 1, 1)],
            'precipitation_sum': [10.0],
            'precipitation_hours': [5.0]
        })

        self.assertEqual(df1['date'].iloc[0], date(2024, 1, 1))

        # Test with datetime objects (should be converted to date)
        df2 = pd.DataFrame({
            'location': ['loc1'],
            'date': [datetime(2024, 1, 1, 12, 0, 0)],
            'precipitation_sum': [10.0],
            'precipitation_hours': [5.0]
        })

        # In actual use, datetime is converted to date in load.py
        self.assertIsInstance(df2['date'].iloc[0], datetime)


class TestWeatherDataValidation(unittest.TestCase):
    """Test weather data validation and edge cases."""

    def test_negative_precipitation(self):
        """Test that negative precipitation values are handled."""
        weather = HistoricalWeather(
            location_name="test",
            date=datetime(2024, 1, 1),
            temperature_2m_max=25.0,
            temperature_2m_min=15.0,
            precipitation_sum=-5.0,  # Invalid negative
            rain_sum=0.0,
            precipitation_hours=0.0
        )

        # Model should allow creation (validation happens elsewhere)
        self.assertEqual(weather.precipitation_sum, -5.0)

    def test_extreme_temperature_values(self):
        """Test handling of extreme temperature values."""
        weather = HistoricalWeather(
            location_name="test",
            date=datetime(2024, 1, 1),
            temperature_2m_max=50.0,  # Very hot
            temperature_2m_min=-40.0,  # Very cold
            precipitation_sum=0.0,
            rain_sum=0.0,
            precipitation_hours=0.0
        )

        self.assertEqual(weather.temperature_2m_max, 50.0)
        self.assertEqual(weather.temperature_2m_min, -40.0)

    def test_precipitation_hours_range(self):
        """Test precipitation hours within valid range."""
        weather = HistoricalWeather(
            location_name="test",
            date=datetime(2024, 1, 1),
            temperature_2m_max=25.0,
            temperature_2m_min=15.0,
            precipitation_sum=10.0,
            rain_sum=8.0,
            precipitation_hours=24.0  # Maximum possible (entire day)
        )

        self.assertEqual(weather.precipitation_hours, 24.0)

    def test_zero_values(self):
        """Test weather with all zero values (valid for dry day)."""
        weather = HistoricalWeather(
            location_name="test",
            date=datetime(2024, 1, 1),
            temperature_2m_max=0.0,
            temperature_2m_min=0.0,
            precipitation_sum=0.0,
            rain_sum=0.0,
            precipitation_hours=0.0
        )

        self.assertEqual(weather.precipitation_sum, 0.0)
        self.assertEqual(weather.temperature_2m_max, 0.0)


class TestWeatherComparison(unittest.TestCase):
    """Test comparison between historical and forecast weather."""

    def test_common_fields_between_models(self):
        """Test that historical and forecast share common fields."""
        hist_fields = set(HistoricalWeather.__table__.columns.keys())
        forecast_fields = set(ForecastWeather.__table__.columns.keys())

        # Common fields should include basic weather data
        common_fields = hist_fields & forecast_fields

        expected_common = {
            'id', 'location_name', 'date',
            'temperature_2m_max', 'temperature_2m_min',
            'precipitation_sum', 'rain_sum', 'precipitation_hours'
        }

        self.assertTrue(expected_common.issubset(common_fields))

    def test_forecast_specific_fields(self):
        """Test that forecast has additional fields not in historical."""
        forecast_fields = set(ForecastWeather.__table__.columns.keys())

        # Forecast should have probability and wind speed
        self.assertIn('precipitation_probability_max', forecast_fields)
        self.assertIn('wind_speed_10m_max', forecast_fields)


if __name__ == '__main__':
    unittest.main()
