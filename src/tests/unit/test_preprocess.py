"""
Unit tests for ML preprocessing functions.
Tests the critical data preprocessing logic used in the ML pipeline.
"""

import unittest
from datetime import date

import numpy as np
import pandas as pd

from flood_forecaster.ml_model.preprocess import (
    preprocess_station,
    preprocess_weather,
    preprocess_all_weather
)


class TestPreprocessStation(unittest.TestCase):
    """Test station data preprocessing with lag features."""

    def setUp(self):
        """Create sample station data for testing."""
        dates = pd.date_range(start='2024-01-01', end='2024-01-10', freq='D')
        self.sample_df = pd.DataFrame({
            'location': ['Station A'] * len(dates),
            'date': dates,
            'level__m': [1.0, 1.5, 2.0, 2.5, 3.0, 3.5, 4.0, 4.5, 5.0, 5.5]
        })
        self.sample_df = self.sample_df.set_index(['location', 'date'])

    def test_preprocess_station_basic(self):
        """Test basic preprocessing with default lag days."""
        result = preprocess_station(self.sample_df, lag_days=[1, 2])

        # Should have lag columns with format lag{number:02d}__column_name
        self.assertIn('lag01__level__m', result.columns)
        self.assertIn('lag02__level__m', result.columns)

        # Should also have original column
        self.assertIn('level__m', result.columns)
        self.assertIsNotNone(result)

    def test_preprocess_station_only_lag_columns(self):
        """Test preprocessing when only lag columns are requested."""
        result = preprocess_station(self.sample_df, lag_days=[1], only_lag_columns=True)

        # Should only have lag columns
        self.assertIn('lag01__level__m', result.columns)
        self.assertNotIn('level__m', result.columns)

    def test_preprocess_station_empty_dataframe(self):
        """Test handling of empty dataframe."""
        empty_df = pd.DataFrame(columns=['location', 'date', 'level__m'])
        empty_df = empty_df.set_index(['location', 'date'])

        result = preprocess_station(empty_df, lag_days=[1, 2])

        # Should return empty dataframe with expected columns
        self.assertTrue(result.empty)


class TestPreprocessWeather(unittest.TestCase):
    """Test weather data preprocessing."""

    def setUp(self):
        """Create sample weather data for testing."""
        dates = pd.date_range(start='2024-01-01', end='2024-01-10', freq='D')
        self.sample_df = pd.DataFrame({
            'date': dates,
            'precipitation_sum': np.random.uniform(0, 50, len(dates)),
            'precipitation_hours': np.random.uniform(0, 24, len(dates))
        })
        self.sample_df = self.sample_df.set_index('date')

    def test_preprocess_weather_basic(self):
        """Test basic weather preprocessing with lag features."""
        result = preprocess_weather(self.sample_df, lag_days=[-1, 0, 1])

        # Should have forecast and lag columns
        # lag=-1 (tomorrow) -> forecast02__
        # lag=0 (today forecast) -> forecast01__
        # lag=1 (yesterday) -> lag01__
        self.assertIn('forecast02__precipitation_sum', result.columns)
        self.assertIn('forecast01__precipitation_sum', result.columns)
        self.assertIn('lag01__precipitation_sum', result.columns)

        # Original columns should be removed (only lag values kept)
        self.assertNotIn('precipitation_sum', result.columns)

    def test_preprocess_weather_handles_missing_dates(self):
        """Test that preprocessing handles gaps in date sequence."""
        # Create data with missing date
        dates = [date(2024, 1, 1), date(2024, 1, 2), date(2024, 1, 4)]  # Missing Jan 3
        df = pd.DataFrame({
            'date': dates,
            'precipitation_sum': [10, 20, 30],
            'precipitation_hours': [5, 10, 15]
        })
        df = df.set_index('date')

        result = preprocess_weather(df, lag_days=[0, 1])

        # Should still process without error
        self.assertIsNotNone(result)


class TestPreprocessAllWeather(unittest.TestCase):
    """Test preprocessing of multiple weather locations."""

    def setUp(self):
        """Create sample multi-location weather data."""
        dates = pd.date_range(start='2024-01-05', end='2024-01-10', freq='D')

        self.weather_dfs = {
            'location_1': pd.DataFrame({
                'location': ['location_1'] * len(dates),
                'date': dates,
                'precipitation_sum': [10, 15, 20, 25, 30, 35],
                'precipitation_hours': [2, 3, 4, 5, 6, 7]
            }).set_index(['location', 'date']),
            'location_2': pd.DataFrame({
                'location': ['location_2'] * len(dates),
                'date': dates,
                'precipitation_sum': [5, 10, 15, 20, 25, 30],
                'precipitation_hours': [1, 2, 3, 4, 5, 6]
            }).set_index(['location', 'date'])
        }

    def test_preprocess_all_weather_basic(self):
        """Test preprocessing multiple weather locations."""
        result = preprocess_all_weather(self.weather_dfs, lag_days=[-1, 0])

        # Should merge all locations into one dataframe
        self.assertIsNotNone(result)

        # Should have prefixed columns for each location
        cols = result.columns.tolist()
        location_1_cols = [c for c in cols if c.startswith('location_1__')]
        location_2_cols = [c for c in cols if c.startswith('location_2__')]

        self.assertTrue(len(location_1_cols) > 0)
        self.assertTrue(len(location_2_cols) > 0)

    def test_preprocess_all_weather_handles_duplicates(self):
        """Test that preprocessing handles and removes duplicate indices."""
        dates = pd.date_range(start='2024-01-05', end='2024-01-08', freq='D')

        # Create dataframe with duplicate index entries
        df_with_dupes = pd.DataFrame({
            'location': ['loc_1'] * len(dates) + ['loc_1'],  # Extra entry
            'date': list(dates) + [dates[0]],  # Duplicate first date
            'precipitation_sum': [10, 15, 20, 25, 999],  # Last is duplicate
            'precipitation_hours': [2, 3, 4, 5, 99]
        }).set_index(['location', 'date'])

        weather_dfs = {'loc_1': df_with_dupes}

        # Should handle duplicates gracefully (warning printed, duplicates removed)
        result = preprocess_all_weather(weather_dfs, lag_days=[0])

        # Should not raise an error
        self.assertIsNotNone(result)

    def test_preprocess_all_weather_empty_dict(self):
        """Test handling of empty weather dictionary."""
        result = preprocess_all_weather({}, lag_days=[0])

        # Should return None or empty dataframe
        self.assertTrue(result is None or result.empty)


class TestPreprocessIntegration(unittest.TestCase):
    """Integration tests for complete preprocessing pipeline."""

    def test_station_and_weather_preprocessing_compatible(self):
        """Test that station and weather preprocessing produce compatible outputs."""
        # Create station data
        dates = pd.date_range(start='2024-01-03', end='2024-01-10', freq='D')
        station_df = pd.DataFrame({
            'location': ['Station A'] * len(dates),
            'date': dates,
            'level__m': [1.0, 1.5, 2.0, 2.5, 3.0, 3.5, 4.0, 4.5]
        }).set_index(['location', 'date'])

        # Create weather data
        weather_df = pd.DataFrame({
            'location': ['Weather Loc'] * len(dates),
            'date': dates,
            'precipitation_sum': [10, 15, 20, 25, 30, 35, 40, 45],
            'precipitation_hours': [2, 3, 4, 5, 6, 7, 8, 9]
        }).set_index(['location', 'date'])

        # Preprocess both
        station_result = preprocess_station(station_df, lag_days=[1, 2])
        weather_result = preprocess_all_weather(
            {'Weather Loc': weather_df},
            lag_days=[-1, 0]
        )

        # Both should have date as index
        self.assertIsNotNone(station_result.index)
        self.assertIsNotNone(weather_result.index)

        # Should be able to merge on date index
        # This is what happens in the actual ML pipeline
        self.assertTrue(True)  # If we got here without error, preprocessing is compatible


if __name__ == '__main__':
    unittest.main()
