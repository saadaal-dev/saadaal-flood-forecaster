import datetime
import unittest

import pytest
from sqlalchemy import delete, insert, select, text
from sqlalchemy.exc import IntegrityError

from flood_forecaster import DatabaseConnection
from flood_forecaster.data_ingestion.swalim.river_level_api import fetch_latest_river_data, insert_river_data
from flood_forecaster.data_model.river_level import HistoricalRiverLevel
from flood_forecaster.utils.configuration import Config


@pytest.mark.integration_db
class TestConfig(unittest.TestCase):

    def test_fetch_latest_river_data(self):
        # Mock configuration
        config = Config("src/tests/mock_config.ini")
        historical_river_levels = fetch_latest_river_data(config)
        self.assertEqual(len(historical_river_levels), 7, "Expected to fetch 7 historical river levels")
        river_names = [i.location_name for i in historical_river_levels]
        self.assertIn("Luuq", river_names, "Expected river station Luuq to be present in the fetched data")


TEST_STATION = "DATA005_INTEGRATION_TEST"
TEST_DATE = datetime.date(3000, 10, 1)


@pytest.mark.integration_db
class TestInsertRiverData(unittest.TestCase):
    """
    Database-backed tests for the (location_name, date) uniqueness guarantee (DATA-005).

    Requires `sql/add_historical_river_level_unique_constraint.sql` to have been
    applied to the target database. Before DATA-005 an earlier version of this test
    asserted that two rows for the same station and day both landed, which is exactly
    the behaviour that produced 962 excess rows in production.
    """

    def setUp(self):
        self.config = Config("src/tests/mock_config.ini")
        self.database_connection = DatabaseConnection(self.config)
        self._delete_test_rows()
        self.addCleanup(self._delete_test_rows)

    def _delete_test_rows(self):
        with self.database_connection.engine.connect() as conn:
            conn.execute(
                delete(HistoricalRiverLevel).where(
                    HistoricalRiverLevel.location_name == TEST_STATION
                )
            )
            conn.commit()

    def _stored(self):
        with self.database_connection.engine.connect() as conn:
            return conn.execute(
                select(HistoricalRiverLevel.date, HistoricalRiverLevel.level_m)
                .where(HistoricalRiverLevel.location_name == TEST_STATION)
                .order_by(HistoricalRiverLevel.date)
            ).all()

    @staticmethod
    def _level(day, value):
        return HistoricalRiverLevel(location_name=TEST_STATION, date=day, level_m=value)

    def test_unique_constraint_is_present(self):
        """The application guarantee is only real if the database enforces it."""
        with self.database_connection.engine.connect() as conn:
            present = conn.execute(text("""
                SELECT COUNT(*) FROM pg_constraint
                WHERE conrelid = 'flood_forecaster.historical_river_level'::regclass
                  AND conname = 'uq_historical_river_level_location_date'
            """)).scalar()
        self.assertEqual(
            present, 1,
            "uq_historical_river_level_location_date is missing. Apply "
            "sql/add_historical_river_level_unique_constraint.sql to this database."
        )

    def test_duplicate_within_one_batch_collapses(self):
        written = insert_river_data(
            [self._level(TEST_DATE, 5.0), self._level(TEST_DATE, 4.5)], self.config
        )
        self.assertEqual(written, 1, "Expected one row for one station-day")
        self.assertEqual([(TEST_DATE, 4.5)], [(r.date, r.level_m) for r in self._stored()])

    def test_repeated_ingestion_of_the_same_window_is_idempotent(self):
        batch = [
            self._level(TEST_DATE, 5.0),
            self._level(TEST_DATE + datetime.timedelta(days=1), 5.5),
        ]
        insert_river_data(batch, self.config)
        insert_river_data(batch, self.config)
        insert_river_data(batch, self.config)
        self.assertEqual(len(self._stored()), 2, "Repeated ingestion must not duplicate rows")

    def test_changed_value_updates_in_place(self):
        insert_river_data([self._level(TEST_DATE, 7.82)], self.config)
        insert_river_data([self._level(TEST_DATE, 6.82)], self.config)
        self.assertEqual([(TEST_DATE, 6.82)], [(r.date, r.level_m) for r in self._stored()])

    def test_null_level_does_not_erase_a_stored_reading(self):
        insert_river_data([self._level(TEST_DATE, 6.82)], self.config)
        insert_river_data([self._level(TEST_DATE, None)], self.config)
        self.assertEqual([(TEST_DATE, 6.82)], [(r.date, r.level_m) for r in self._stored()])

    def test_raw_duplicate_insert_is_rejected_by_the_database(self):
        """Any write path that bypasses insert_river_data must still be stopped."""
        insert_river_data([self._level(TEST_DATE, 5.0)], self.config)
        with self.assertRaises(IntegrityError):
            with self.database_connection.engine.connect() as conn:
                conn.execute(
                    insert(HistoricalRiverLevel).values(
                        location_name=TEST_STATION, date=TEST_DATE, level_m=9.9
                    )
                )
                conn.commit()
