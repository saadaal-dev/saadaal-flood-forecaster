"""
Unit tests for the compare-sensor-weather CLI command.
"""
import csv
import os
import tempfile
import unittest
from datetime import date, datetime
from unittest.mock import MagicMock, patch

import pandas as pd
from click.testing import CliRunner

from flood_forecaster_cli.commands.database_model import database_model


def _sensor_df(*rows):
    """Build a minimal SensorRainfallDataFrameSchema-compatible DataFrame."""
    return pd.DataFrame(
        rows,
        columns=["location", "date", "precipitation_sum", "precipitation_hours"],
    ).assign(date=lambda df: pd.to_datetime(df["date"]))


def _weather_df(*rows):
    """Build a minimal WeatherDataFrameSchema-compatible DataFrame."""
    return pd.DataFrame(
        rows,
        columns=["location", "date", "precipitation_sum", "precipitation_hours"],
    ).assign(date=lambda df: pd.to_datetime(df["date"]))


_CONFIG_PATCH = "flood_forecaster.utils.configuration.Config.__init__"
_SENSOR_LOAD_PATCH = "flood_forecaster_cli.commands.database_model.load_sensor_rainfall_db"
_WEATHER_LOAD_PATCH = "flood_forecaster_cli.commands.database_model.load_history_weather_db"
_GEO_PATCH = "flood_forecaster_cli.commands.database_model.build_sensor_location_mapping"

# Minimal station→location mapping used by most tests.
# "Elbarde" is the sensor station label; "bay__baydhaba" is its nearest forecast location.
_STATION_MAP = {"Elbarde": "bay__baydhaba"}

_SENSOR_CONFIG = {
    "sensor_stations_file": "data/static/sensor-stations.csv",
    "sensor_max_distance_km": "50",
    "rainfall_sensor_meaning": "Rainfall",
}
_STATIC_CONFIG = {"weather_location_data_path": "data/static/forecast-locations.csv"}


class TestCompareSensorWeatherCommand(unittest.TestCase):
    def _run(self, extra_args=None, sensor_df=None, weather_df=None,
             location="bay__baydhaba", station_map=None):
        runner = CliRunner()
        default_sensor = _sensor_df(("bay__baydhaba", "2025-01-01", 5.5, 2))
        default_weather = _weather_df(("bay__baydhaba", "2025-01-01", 4.0, 3))
        with (
            patch(_CONFIG_PATCH, return_value=None),
            patch(
                "flood_forecaster.utils.configuration.Config.load_sensor_config",
                return_value=_SENSOR_CONFIG,
            ),
            patch(
                "flood_forecaster.utils.configuration.Config.load_static_data_config",
                return_value=_STATIC_CONFIG,
            ),
            patch(_GEO_PATCH, return_value=station_map if station_map is not None else _STATION_MAP),
            patch(_SENSOR_LOAD_PATCH, return_value=default_sensor if sensor_df is None else sensor_df) as mock_sensor,
            patch(_WEATHER_LOAD_PATCH, return_value=default_weather if weather_df is None else weather_df) as mock_weather,
        ):
            args = [
                "compare-sensor-weather",
                "--location", location,
                "--date-from", "2025-01-01",
                "--date-to", "2025-01-31",
            ]
            if extra_args:
                args += extra_args
            result = runner.invoke(database_model, args)
            return result, mock_sensor, mock_weather

    # ------------------------------------------------------------------
    # basic happy-path
    # ------------------------------------------------------------------

    def test_exit_code_zero(self):
        result, _, _ = self._run()
        self.assertEqual(result.exit_code, 0, result.output)

    def test_output_contains_column_headers(self):
        result, _, _ = self._run()
        self.assertIn("sensor_precip_mm", result.output)
        self.assertIn("openmeteo_precip_mm", result.output)
        self.assertIn("delta_mm", result.output)

    def test_output_contains_location(self):
        result, _, _ = self._run()
        self.assertIn("bay__baydhaba", result.output)

    def test_delta_computed_correctly(self):
        """5.5 - 4.0 = 1.5 → should appear in formatted output."""
        result, _, _ = self._run()
        self.assertIn("1.50", result.output)

    # ------------------------------------------------------------------
    # loaders are called with the right arguments
    # ------------------------------------------------------------------

    def test_sensor_loader_receives_correct_args(self):
        _, mock_sensor, _ = self._run()
        call_kwargs = mock_sensor.call_args
        # second positional arg is locations list
        locations = call_kwargs.args[1] if call_kwargs.args else call_kwargs.kwargs.get("locations")
        self.assertIn("bay__baydhaba", locations)

    def test_weather_loader_receives_correct_args(self):
        _, _, mock_weather = self._run()
        call_kwargs = mock_weather.call_args
        locations = call_kwargs.args[1] if call_kwargs.args else call_kwargs.kwargs.get("locations")
        self.assertIn("bay__baydhaba", locations)

    # ------------------------------------------------------------------
    # multi-location support
    # ------------------------------------------------------------------

    def test_multiple_locations_passed_to_loaders(self):
        sensor_df = _sensor_df(
            ("loc_a", "2025-01-01", 3.0, 1),
            ("loc_b", "2025-01-01", 2.5, 1),
        )
        weather_df = _weather_df(
            ("loc_a", "2025-01-01", 3.1, 2),
            ("loc_b", "2025-01-01", 2.4, 2),
        )
        runner = CliRunner()
        with (
            patch(_CONFIG_PATCH, return_value=None),
            patch("flood_forecaster.utils.configuration.Config.load_sensor_config", return_value=_SENSOR_CONFIG),
            patch("flood_forecaster.utils.configuration.Config.load_static_data_config", return_value=_STATIC_CONFIG),
            patch(_GEO_PATCH, return_value={}),  # no sensor-label aliases for these synthetic locations
            patch(_SENSOR_LOAD_PATCH, return_value=sensor_df) as mock_sensor,
            patch(_WEATHER_LOAD_PATCH, return_value=weather_df),
        ):
            result = runner.invoke(
                database_model,
                [
                    "compare-sensor-weather",
                    "--location", "loc_a",
                    "--location", "loc_b",
                    "--date-from", "2025-01-01",
                    "--date-to", "2025-01-31",
                ],
            )
        self.assertEqual(result.exit_code, 0, result.output)
        locations_arg = mock_sensor.call_args.args[1]
        self.assertIn("loc_a", locations_arg)
        self.assertIn("loc_b", locations_arg)

    # ------------------------------------------------------------------
    # sensor station label → forecast location resolution
    # ------------------------------------------------------------------

    def test_sensor_station_label_resolved_to_forecast_location(self):
        """Passing a sensor station label (e.g. 'Elbarde') should be silently resolved
        to its nearest forecast location label ('bay__baydhaba') so that both loaders
        receive a valid pipeline location key."""
        station_map = {"Elbarde": "bay__baydhaba"}
        sensor_df = _sensor_df(("bay__baydhaba", "2025-01-01", 5.5, 2))
        weather_df = _weather_df(("bay__baydhaba", "2025-01-01", 4.0, 3))
        result, mock_sensor, mock_weather = self._run(
            location="Elbarde",
            station_map=station_map,
            sensor_df=sensor_df,
            weather_df=weather_df,
        )
        self.assertEqual(result.exit_code, 0, result.output)
        # Resolution should be logged
        self.assertIn("bay__baydhaba", result.output)
        # Both loaders must receive the resolved forecast location, not the raw sensor label
        sensor_locs = mock_sensor.call_args.args[1]
        self.assertIn("bay__baydhaba", sensor_locs)
        self.assertNotIn("Elbarde", sensor_locs)
        weather_locs = mock_weather.call_args.args[1]
        self.assertIn("bay__baydhaba", weather_locs)
        self.assertNotIn("Elbarde", weather_locs)

    def test_forecast_location_label_passes_through_unchanged(self):
        """A valid pipeline location label should not be modified by the resolution step."""
        result, mock_sensor, _ = self._run(location="bay__baydhaba", station_map={})
        self.assertEqual(result.exit_code, 0, result.output)
        sensor_locs = mock_sensor.call_args.args[1]
        self.assertIn("bay__baydhaba", sensor_locs)

    # ------------------------------------------------------------------
    # N/A handling for missing data
    # ------------------------------------------------------------------

    def test_na_displayed_for_sensor_gap(self):
        """Row present in Open-Meteo but absent from sensor → 'N/A' for sensor column."""
        sensor_df = _sensor_df()  # empty
        weather_df = _weather_df(("bay__baydhaba", "2025-01-01", 4.0, 3))
        result, _, _ = self._run(sensor_df=sensor_df, weather_df=weather_df)
        self.assertEqual(result.exit_code, 0, result.output)
        self.assertIn("N/A", result.output)

    def test_na_displayed_for_weather_gap(self):
        """Row present in sensor but absent from Open-Meteo → 'N/A' for Open-Meteo column."""
        sensor_df = _sensor_df(("bay__baydhaba", "2025-01-01", 5.5, 2))
        weather_df = _weather_df()  # empty
        result, _, _ = self._run(sensor_df=sensor_df, weather_df=weather_df)
        self.assertEqual(result.exit_code, 0, result.output)
        self.assertIn("N/A", result.output)

    # ------------------------------------------------------------------
    # --output CSV
    # ------------------------------------------------------------------

    def test_csv_saved_when_output_given(self):
        with tempfile.NamedTemporaryFile(suffix=".csv", delete=False) as f:
            tmp_path = f.name
        try:
            result, _, _ = self._run(extra_args=["--output", tmp_path])
            self.assertEqual(result.exit_code, 0, result.output)
            self.assertIn("Saved comparison", result.output)
            self.assertTrue(os.path.exists(tmp_path))
            with open(tmp_path) as csvfile:
                reader = csv.DictReader(csvfile)
                rows = list(reader)
            self.assertTrue(len(rows) >= 1)
            self.assertIn("sensor_precip_mm", rows[0])
            self.assertIn("openmeteo_precip_mm", rows[0])
            self.assertIn("delta_mm", rows[0])
        finally:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)

    def test_no_csv_saved_without_output_flag(self):
        """When --output is not given, no CSV message should appear."""
        result, _, _ = self._run()
        self.assertNotIn("Saved comparison", result.output)

    # ------------------------------------------------------------------
    # summary row count line
    # ------------------------------------------------------------------

    def test_summary_row_count_displayed(self):
        result, _, _ = self._run()
        # Should show something like "1 rows | 1 sensor, 1 Open-Meteo"
        self.assertIn("rows |", result.output)
        self.assertIn("sensor", result.output)
        self.assertIn("Open-Meteo", result.output)

    # ------------------------------------------------------------------
    # missing required options
    # ------------------------------------------------------------------

    def test_missing_location_fails(self):
        runner = CliRunner()
        with patch(_CONFIG_PATCH, return_value=None):
            result = runner.invoke(
                database_model,
                ["compare-sensor-weather", "--date-from", "2025-01-01", "--date-to", "2025-01-31"],
            )
        self.assertNotEqual(result.exit_code, 0)

    def test_missing_date_from_fails(self):
        runner = CliRunner()
        with patch(_CONFIG_PATCH, return_value=None):
            result = runner.invoke(
                database_model,
                ["compare-sensor-weather", "--location", "bay__baydhaba", "--date-to", "2025-01-31"],
            )
        self.assertNotEqual(result.exit_code, 0)


if __name__ == "__main__":
    unittest.main()
