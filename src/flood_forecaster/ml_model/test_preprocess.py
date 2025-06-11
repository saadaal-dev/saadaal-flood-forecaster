import unittest

import pandas as pd

from src.flood_forecaster.ml_model.preprocess import preprocess_diff
from src.flood_forecaster.utils.configuration import StationMapping


class TestPreprocessDiff(unittest.TestCase):
    def create_station_df(self):
        return pd.DataFrame({
            "location": ["S1", "S1", "S1", "S2", "S2", "S2"],
            "date": [pd.Timestamp("2021-01-01"), pd.Timestamp("2021-01-02"), pd.Timestamp("2021-01-03")] * 2,
            "level__m": [10.0, 11.0, 13.0, 23.0, 24.0, 25.0],
        })
    
    def create_weather_df(self):
        return pd.DataFrame({
            "location": ["W1", "W1", "W1"],
            "date": [pd.Timestamp("2021-01-01"), pd.Timestamp("2021-01-02"), pd.Timestamp("2021-01-03")],
            "precipitation_sum": [0.1, 0.2, 0.3],
            "precipitation_hours": [1, 2, 3],
        })
    
    def _add_sin_cos_features(self, df):
        """
        Add sine and cosine features for month and day of the year.
        """
        import numpy as np
        df["month_sin"] = np.sin((df["date"].dt.month - 1) * (2 * np.pi / 12))
        df["month_cos"] = np.cos((df["date"].dt.month - 1) * (2 * np.pi / 12))
        df["dayofyear_sin"] = np.sin((df["date"].dt.dayofyear - 1) * (2 * np.pi / 365))
        df["dayofyear_cos"] = np.cos((df["date"].dt.dayofyear - 1) * (2 * np.pi / 365))
        return df
    
    def _add_month_day_features(self, df):
        """
        Add month and day of the year features.
        """
        df["month"] = df["date"].dt.month
        df["dayofyear"] = df["date"].dt.dayofyear
        return df

    def test_simple_1(self):
        """
        Test a simple case with one relevant station and one weather location.
        The expected output has:
         - 1 lag day for the station
         - 1 lag day for the weather location
         - 1 forecast day for the weather location (same day)
        """
        station_metadata = StationMapping(
            location="S1",
            river="R",
            upstream_stations=["S1"],
            weather_locations=["W1"],
        )

        station_lag_days = [1]
        weather_lag_days = [1, 0]

        expected_df = pd.DataFrame({
            "location": ["S1", "S1"],
            "date": [pd.Timestamp("2021-01-02"), pd.Timestamp("2021-01-03")],
            "level__m": [11.0, 13.0],
            "lag01__level__m": [10.0, 11.0],
            "s1__lag01__level__m": [10.0, 11.0],
            "w1__lag01__precipitation_sum": [0.1, 0.2],
            "w1__lag01__precipitation_hours": [1.0, 2.0],
            "w1__forecast01__precipitation_sum": [0.2, 0.3],
            "w1__forecast01__precipitation_hours": [2.0, 3.0],
            "y": [1.0, 2.0],
        })
        self._add_sin_cos_features(expected_df)
        self._add_month_day_features(expected_df)

        stations_df = self.create_station_df()
        weather_df = self.create_weather_df()

        actual_df = preprocess_diff(station_metadata, stations_df, weather_df, station_lag_days, weather_lag_days, forecast_days=1, infer=False)

        try:
            pd.testing.assert_frame_equal(expected_df, actual_df, check_like=True)
        except AssertionError as e:
            # disable DF print truncation (backup is restored at the end of the test)
            max_columns = pd.get_option('display.max_columns')
            pd.set_option('display.max_columns', None)
            print("Expected:")
            print(expected_df)
            print("Actual:")
            print(actual_df)
            pd.set_option('display.max_columns', max_columns)
            raise e
    
    def test_simple_2(self):
        """
        Test a simple case with one relevant station and one weather location.
        Assuming 2021-01-02 is today, we set forecast_days=1, then the prediction will refer to 2021-01-02 (today).

        The expected output has:
         - 1 lag day for the station
         - 1 lag day for the weather location
         - 2 forecast days for the weather location (same day and next day)

        NOTE: we are not explicitly setting the date for the prediction, it is inferred from the data
              (only entries fitting the lag and forecast days constraints).
        """
        station_metadata = StationMapping(
            location="S1",
            river="R",
            upstream_stations=["S1"],
            weather_locations=["W1"],
        )

        station_lag_days = [1]
        weather_lag_days = [1, 0, -1]

        expected_df = pd.DataFrame({
            "location": ["S1"],
            "date": [pd.Timestamp("2021-01-02")],
            "level__m": [11.0],
            "lag01__level__m": [10.0],
            "s1__lag01__level__m": [10.0],
            "w1__lag01__precipitation_sum": [0.1],
            "w1__lag01__precipitation_hours": [1.0],
            "w1__forecast01__precipitation_sum": [0.2],
            "w1__forecast01__precipitation_hours": [2.0],
            "w1__forecast02__precipitation_sum": [0.3],
            "w1__forecast02__precipitation_hours": [3.0],
            "y": [1.0],
        })
        self._add_sin_cos_features(expected_df)
        self._add_month_day_features(expected_df)

        stations_df = self.create_station_df()
        weather_df = self.create_weather_df()

        actual_df = preprocess_diff(station_metadata, stations_df, weather_df, station_lag_days, weather_lag_days, forecast_days=1, infer=False)

        try:
            pd.testing.assert_frame_equal(expected_df, actual_df, check_like=True)
        except AssertionError as e:
            # disable DF print truncation (backup is restored at the end of the test)
            max_columns = pd.get_option('display.max_columns')
            pd.set_option('display.max_columns', None)
            print("Expected:")
            print(expected_df)
            print("Actual:")
            print(actual_df)
            pd.set_option('display.max_columns', max_columns)
            raise e

    def test_simple_3(self):
        """
        Test a simple case with one relevant station and one weather location.
        This test makes explicit which date is used for the prediction.
        Assuming 2021-01-02 is today, we set forecast_days=2, then the prediction will refer to 2021-01-03 (today+1).

        The expected output has:
         - 1 lag day for the station
         - 2 forecast days for the weather location (same day and next day)
        """
        station_metadata = StationMapping(
            location="S1",
            river="R",
            upstream_stations=["S1"],
            weather_locations=["W1"],
        )

        station_lag_days = [1]
        weather_lag_days = [0, -1]
        forecast_days = 2

        # Data available for predictions:
        # pd.Timestamp("2021-01-02") is the only date fitting the lag and forecast days constraints:
        # # - lag day for station(1): pd.Timestamp("2021-01-01")
        # # - forecast day for weather(0): pd.Timestamp("2021-01-02")
        # # - forecast day for weather(-1): pd.Timestamp("2021-01-03")

        # Expected output:
        # date: pd.Timestamp("2021-01-02") is the date where the prediction is made,
        # (implicit) pd.Timestamp("2021-01-02").add(pd.Timedelta(days=(forecast_days-1))) = pd.Timestamp("2021-01-03") is the date where the prediction is made for
        # level__m: 13.0 is the absolute level at pd.Timestamp("2021-01-03") (prediction)
        # y: 1.0 is the difference between level__m (prediction) and lag01__level__m (last known observation) = 13.0 - 10.0 = 1.0
        expected_df = pd.DataFrame({
            "location": ["S1"],
            "date": [pd.Timestamp("2021-01-02")],
            "level__m": [13.0],
            "lag01__level__m": [10.0],
            "s1__lag01__level__m": [10.0],
            "w1__forecast01__precipitation_sum": [0.2],
            "w1__forecast01__precipitation_hours": [2.0],
            "w1__forecast02__precipitation_sum": [0.3],
            "w1__forecast02__precipitation_hours": [3.0],
            "y": [3.0],
        })

        self._add_sin_cos_features(expected_df)
        self._add_month_day_features(expected_df)

        stations_df = self.create_station_df()
        weather_df = self.create_weather_df()

        actual_df = preprocess_diff(station_metadata, stations_df, weather_df, station_lag_days, weather_lag_days, forecast_days=forecast_days, infer=False)

        try:
            pd.testing.assert_frame_equal(expected_df, actual_df, check_like=True)
        except AssertionError as e:
            # disable DF print truncation (backup is restored at the end of the test)
            max_columns = pd.get_option('display.max_columns')
            pd.set_option('display.max_columns', None)
            print("Expected:")
            print(expected_df)
            print("Actual:")
            print(actual_df)
            pd.set_option('display.max_columns', max_columns)
            raise e


if __name__ == '__main__':
    unittest.main()
