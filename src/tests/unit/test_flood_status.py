"""
Regression tests for the alert query path (RISK-006).

`PredictedRiverLevel.date` is a DATE column, so `DatabaseConnection.get_max_date()`
returns a `datetime.date`. A previous implementation of `get_df_by_date()` called
`date_begin.date()` on that value and then used the `.dt` accessor on the resulting
object-dtype column, which crashed `flood-cli alert` before any alert could be sent:

    AttributeError: 'datetime.date' object has no attribute 'date'

These tests run the real query against an in-memory SQLite database using the
production SQLAlchemy model, so the DATE column semantics are exercised end to end.
"""

import unittest
from datetime import date, datetime
from types import SimpleNamespace

from sqlalchemy import create_engine, event, insert
from sqlalchemy.pool import StaticPool

from flood_forecaster.alert_module.flood_status import get_df_by_date
from flood_forecaster.data_model.river_level import PredictedRiverLevel

REFERENCE_DATE = date(2026, 9, 23)


def _make_engine():
    """In-memory SQLite engine with the `flood_forecaster` schema attached."""
    engine = create_engine("sqlite://", poolclass=StaticPool)

    @event.listens_for(engine, "connect")
    def _attach_schema(dbapi_connection, _connection_record):
        dbapi_connection.execute("ATTACH DATABASE ':memory:' AS flood_forecaster")

    PredictedRiverLevel.__table__.create(engine)
    return engine


class TestGetDfByDate(unittest.TestCase):
    def setUp(self):
        self.engine = _make_engine()
        self.db_client = SimpleNamespace(engine=self.engine)

    def tearDown(self):
        self.engine.dispose()

    def _insert(self, rows):
        with self.engine.begin() as conn:
            conn.execute(insert(PredictedRiverLevel), rows)

    @staticmethod
    def _row(location_name, row_date, risk_level="full", level_m=7.5, forecast_days=3):
        return {
            "location_name": location_name,
            "date": row_date,
            "level_m": level_m,
            "station_number": "1",
            "ml_model_name": "test-model",
            "forecast_days": forecast_days,
            "risk_level": risk_level,
            "created_at": datetime(2026, 9, 23, 12, 0, 0),
            "updated_at": datetime(2026, 9, 23, 12, 0, 0),
        }

    def test_accepts_date_as_returned_by_get_max_date(self):
        """A plain datetime.date must not raise (the RISK-006 crash)."""
        self._insert([self._row("Luuq", REFERENCE_DATE)])

        result = get_df_by_date(self.db_client, REFERENCE_DATE, risk_level="full")

        self.assertEqual(len(result), 1)
        self.assertEqual(result.iloc[0]["Station"], "Luuq")
        self.assertEqual(result.iloc[0]["Flood risk"], "full")
        self.assertEqual(result.iloc[0]["Water level (m)"], 7.5)
        self.assertEqual(
            list(result.columns),
            ["Station", "Flood risk", "Water level (m)", "Prediction date"],
        )

    def test_prediction_date_is_a_date_value(self):
        """Guards the `.dt` accessor use on the object-dtype DATE column."""
        self._insert([self._row("Luuq", REFERENCE_DATE)])

        result = get_df_by_date(self.db_client, REFERENCE_DATE, risk_level="full")

        self.assertEqual(result.iloc[0]["Prediction date"], REFERENCE_DATE)

    def test_accepts_datetime(self):
        """Datetime callers keep working; only the calendar day is compared."""
        self._insert([self._row("Luuq", REFERENCE_DATE)])

        result = get_df_by_date(
            self.db_client, datetime(2026, 9, 23, 18, 30), risk_level="full"
        )

        self.assertEqual(len(result), 1)
        self.assertEqual(result.iloc[0]["Station"], "Luuq")

    def test_filters_earlier_dates_and_other_risk_levels(self):
        self._insert([
            self._row("Luuq", REFERENCE_DATE, risk_level="full"),
            self._row("Bulo Burti", date(2026, 9, 24), risk_level="full"),
            self._row("Jowhar", date(2026, 9, 20), risk_level="full"),
            self._row("Belet Weyne", REFERENCE_DATE, risk_level="moderate"),
        ])

        result = get_df_by_date(self.db_client, REFERENCE_DATE, risk_level="full")

        self.assertEqual(
            sorted(result["Station"].tolist()), ["Bulo Burti", "Luuq"]
        )

    def test_risk_level_match_is_case_insensitive(self):
        self._insert([self._row("Luuq", REFERENCE_DATE, risk_level="FULL")])

        result = get_df_by_date(self.db_client, REFERENCE_DATE, risk_level="full")

        self.assertEqual(len(result), 1)

    def test_no_matching_rows_returns_empty_dataframe(self):
        self._insert([self._row("Jowhar", date(2026, 9, 20), risk_level="full")])

        result = get_df_by_date(self.db_client, REFERENCE_DATE, risk_level="full")

        self.assertTrue(result.empty)

    def test_empty_table_returns_empty_dataframe(self):
        result = get_df_by_date(self.db_client, REFERENCE_DATE, risk_level="full")

        self.assertTrue(result.empty)


if __name__ == "__main__":
    unittest.main()
