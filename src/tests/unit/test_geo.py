import os
import tempfile
import unittest

from flood_forecaster.utils.geo import build_sensor_location_mapping, haversine_distance


class TestHaversineDistance(unittest.TestCase):

    def test_same_point_is_zero(self):
        self.assertAlmostEqual(haversine_distance(3.85, 45.57, 3.85, 45.57), 0.0, places=6)

    def test_known_distance_baidoa_to_buloburti(self):
        """Baidoa ~(3.11, 43.62) to Bulo Burti ~(3.86, 45.57): roughly 231 km."""
        dist = haversine_distance(3.1108195, 43.6233185, 3.85702, 45.56727)
        self.assertGreater(dist, 220)
        self.assertLess(dist, 240)

    def test_symmetry(self):
        lat1, lon1, lat2, lon2 = 3.1, 43.6, 4.7, 45.2
        self.assertAlmostEqual(
            haversine_distance(lat1, lon1, lat2, lon2),
            haversine_distance(lat2, lon2, lat1, lon1),
            places=6,
        )

    def test_returns_float(self):
        self.assertIsInstance(haversine_distance(0.0, 0.0, 1.0, 1.0), float)


class TestBuildSensorLocationMapping(unittest.TestCase):

    def _write(self, path: str, content: str) -> None:
        with open(path, "w") as f:
            f.write(content)

    def test_nearest_neighbour_mapping(self):
        """BAIDOA_MOH (3.11, 43.62) must map to bay__baydhaba (3.27, 43.64)."""
        sensor_csv = (
            "sensor, label, latitude, longitude, type\n"
            "Baidoa, BAIDOA_MOH, 3.1108195, 43.6233185, weather station\n"
        )
        forecast_csv = (
            "label,region,district,latitude,longitude,remarks\n"
            "bay__baydhaba,Bay,Baydhaba,3.26636,43.63929,\n"
            "hiran__belet_weyne,Hiran,Belet Weyne,4.73597,45.20596,river station\n"
        )
        with tempfile.TemporaryDirectory() as d:
            s = os.path.join(d, "s.csv")
            f = os.path.join(d, "f.csv")
            self._write(s, sensor_csv)
            self._write(f, forecast_csv)
            mapping = build_sensor_location_mapping(s, f)

        self.assertEqual(mapping.get("BAIDOA_MOH"), "bay__baydhaba")

    def test_max_distance_excludes_far_stations(self):
        """A station in Nairobi (~-1.3, 36.8) must be excluded when max_distance_km=50."""
        sensor_csv = (
            "sensor, label, latitude, longitude, type\n"
            "Nairobi, NBI_SENSOR, -1.286389, 36.817223, weather station\n"
        )
        forecast_csv = (
            "label,region,district,latitude,longitude,remarks\n"
            "bay__baydhaba,Bay,Baydhaba,3.26636,43.63929,\n"
        )
        with tempfile.TemporaryDirectory() as d:
            s = os.path.join(d, "s.csv")
            f = os.path.join(d, "f.csv")
            self._write(s, sensor_csv)
            self._write(f, forecast_csv)
            mapping = build_sensor_location_mapping(s, f, max_distance_km=50)

        self.assertEqual(mapping, {})

    def test_duplicate_labels_deduplicated(self):
        """Same station_id with two sensor types must appear exactly once in mapping."""
        sensor_csv = (
            "sensor, label, latitude, longitude, type\n"
            "Baidoa, BAIDOA_MOH, 3.1108195, 43.6233185, weather station\n"
            "Baidoa, BAIDOA_MOH, 3.1108195, 43.6233185, water level sensor\n"
        )
        forecast_csv = (
            "label,region,district,latitude,longitude,remarks\n"
            "bay__baydhaba,Bay,Baydhaba,3.26636,43.63929,\n"
        )
        with tempfile.TemporaryDirectory() as d:
            s = os.path.join(d, "s.csv")
            f = os.path.join(d, "f.csv")
            self._write(s, sensor_csv)
            self._write(f, forecast_csv)
            mapping = build_sensor_location_mapping(s, f)

        self.assertEqual(list(mapping.keys()).count("BAIDOA_MOH"), 1)

    def test_empty_sensor_file_returns_empty_mapping(self):
        sensor_csv = "sensor, label, latitude, longitude, type\n"
        forecast_csv = (
            "label,region,district,latitude,longitude,remarks\n"
            "bay__baydhaba,Bay,Baydhaba,3.26636,43.63929,\n"
        )
        with tempfile.TemporaryDirectory() as d:
            s = os.path.join(d, "s.csv")
            f = os.path.join(d, "f.csv")
            self._write(s, sensor_csv)
            self._write(f, forecast_csv)
            mapping = build_sensor_location_mapping(s, f)

        self.assertEqual(mapping, {})

    def test_multiple_sensors_map_independently(self):
        """Two sensors in different areas must each map to their nearest location."""
        sensor_csv = (
            "sensor, label, latitude, longitude, type\n"
            "Baidoa, BAIDOA_MOH, 3.1108195, 43.6233185, weather station\n"
            "Afgooye, MOHADM_AFG, 2.140976, 45.1085611, weather station\n"
        )
        forecast_csv = (
            "label,region,district,latitude,longitude,remarks\n"
            "bay__baydhaba,Bay,Baydhaba,3.26636,43.63929,\n"
            "lower_shabelle__afgooye,Lower Shabelle,Afgooye,2.2354874,44.9969419,\n"
        )
        with tempfile.TemporaryDirectory() as d:
            s = os.path.join(d, "s.csv")
            f = os.path.join(d, "f.csv")
            self._write(s, sensor_csv)
            self._write(f, forecast_csv)
            mapping = build_sensor_location_mapping(s, f)

        self.assertEqual(mapping.get("BAIDOA_MOH"), "bay__baydhaba")
        self.assertEqual(mapping.get("MOHADM_AFG"), "lower_shabelle__afgooye")


if __name__ == "__main__":
    unittest.main()
