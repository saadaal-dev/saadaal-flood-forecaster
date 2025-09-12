import unittest
from datetime import datetime, timedelta
from unittest.mock import patch, MagicMock

import pandas as pd

from flood_forecaster.data_ingestion.load import (
    load_inference_weather,
    load_inference_river_levels
)
from flood_forecaster.utils.configuration import Config, DataSourceType


class TestLoadFunctions(unittest.TestCase):

    @patch('flood_forecaster.data_ingestion.load.load_inference_weather')
    @patch('flood_forecaster.data_ingestion.load.load_forecast_weather')
    @patch('flood_forecaster.data_ingestion.load.load_history_weather')
    def test_load_inference_weather_today_past_only(self, mock_load_history_weather, mock_load_forecast_weather, mock_load_inference):
        mock_config = MagicMock(spec=Config)
        mock_config.load_model_config.return_value = {"weather_lag_days": "[1, 2, 3]"}
        mock_config.get_data_source_type.return_value = DataSourceType.CSV

        # NOTE: today is considered as a future day (forecast day)
        # so we set the current datetime to yesterday
        now = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0) - timedelta(days=1)
        
        # generate mock data for historical weather with 2 locations, 3 days each
        mock_history_df = pd.DataFrame({
            'location': ['loc1', 'loc1', 'loc1', 'loc2', 'loc2', 'loc2'],
            'date': [now - timedelta(days=3), now - timedelta(days=2), now - timedelta(days=1),
                     now - timedelta(days=3), now - timedelta(days=2), now - timedelta(days=1)],
            'precipitation_sum': [0.1, 0.2, 0.3, 1.4, 1.5, 1.6],
            'precipitation_hours': [1, 2, 3, 4, 5, 6]
        })
        mock_load_history_weather.return_value = mock_history_df

        # no forecast data - return empty DataFrame with correct columns
        mock_forecast_df = pd.DataFrame(columns=['location', 'date', 'precipitation_sum', 'precipitation_hours'])
        mock_load_forecast_weather.return_value = mock_forecast_df

        expected_df = mock_history_df.sort_values(by=['location', 'date']).reset_index(drop=True)
        mock_load_inference.return_value = expected_df
        
        result = mock_load_inference(mock_config, ['loc1', 'loc2'], now)
        
        self.assertIsInstance(result, pd.DataFrame)
        self.assertEqual(len(result), 6)  # 2 locations × 3 days
        self.assertListEqual(list(result.columns), ['location', 'date', 'precipitation_sum', 'precipitation_hours'])

    @patch('flood_forecaster.data_ingestion.load.load_inference_weather')
    def test_load_inference_weather_today_forecast_only(self, mock_load_inference):
        mock_config = MagicMock(spec=Config)
        mock_config.load_model_config.return_value = {"weather_lag_days": "[0, -1]"}
        mock_config.get_data_source_type.return_value = DataSourceType.CSV
        now = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        
        # generate mock data for forecast weather with 2 locations, 2 days each (today, tomorrow)
        expected_df = pd.DataFrame({
            'location': ['loc1', 'loc1', 'loc2', 'loc2'],
            'date': [now, now + timedelta(days=1),
                     now, now + timedelta(days=1)],
            'precipitation_sum': [0.3, 0.4, 1.0, 2.0],
            'precipitation_hours': [3, 4, 10, 20]
        }).sort_values(by=['location', 'date']).reset_index(drop=True)
        
        mock_load_inference.return_value = expected_df

        result = mock_load_inference(mock_config, ['loc1', 'loc2'], now)
        
        self.assertIsInstance(result, pd.DataFrame)
        self.assertEqual(len(result), 4)  # 2 locations × 2 days
        self.assertListEqual(list(result.columns), ['location', 'date', 'precipitation_sum', 'precipitation_hours'])

    @patch('flood_forecaster.data_ingestion.load.load_inference_weather')
    def test_load_inference_weather_today(self, mock_load_inference):
        mock_config = MagicMock(spec=Config)
        mock_config.load_model_config.return_value = {"weather_lag_days": "[1, 2, 3, 0, -1]"}
        mock_config.get_data_source_type.return_value = DataSourceType.CSV
        now = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        
        # Combined historical and forecast data
        expected_df = pd.DataFrame({
            'location': ['loc1', 'loc1', 'loc1', 'loc1', 'loc1', 'loc2', 'loc2', 'loc2', 'loc2', 'loc2'],
            'date': [now - timedelta(days=3), now - timedelta(days=2), now - timedelta(days=1), now, now + timedelta(days=1),
                     now - timedelta(days=3), now - timedelta(days=2), now - timedelta(days=1), now, now + timedelta(days=1)],
            'precipitation_sum': [0.1, 0.2, 0.3, 0.3, 0.4, 1.4, 1.5, 1.6, 1.0, 2.0],
            'precipitation_hours': [1, 2, 3, 3, 4, 4, 5, 6, 10, 20]
        }).sort_values(by=['location', 'date']).reset_index(drop=True)
        
        mock_load_inference.return_value = expected_df

        result = mock_load_inference(mock_config, ['loc1', 'loc2'], now)
        
        self.assertIsInstance(result, pd.DataFrame)
        self.assertEqual(len(result), 10)  # 2 locations × 5 days
        self.assertListEqual(list(result.columns), ['location', 'date', 'precipitation_sum', 'precipitation_hours'])

    @patch('flood_forecaster.data_ingestion.load.load_river_level')
    def test_load_inference_river_levels(self, mock_load_river_level):
        """
        Test the load_inference_river_levels function

        It should load river levels for inference, given a list of locations and a date
        based on the lag days provided in the input config.
        """

        # relevant parts of the config are:
        # "river_station_lag_days": "[1, 2, 3]"
        mock_config = MagicMock(spec=Config)
        mock_config.load_model_config.return_value = {"river_station_lag_days": "[1, 2, 3]"}
        mock_config.get_data_source_type.return_value = DataSourceType.CSV
        now = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        
        # generate mock data for river levels with 2 locations, 3 lag days each
        # 6 values in total
        mock_df = pd.DataFrame({
            'location': ['loc1', 'loc1', 'loc1', 'loc2', 'loc2', 'loc2'],
            'date': [now - timedelta(days=3), now - timedelta(days=2), now - timedelta(days=1),
                     now - timedelta(days=3), now - timedelta(days=2), now - timedelta(days=1)],
            'level__m': [11.0, 12.0, 13.0, 21.0, 22.0, 23.0]
        })

        # fill values for the current day with 0.0
        # (reference line for prediction)
        placeholder_df = pd.DataFrame({
            'location': ['loc1', 'loc2'],
            'date': [now, now],
            'level__m': [0.0, 0.0]
        })
        
        mock_load_river_level.return_value = mock_df

        result = load_inference_river_levels(mock_config, ['loc1', 'loc2'], now)
        expected_df = pd.concat([mock_df, placeholder_df], axis=0, ignore_index=True)

        # assert that the parameters sent to load_river_level are the expected ones
        mock_load_river_level.assert_called_with(
            mock_config,
            ['loc1', 'loc2'],
            now.date() - timedelta(days=3), 
            now.date() - timedelta(days=1),
            fill_missing_dates=True
        )

        pd.testing.assert_frame_equal(result, expected_df)


if __name__ == '__main__':
    unittest.main()