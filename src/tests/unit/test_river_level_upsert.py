"""
Tests for the river-level write path (DATA-005).

`historical_river_level` had no uniqueness constraint on (location_name, date).
Duplicate suppression was an N+1 `SELECT` per candidate row followed by
`add_all()`, so repeated or concurrent ingestion could duplicate rows, and a
corrected upstream value was warned about and then discarded. The 2026-09-22
production snapshot held 962 excess rows across 962 duplicate pairs.

These tests run the real upsert against an in-memory SQLite database using the
production SQLAlchemy model, so the constraint declared on the model and the
ON CONFLICT clause are both exercised. The same approach is used by the RISK-006
alert regression tests.
"""
import unittest
from datetime import date, datetime
from types import SimpleNamespace
from unittest.mock import patch

import pandas as pd
from sqlalchemy import create_engine, event, func, select
from sqlalchemy.pool import StaticPool

from flood_forecaster.data_ingestion.swalim.river_level_api import (
    _collapse_duplicate_levels,
    _normalize_reading_date,
    insert_river_data,
)
from flood_forecaster.data_model.river_level import HistoricalRiverLevel

STATION = "Jowhar"


def _make_engine():
    """In-memory SQLite engine with the `flood_forecaster` schema attached."""
    engine = create_engine("sqlite://", poolclass=StaticPool)

    @event.listens_for(engine, "connect")
    def _attach_schema(dbapi_connection, _connection_record):
        dbapi_connection.execute("ATTACH DATABASE ':memory:' AS flood_forecaster")

    HistoricalRiverLevel.__table__.create(engine)
    return engine


def _level(location, day, value):
    return HistoricalRiverLevel(location_name=location, date=day, level_m=value)


class TestNormalizeReadingDate(unittest.TestCase):
    """
    `date`, `datetime` and `pd.Timestamp` never compare or hash equal to one
    another. `_get_new_river_levels()` produces Timestamps while other callers
    produce plain dates, so without normalization the same day arrives twice and
    only collides once it reaches the database.
    """

    def test_accepts_date(self):
        self.assertEqual(_normalize_reading_date(date(2026, 5, 12)), date(2026, 5, 12))

    def test_accepts_datetime(self):
        self.assertEqual(
            _normalize_reading_date(datetime(2026, 5, 12, 23, 59)), date(2026, 5, 12)
        )

    def test_accepts_pandas_timestamp(self):
        self.assertEqual(
            _normalize_reading_date(pd.Timestamp("2026-05-12 07:00:00")), date(2026, 5, 12)
        )

    def test_accepts_string(self):
        self.assertEqual(_normalize_reading_date("2026-05-12"), date(2026, 5, 12))

    def test_none_and_unparsable_become_none(self):
        self.assertIsNone(_normalize_reading_date(None))
        self.assertIsNone(_normalize_reading_date("not a date"))

    def test_mixed_representations_of_one_day_collapse_to_one_row(self):
        rows = _collapse_duplicate_levels([
            _level(STATION, date(2026, 5, 12), 4.0),
            _level(STATION, pd.Timestamp("2026-05-12"), 4.5),
            _level(STATION, datetime(2026, 5, 12, 6, 0), 5.0),
        ])
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["date"], date(2026, 5, 12))
        self.assertEqual(rows[0]["level_m"], 5.0, "last occurrence should win")


class TestCollapseDuplicateLevels(unittest.TestCase):
    """
    ON CONFLICT DO UPDATE raises "cannot affect row a second time" when one
    statement carries two rows with the same conflict key, so the batch must be
    collapsed first.
    """

    def test_keeps_last_occurrence(self):
        rows = _collapse_duplicate_levels([
            _level(STATION, date(2026, 5, 12), 4.88),
            _level(STATION, date(2026, 5, 12), 3.30),
        ])
        self.assertEqual([r["level_m"] for r in rows], [3.30])


class TestCollapseKeepsLatestAvailableMeasurement(unittest.TestCase):
    """
    A NULL must not displace a reading seen earlier in the same batch.

    NULL means the reading was unavailable. It is not a measurement and it is not a
    retraction, so plain "last wins" silently destroyed valid data before it ever
    reached the database, defeating the NULL guard in `_river_level_upsert()` one
    layer below. Raised in PR review on the DATA-005 branch.
    """

    DAY = date(2026, 5, 12)

    def _collapse(self, values):
        rows = _collapse_duplicate_levels([_level(STATION, self.DAY, v) for v in values])
        self.assertEqual(len(rows), 1, "one station-day must collapse to one row")
        return rows[0]["level_m"]

    def test_null_after_a_reading_keeps_the_reading(self):
        self.assertEqual(self._collapse([4.70, None]), 4.70)

    def test_null_after_two_readings_keeps_the_later_reading(self):
        self.assertEqual(self._collapse([4.70, 4.80, None]), 4.80)

    def test_reading_after_a_null_replaces_it(self):
        self.assertEqual(self._collapse([None, 4.70]), 4.70)

    def test_latest_reading_wins_not_the_largest(self):
        """Recency, not magnitude: 4.70 arrived after 4.80."""
        self.assertEqual(self._collapse([4.80, 4.70, None]), 4.70)

    def test_all_null_stays_null(self):
        """Nothing was ever reported, so the placeholder is preserved (DATA-010)."""
        self.assertIsNone(self._collapse([None, None]))

    def test_trailing_nulls_do_not_accumulate_damage(self):
        self.assertEqual(self._collapse([4.70, None, None, None]), 4.70)

    def test_reading_recovers_after_interleaved_nulls(self):
        self.assertEqual(self._collapse([4.70, None, 4.90, None]), 4.90)

    def test_nan_is_treated_as_null_not_as_a_measurement(self):
        """`pd.to_numeric(errors="coerce")` yields NaN, which must behave like NULL."""
        self.assertEqual(self._collapse([4.70, float("nan")]), 4.70)

    def test_other_station_days_are_unaffected(self):
        rows = _collapse_duplicate_levels([
            _level("Jowhar", self.DAY, 4.70),
            _level("Jowhar", self.DAY, None),
            _level("Luuq", self.DAY, None),
        ])
        self.assertEqual(
            {(r["location_name"], r["level_m"]) for r in rows},
            {("Jowhar", 4.70), ("Luuq", None)},
        )

    def test_ignored_null_keeps_its_original_batch_position(self):
        rows = _collapse_duplicate_levels([
            _level(STATION, date(2026, 5, 11), 1.0),
            _level(STATION, date(2026, 5, 12), 2.0),
            _level(STATION, date(2026, 5, 11), None),
        ])
        self.assertEqual(
            [(r["date"], r["level_m"]) for r in rows],
            [(date(2026, 5, 11), 1.0), (date(2026, 5, 12), 2.0)],
        )

    def test_distinct_stations_on_the_same_day_are_both_kept(self):
        rows = _collapse_duplicate_levels([
            _level("Jowhar", date(2026, 5, 12), 4.88),
            _level("Luuq", date(2026, 5, 12), 2.34),
        ])
        self.assertEqual(len(rows), 2)

    def test_preserves_input_order(self):
        rows = _collapse_duplicate_levels([
            _level(STATION, date(2026, 5, 11), 1.0),
            _level(STATION, date(2026, 5, 13), 3.0),
            _level(STATION, date(2026, 5, 12), 2.0),
        ])
        self.assertEqual(
            [r["date"] for r in rows],
            [date(2026, 5, 11), date(2026, 5, 13), date(2026, 5, 12)],
        )

    def test_drops_rows_that_cannot_be_keyed(self):
        rows = _collapse_duplicate_levels([
            _level(None, date(2026, 5, 12), 4.0),
            _level(STATION, None, 4.0),
            _level(STATION, date(2026, 5, 12), 4.0),
        ])
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["location_name"], STATION)

    def test_nan_level_becomes_none(self):
        rows = _collapse_duplicate_levels([_level(STATION, date(2026, 5, 12), float("nan"))])
        self.assertIsNone(rows[0]["level_m"])

    def test_empty_batch(self):
        self.assertEqual(_collapse_duplicate_levels([]), [])


class TestInsertRiverData(unittest.TestCase):
    """End-to-end upsert behaviour against a database that enforces the constraint."""

    def setUp(self):
        self.engine = _make_engine()
        patcher = patch(
            "flood_forecaster.data_ingestion.swalim.river_level_api.DatabaseConnection",
            return_value=SimpleNamespace(engine=self.engine),
        )
        patcher.start()
        self.addCleanup(patcher.stop)
        self.addCleanup(self.engine.dispose)
        self.config = SimpleNamespace()

    def _stored(self):
        with self.engine.begin() as conn:
            return conn.execute(
                select(
                    HistoricalRiverLevel.location_name,
                    HistoricalRiverLevel.date,
                    HistoricalRiverLevel.level_m,
                ).order_by(HistoricalRiverLevel.location_name, HistoricalRiverLevel.date)
            ).all()

    def _row_count(self):
        with self.engine.begin() as conn:
            return conn.execute(
                select(func.count()).select_from(HistoricalRiverLevel.__table__)
            ).scalar()

    def test_constraint_is_declared_on_the_model(self):
        """
        The constraint has to exist on the model, not only in the SQL migration, so
        that `index_elements` has a target and a bootstrap-from-model matches
        production.
        """
        unique = {
            tuple(sorted(c.name for c in constraint.columns))
            for constraint in HistoricalRiverLevel.__table__.constraints
            if constraint.__class__.__name__ == "UniqueConstraint"
        }
        self.assertIn(("date", "location_name"), unique)

    def test_inserts_new_rows(self):
        written = insert_river_data(
            [
                _level(STATION, date(2026, 5, 11), 4.88),
                _level(STATION, date(2026, 5, 12), 4.70),
            ],
            self.config,
        )
        self.assertEqual(written, 2)
        self.assertEqual(self._row_count(), 2)

    def test_repeated_ingestion_of_the_same_window_is_idempotent(self):
        """
        The Jowhar outage was repaired by re-running ingestion over an overlapping
        window. That must not multiply rows.
        """
        batch = [
            _level(STATION, date(2026, 5, 11), 4.88),
            _level(STATION, date(2026, 5, 12), 4.70),
        ]
        insert_river_data(batch, self.config)
        insert_river_data(batch, self.config)
        insert_river_data(batch, self.config)

        self.assertEqual(self._row_count(), 2)
        self.assertEqual(
            self._stored(),
            [
                (STATION, date(2026, 5, 11), 4.88),
                (STATION, date(2026, 5, 12), 4.70),
            ],
        )

    def test_duplicate_within_a_single_batch_does_not_raise(self):
        """
        Two rows for the same station and day in one call previously produced two
        database rows. Now the batch is collapsed and the last value is stored.
        """
        written = insert_river_data(
            [
                _level(STATION, date(2026, 5, 12), 4.88),
                _level(STATION, date(2026, 5, 12), 3.30),
            ],
            self.config,
        )
        self.assertEqual(written, 1)
        self.assertEqual(self._stored(), [(STATION, date(2026, 5, 12), 3.30)])

    def test_changed_upstream_value_updates_in_place(self):
        """
        A differing upstream reading is a correction, not something to discard. All
        nine conflicting pairs in the production snapshot were arbitrated against
        public.station_river_data and the later value was right every time.
        """
        insert_river_data([_level("Belet Weyne", date(2024, 8, 18), 7.82)], self.config)
        insert_river_data([_level("Belet Weyne", date(2024, 8, 18), 6.82)], self.config)

        self.assertEqual(self._row_count(), 1)
        self.assertEqual(self._stored(), [("Belet Weyne", date(2024, 8, 18), 6.82)])

    def test_null_incoming_level_does_not_erase_a_stored_reading(self):
        """
        NULL means "no usable reading" throughout the gap logic. Letting it overwrite
        a real value would manufacture a gap (DATA-010).
        """
        insert_river_data([_level(STATION, date(2026, 5, 12), 4.70)], self.config)
        insert_river_data([_level(STATION, date(2026, 5, 12), None)], self.config)

        self.assertEqual(self._stored(), [(STATION, date(2026, 5, 12), 4.70)])

    def test_null_level_can_still_be_inserted_for_a_new_date(self):
        insert_river_data([_level(STATION, date(2026, 5, 12), None)], self.config)
        self.assertEqual(self._stored(), [(STATION, date(2026, 5, 12), None)])

    def test_reading_and_null_in_one_batch_stores_the_reading(self):
        """
        End to end for the PR review case: a batch carrying both a reading and a
        NULL for one station-day must store the reading, not a placeholder.
        """
        written = insert_river_data(
            [
                _level(STATION, date(2026, 5, 12), 4.70),
                _level(STATION, date(2026, 5, 12), None),
            ],
            self.config,
        )
        self.assertEqual(written, 1)
        self.assertEqual(self._stored(), [(STATION, date(2026, 5, 12), 4.70)])

    def test_null_in_a_later_batch_also_cannot_erase_the_stored_reading(self):
        """The batch-level and database-level guards must agree."""
        insert_river_data([_level(STATION, date(2026, 5, 12), 4.70)], self.config)
        insert_river_data(
            [
                _level(STATION, date(2026, 5, 12), None),
                _level(STATION, date(2026, 5, 13), None),
            ],
            self.config,
        )
        self.assertEqual(
            self._stored(),
            [(STATION, date(2026, 5, 12), 4.70), (STATION, date(2026, 5, 13), None)],
        )

    def test_mixed_new_and_existing_dates_in_one_batch(self):
        insert_river_data([_level(STATION, date(2026, 5, 11), 4.88)], self.config)
        written = insert_river_data(
            [
                _level(STATION, date(2026, 5, 11), 4.90),  # update
                _level(STATION, date(2026, 5, 12), 4.70),  # insert
            ],
            self.config,
        )
        self.assertEqual(written, 2)
        self.assertEqual(
            self._stored(),
            [
                (STATION, date(2026, 5, 11), 4.90),
                (STATION, date(2026, 5, 12), 4.70),
            ],
        )

    def test_empty_batch_writes_nothing(self):
        self.assertEqual(insert_river_data([], self.config), 0)
        self.assertEqual(self._row_count(), 0)

    def test_batch_of_only_unkeyable_rows_writes_nothing(self):
        self.assertEqual(
            insert_river_data([_level(STATION, None, 4.0)], self.config), 0
        )
        self.assertEqual(self._row_count(), 0)

    def test_avoid_duplicates_false_no_longer_duplicates(self):
        """
        The flag is retained for compatibility but ignored: the database now refuses
        duplicates, so the old "insert everything" path cannot be honoured.
        """
        insert_river_data([_level(STATION, date(2026, 5, 12), 4.70)], self.config)
        insert_river_data(
            [_level(STATION, date(2026, 5, 12), 4.70)], self.config, avoid_duplicates=False
        )
        self.assertEqual(self._row_count(), 1)


if __name__ == "__main__":
    unittest.main()
