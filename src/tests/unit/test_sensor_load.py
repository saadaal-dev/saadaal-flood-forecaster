import unittest
from datetime import date, datetime, timedelta
from unittest.mock import MagicMock, patch

import pandas as pd

from flood_forecaster.data_ingestion.load import (
    load_inference_sensor_rainfall,
    load_sensor_rainfall_db,
)
from flood_forecaster.utils.configuration import Config, DataSourceType


def _make_config(weather_lag_days="[1, 3, 7]"):
    cfg = MagicMock(spec=Config)
    cfg.load_model_config.return_value = {"weather_lag_days": weather_lag_days}
    cfg.load_sensor_config.return_value = {
        "sensor_stations_file": "data/static/sensor-stations.csv",
        "rainfall_sensor_meaning": "Rainfall",
        "sensor_max_distance_km": "50",
    }
    cfg.load_static_data_config.return_value = {
        "weather_location_data_path": "data/static/forecast-locations.csv",
    }
    cfg.get_data_source_type.return_value = DataSourceType.DATABASE
    return cfg


def _raw_sensor_rows(dates, values, station_id="BAIDOA_MOH"):
    return pd.DataFrame({
        "id": range(len(dates)),
        "station_id": [station_id] * len(dates),
        "sensor_meaning": ["Rainfall"] * len(dates),
        "reading_ts": [pd.Timestamp(d) for d in dates],
        "value": values,
        "sensor_id": ["S1"] * len(dates),
        "original_date": [None] * len(dates),
        "original_time": [None] * len(dates),
        "firmware": [None] * len(dates),
        "ingested_at": [None] * len(dates),
    })


class TestLoadSensorRainfallDb(unittest.TestCase):

    @patch("flood_forecaster.data_ingestion.load.build_sensor_location_mapping")
    def test_returns_empty_when_no_stations_map_to_location(self, mock_mapping):
        mock_mapping.return_value = {}
        result = load_sensor_rainfall_db(_make_config(), ["bay__baydhaba"], date(2025, 1, 1), date(2025, 1, 7))
        self.assertIsInstance(result, pd.DataFrame)
        self.assertEqual(len(result), 0)

    @patch("flood_forecaster.data_ingestion.load.DatabaseConnection")
    @patch("flood_forecaster.data_ingestion.load.build_sensor_location_mapping")
    def test_aggregates_daily_totals(self, mock_mapping, mock_db_cls):
        mock_mapping.return_value = {"BAIDOA_MOH": "bay__baydhaba"}
        mock_db_cls.return_value.engine = MagicMock()

        raw = _raw_sensor_rows(
            dates=["2025-01-01 06:00:00", "2025-01-01 12:00:00", "2025-01-02 06:00:00"],
            values=["2.5", "3.0", "1.0"],
        )

        with patch("flood_forecaster.data_ingestion.load.pd.read_sql", return_value=raw):
            result = load_sensor_rainfall_db(_make_config(), ["bay__baydhaba"], date(2025, 1, 1), date(2025, 1, 2))

        self.assertSetEqual(set(result.columns), {"location", "date", "precipitation_sum", "precipitation_hours"})
        self.assertEqual(len(result), 2)

        day1 = result[result["date"] == pd.Timestamp("2025-01-01")].iloc[0]
        self.assertAlmostEqual(float(day1["precipitation_sum"]), 5.5)
        self.assertEqual(int(day1["precipitation_hours"]), 2)

        day2 = result[result["date"] == pd.Timestamp("2025-01-02")].iloc[0]
        self.assertAlmostEqual(float(day2["precipitation_sum"]), 1.0)
        self.assertEqual(int(day2["precipitation_hours"]), 1)

    @patch("flood_forecaster.data_ingestion.load.DatabaseConnection")
    @patch("flood_forecaster.data_ingestion.load.build_sensor_location_mapping")
    def test_invalid_values_are_dropped(self, mock_mapping, mock_db_cls):
        """Sentinel strings '---', 'NULL', '-999.99' must be excluded; '2.0' kept."""
        mock_mapping.return_value = {"BAIDOA_MOH": "bay__baydhaba"}
        mock_db_cls.return_value.engine = MagicMock()

        raw = _raw_sensor_rows(
            dates=["2025-01-01 06:00:00"] * 4,
            values=["---", "NULL", "-999.99", "2.0"],
        )

        with patch("flood_forecaster.data_ingestion.load.pd.read_sql", return_value=raw):
            result = load_sensor_rainfall_db(_make_config(), ["bay__baydhaba"], date(2025, 1, 1), date(2025, 1, 1))

        self.assertEqual(len(result), 1)
        self.assertAlmostEqual(float(result.iloc[0]["precipitation_sum"]), 2.0)
        self.assertEqual(int(result.iloc[0]["precipitation_hours"]), 1)

    @patch("flood_forecaster.data_ingestion.load.DatabaseConnection")
    @patch("flood_forecaster.data_ingestion.load.build_sensor_location_mapping")
    def test_empty_db_result_returns_empty_dataframe(self, mock_mapping, mock_db_cls):
        mock_mapping.return_value = {"BAIDOA_MOH": "bay__baydhaba"}
        mock_db_cls.return_value.engine = MagicMock()

        empty_raw = pd.DataFrame(columns=[
            "id", "station_id", "sensor_meaning", "reading_ts", "value",
            "sensor_id", "original_date", "original_time", "firmware", "ingested_at",
        ])

        with patch("flood_forecaster.data_ingestion.load.pd.read_sql", return_value=empty_raw):
            result = load_sensor_rainfall_db(_make_config(), ["bay__baydhaba"], date(2025, 1, 1), date(2025, 1, 1))

        self.assertIsInstance(result, pd.DataFrame)
        self.assertEqual(len(result), 0)

    @patch("flood_forecaster.data_ingestion.load.DatabaseConnection")
    @patch("flood_forecaster.data_ingestion.load.build_sensor_location_mapping")
    def test_all_values_only_counts_valid_rows_in_precipitation_hours(self, mock_mapping, mock_db_cls):
        """precipitation_hours must equal the count of *valid* readings per day."""
        mock_mapping.return_value = {"BAIDOA_MOH": "bay__baydhaba"}
        mock_db_cls.return_value.engine = MagicMock()

        raw = _raw_sensor_rows(
            dates=["2025-01-01 06:00:00", "2025-01-01 12:00:00", "2025-01-01 18:00:00"],
            values=["1.0", "---", "3.0"],
        )

        with patch("flood_forecaster.data_ingestion.load.pd.read_sql", return_value=raw):
            result = load_sensor_rainfall_db(_make_config(), ["bay__baydhaba"], date(2025, 1, 1), date(2025, 1, 1))

        self.assertEqual(int(result.iloc[0]["precipitation_hours"]), 2)
        self.assertAlmostEqual(float(result.iloc[0]["precipitation_sum"]), 4.0)


class TestLoadInferenceSensorRainfall(unittest.TestCase):

    @patch("flood_forecaster.data_ingestion.load.load_sensor_rainfall_db")
    def test_calls_db_with_correct_lag_window(self, mock_load_db):
        """With weather_lag_days=[1,3,7], min_date = today - 7 days."""
        now = datetime(2025, 6, 15)
        cfg = _make_config(weather_lag_days="[1, 3, 7]")

        sensor_df = pd.DataFrame({
            "location": ["bay__baydhaba"] * 7,
            "date": pd.date_range("2025-06-08", periods=7),
            "precipitation_sum": [1.0] * 7,
            "precipitation_hours": [1] * 7,
        })
        mock_load_db.return_value = sensor_df

        load_inference_sensor_rainfall(cfg, ["bay__baydhaba"], date=now)

        called_begin = mock_load_db.call_args[0][2]
        self.assertEqual(called_begin, date(2025, 6, 8))  # 2025-06-15 - 7 days

    @patch("flood_forecaster.data_ingestion.load.load_sensor_rainfall_db")
    def test_returns_empty_dataframe_when_no_data(self, mock_load_db):
        mock_load_db.return_value = pd.DataFrame(
            columns=["location", "date", "precipitation_sum", "precipitation_hours"]
        )
        result = load_inference_sensor_rainfall(_make_config(), ["bay__baydhaba"], date=datetime(2025, 6, 15))
        self.assertIsInstance(result, pd.DataFrame)
        self.assertEqual(len(result), 0)

    @patch("flood_forecaster.data_ingestion.load.load_sensor_rainfall_db")
    def test_result_columns_match_weather_schema(self, mock_load_db):
        """Output columns must be identical to WeatherDataFrameSchema."""
        now = datetime(2025, 6, 15)
        cfg = _make_config(weather_lag_days="[1, 3, 7]")

        sensor_df = pd.DataFrame({
            "location": ["bay__baydhaba"] * 7,
            "date": pd.date_range("2025-06-08", periods=7),
            "precipitation_sum": [1.5] * 7,
            "precipitation_hours": [2] * 7,
        })
        mock_load_db.return_value = sensor_df

        result = load_inference_sensor_rainfall(cfg, ["bay__baydhaba"], date=now)

        self.assertSetEqual(
            set(result.columns),
            {"location", "date", "precipitation_sum", "precipitation_hours"},
        )


if __name__ == "__main__":
    unittest.main()
