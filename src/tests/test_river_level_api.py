import datetime
import unittest

from src.flood_forecaster import DatabaseConnection
from src.flood_forecaster.data_ingestion.swalim.river_level_api import fetch_latest_river_data, insert_river_data
from src.flood_forecaster.data_model.river_level import HistoricalRiverLevel
from src.flood_forecaster.utils.configuration import Config


class TestConfig(unittest.TestCase):

    def test_fetch_latest_river_data(self):
        # Mock configuration
        config = Config("src/tests/mock_config.ini")
        historical_river_levels = fetch_latest_river_data(config)
        self.assertEqual(len(historical_river_levels), 7, "Expected to fetch 7 historical river levels")
        river_names = [i.location_name for i in historical_river_levels]
        self.assertIn("Luuq", river_names, "Expected river station Luuq to be present in the fetched data")

    def test_insert_river_data(self):
        config = Config("src/tests/mock_config.ini")
        database_connection = DatabaseConnection(config)

        # Mock data
        river_levels = [
            HistoricalRiverLevel(location_name="test", date=datetime.date(3000, 10, 1), level_m=5.0, ),
            HistoricalRiverLevel(location_name="test", date=datetime.date(3000, 10, 1), level_m=4.5, )
        ]

        # Insert data into the database
        insert_river_data(river_levels, config)

        from sqlalchemy import select, delete
        with database_connection.engine.connect() as conn:
            # Read rows
            rows_to_delete = conn.execute(
                select(HistoricalRiverLevel).where(HistoricalRiverLevel.location_name == "test")
            ).all()

            # Delete rows
            conn.execute(
                delete(HistoricalRiverLevel).where(HistoricalRiverLevel.location_name == "test")
            )
            conn.commit()

            # Print deleted rows
        self.assertEqual(len(rows_to_delete), 2, "Expected to delete 2 rows")
        for row in rows_to_delete:
            print(f"Deleted row: {row.location_name}, {row.date}, {row.level_m}")
            self.assertEqual(row.location_name, "test")
