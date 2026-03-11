"""Unit tests for river level ORM models."""

import datetime
import unittest
from decimal import Decimal

from flood_forecaster.data_model.river_level import RiverStationMetadata, StationRiverData


class TestRiverStationMetadata(unittest.TestCase):
    """Test RiverStationMetadata ORM model."""

    def test_create_river_station_metadata(self):
        """Test creating a RiverStationMetadata instance."""
        station = RiverStationMetadata(
            station_number="A-101",
            station_name="Jowhar",
            river_name="Shabelle",
            region="Middle Shabelle",
            status="Active",
            first_date=datetime.date(2020, 1, 1),
            latitude=2.78,
            longitude=45.50,
            moderate_flood_risk_m=4.2,
            high_flood_risk_m=5.0,
            bankfull_m=4.8,
            maximum_depth_m=6.1,
            maximum_width_m=110.0,
            maximum_flow_m=2200.0,
            elevation=95.0,
            swalim_internal_id=301,
        )

        self.assertEqual(station.station_name, "Jowhar")
        self.assertEqual(station.swalim_internal_id, 301)
        self.assertEqual(station.maximum_flow_m, 2200.0)
        self.assertEqual(station.elevation, 95.0)

    def test_station_metadata_table_mapping(self):
        """Test table and schema mapping are correct."""
        self.assertEqual(RiverStationMetadata.__tablename__, "river_station_metadata")
        self.assertEqual(RiverStationMetadata.__table__.schema, "flood_forecaster")

    def test_station_name_is_primary_key(self):
        """Test ORM has a primary key configured (required by SQLAlchemy mapper)."""
        pk_columns = [col.name for col in RiverStationMetadata.__table__.primary_key.columns]
        self.assertEqual(pk_columns, ["station_name"])

    def test_station_metadata_column_names_match_db(self):
        """Test columns that recently changed names match DB DDL."""
        columns = set(RiverStationMetadata.__table__.columns.keys())
        self.assertIn("maximum_flow_m", columns)
        self.assertIn("elevation", columns)
        self.assertNotIn("maximum_flow_m3_s", columns)
        self.assertNotIn("elevation_m", columns)


class TestStationRiverData(unittest.TestCase):
    """Test StationRiverData ORM model."""

    def test_create_station_river_data(self):
        """Test creating a StationRiverData instance with decimal reading."""
        reading = Decimal("3.45")
        station_data = StationRiverData(
            station_id=12,
            reading=reading,
            reading_date=datetime.date(2026, 1, 15),
        )

        self.assertEqual(station_data.station_id, 12)
        self.assertEqual(station_data.reading, reading)
        self.assertEqual(station_data.reading_date, datetime.date(2026, 1, 15))

    def test_reading_can_be_null(self):
        """Test reading column allows null values."""
        reading_column = StationRiverData.__table__.columns["reading"]
        self.assertTrue(reading_column.nullable)

    def test_station_river_data_table_mapping(self):
        """Test table and schema mapping are correct."""
        self.assertEqual(StationRiverData.__tablename__, "station_river_data")
        self.assertEqual(StationRiverData.__table__.schema, "public")


if __name__ == "__main__":
    unittest.main()
