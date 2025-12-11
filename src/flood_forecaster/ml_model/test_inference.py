import unittest
from datetime import datetime, timedelta
from unittest.mock import MagicMock

import pandas as pd

from flood_forecaster.data_ingestion.load import StationDataFrameSchema, WeatherDataFrameSchema
from flood_forecaster.data_model.weather import StationMapping
from flood_forecaster.ml_model.inference import infer_from_raw_data


class TestInference(unittest.TestCase):
    def setUp(self):
        # Mock ModelManager so that .infer(df) returns the input dataframe with y=42.0 using a lambda function
        self.model_manager = MagicMock()
        self.model_manager.load.return_value = "mock_model"
        IGNORE_COLUMNS = ["month", "dayofyear", "month_sin", "month_cos", "dayofyear_sin", "dayofyear_cos"]
        self.model_manager.infer.side_effect = lambda _, df: df.assign(y=42.0).drop(columns=IGNORE_COLUMNS)

        # Mock data
        self.station_metadata = StationMapping(**{
            "location": "S1",
            "river": "R",
            "upstream_stations": ["S1", "S2"],
            "weather_locations": ["W1", "W2"]
        })
        self.now = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        self.stations_df = StationDataFrameSchema(pd.DataFrame({
            "location": sum([[f"S{i}"] * 4 for i in range(3)], []),
            "date": [self.now + timedelta(days=i) for i in range(-3, 1)] * 3,
            "level__m": [0.0 if j == 3 else i + (j / 10) for i in range(3) for j in range(4)]
        }))
        self.weather_df = WeatherDataFrameSchema(pd.DataFrame({
            "location": ["W1", "W1", "W1", "W1", "W1", "W2", "W2", "W2", "W2", "W2"],
            "date": [self.now + timedelta(days=i) for i in range(-3, 2)] * 2,
            "precipitation_sum": [0.1, 0.2, 0.3, 0.4, 0.5] * 2,
            "precipitation_hours": [1, 2, 3, 4, 5, 11, 12, 13, 14, 15]
        }))
        self.model_path = "mock_model_path"
        self.model_name = "mock_model_name"
        self.station_lag_days = [3, 1]
        self.weather_lag_days = [3, 1, 0, -1]
        self.forecast_days = 3

    def test_infer_naive(self):
        # WARNING: a reference for the prediction day is needed to run infer_from_raw_data
        # (in this case it is today)

        station_metadata = StationMapping(**{
            "location": "S1",
            "river": "R",
            "upstream_stations": ["S1"],
            "weather_locations": ["W1"]
        })
        stations_df = StationDataFrameSchema(pd.DataFrame({
            "location": ["S1"] * 2,
            "date": [self.now, self.now - timedelta(days=1)],
            "level__m": [0.0, 1.0]
        }))
        weather_df = WeatherDataFrameSchema(pd.DataFrame({
            "location": ["W1"],
            "date": [self.now],
            "precipitation_sum": [0.1],
            "precipitation_hours": [1.1]
        }))
        station_lag_days = [1]
        weather_lag_days = [0]

        result = infer_from_raw_data(
            self.model_manager,
            self.model_path,
            self.model_name,
            station_metadata,
            stations_df,
            weather_df,
            station_lag_days,
            weather_lag_days,
            self.forecast_days
        )

        expected_df = pd.DataFrame({
            "date": [self.now],
            "location": ["S1"],
            "level__m": [0.0],
            "lagabs01__level__m": [1.0],
            "s1__lagabs01__level__m": [1.0],
            "w1__forecast01__precipitation_sum": [0.1],
            "w1__forecast01__precipitation_hours": [1.1],
            "y": [42.0]
        })

        self.model_manager.load.assert_called_once_with(self.model_path, self.model_name)
        self.model_manager.infer.assert_called_once()
        self.assertIsInstance(result, pd.DataFrame)
        self.assertEqual(result["y"].values[0], 42.0)
        pd.testing.assert_frame_equal(result, expected_df, check_like=True)

    def test_infer(self):
        # WARNING: a reference for the prediction day is needed to run infer_from_raw_data
        # (in this case it is today - see setUp)

        result = infer_from_raw_data(
            self.model_manager,
            self.model_path,
            self.model_name,
            self.station_metadata,
            self.stations_df,
            self.weather_df,
            self.station_lag_days,
            self.weather_lag_days,
            self.forecast_days
        )

        expected_df = pd.DataFrame({
            "location": ["S1"],
            "date": [self.now],
            "level__m": [0.0],
            "lagabs01__level__m": [1.2],
            "lagabs03__level__m": [1.0],
            "s1__lagabs01__level__m": [1.2],
            "s2__lagabs01__level__m": [2.2],
            "s1__lagabs03__level__m": [1.0],
            "s2__lagabs03__level__m": [2.0],
            "w1__lagabs01__precipitation_sum": [0.3],
            "w1__lagabs01__precipitation_hours": [3.0],
            "w1__lagabs03__precipitation_sum": [0.1],
            "w1__lagabs03__precipitation_hours": [1.0],
            "w1__forecast01__precipitation_sum": [0.4],
            "w1__forecast01__precipitation_hours": [4.0],
            "w1__forecast02__precipitation_sum": [0.5],
            "w1__forecast02__precipitation_hours": [5.0],
            "w2__lagabs01__precipitation_sum": [0.3],
            "w2__lagabs01__precipitation_hours": [13.0],
            "w2__lagabs03__precipitation_sum": [0.1],
            "w2__lagabs03__precipitation_hours": [11.0],
            "w2__forecast01__precipitation_sum": [0.4],
            "w2__forecast01__precipitation_hours": [14.0],
            "w2__forecast02__precipitation_sum": [0.5],
            "w2__forecast02__precipitation_hours": [15.0],
            "y": [42.0]
        })

        self.model_manager.load.assert_called_once_with(self.model_path, self.model_name)
        self.model_manager.infer.assert_called_once()
        self.assertIsInstance(result, pd.DataFrame)
        self.assertEqual(result["y"].values[0], 42.0)
        pd.testing.assert_frame_equal(result, expected_df, check_like=True)


if __name__ == "__main__":
    unittest.main()
