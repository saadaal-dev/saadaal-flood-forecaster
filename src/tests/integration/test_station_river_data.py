import datetime
import unittest
from unittest.mock import MagicMock, patch

from flood_forecaster.data_ingestion.swalim import station_river_data


class TestStationRiverDataIntegration(unittest.TestCase):
    def test_identify_gaps_detects_missing_dates(self):
        session = MagicMock()
        query_chain = session.query.return_value.filter.return_value.order_by.return_value
        query_chain.all.return_value = [
            (datetime.date(2026, 1, 1),),
            (datetime.date(2026, 1, 3),),
        ]

        missing_dates = station_river_data.identify_gaps(
            session,
            location="Jowhar",
            first_date=datetime.date(2026, 1, 1),
            last_date=datetime.date(2026, 1, 3),
        )

        self.assertEqual(missing_dates, [datetime.date(2026, 1, 2)])
        session.query.assert_called_once()

    def test_fetch_data_from_public_schema_with_empty_dates_skips_query(self):
        session = MagicMock()

        data = station_river_data.fetch_data_from_public_schema(session, swalim_id=12, missing_dates=[])

        self.assertEqual(data, [])
        session.query.assert_not_called()

    @patch("flood_forecaster.data_ingestion.swalim.station_river_data.get_station_mapping")
    @patch("flood_forecaster.data_ingestion.swalim.station_river_data.DatabaseConnection")
    def test_fill_gaps_returns_false_when_station_mapping_missing(self, mock_db_connection, mock_get_station_mapping):
        mock_db_connection.return_value = MagicMock()
        mock_get_station_mapping.return_value = []
        config = MagicMock()

        result = station_river_data.fill_gaps_using_public_schema(config=config)

        self.assertFalse(result)
        mock_get_station_mapping.assert_called_once_with(config)

    @patch("flood_forecaster.data_ingestion.swalim.station_river_data.identify_gaps")
    @patch("flood_forecaster.data_ingestion.swalim.station_river_data.get_existing_data_range")
    @patch("flood_forecaster.data_ingestion.swalim.station_river_data.get_station_mapping")
    @patch("flood_forecaster.data_ingestion.swalim.station_river_data.Session")
    @patch("flood_forecaster.data_ingestion.swalim.station_river_data.DatabaseConnection")
    def test_fill_gaps_returns_true_when_no_gaps_found(
        self,
        mock_db_connection,
        mock_session_cls,
        mock_get_station_mapping,
        mock_get_existing_data_range,
        mock_identify_gaps,
    ):
        mock_conn = MagicMock()
        mock_db = MagicMock()
        mock_db.engine.connect.return_value.__enter__.return_value = mock_conn
        mock_db_connection.return_value = mock_db

        mock_session = MagicMock()
        mock_session_cls.return_value.__enter__.return_value = mock_session

        station = MagicMock(station_name="Jowhar", swalim_internal_id=301)
        mock_get_station_mapping.return_value = [station]
        # 3 expected days and 3 records means no gap.
        mock_get_existing_data_range.return_value = (
            datetime.date(2026, 1, 1),
            datetime.date(2026, 1, 3),
            3,
        )

        result = station_river_data.fill_gaps_using_public_schema(config=MagicMock())

        self.assertTrue(result)
        mock_identify_gaps.assert_not_called()

    @patch("flood_forecaster.data_ingestion.swalim.station_river_data.insert_missing_data")
    @patch("flood_forecaster.data_ingestion.swalim.station_river_data.fetch_data_from_public_schema")
    @patch("flood_forecaster.data_ingestion.swalim.station_river_data.identify_gaps")
    @patch("flood_forecaster.data_ingestion.swalim.station_river_data.get_existing_data_range")
    @patch("flood_forecaster.data_ingestion.swalim.station_river_data.get_station_mapping")
    @patch("flood_forecaster.data_ingestion.swalim.station_river_data.Session")
    @patch("flood_forecaster.data_ingestion.swalim.station_river_data.DatabaseConnection")
    def test_fill_gaps_returns_false_when_source_has_no_data(
        self,
        mock_db_connection,
        mock_session_cls,
        mock_get_station_mapping,
        mock_get_existing_data_range,
        mock_identify_gaps,
        mock_fetch_data,
        mock_insert_missing_data,
    ):
        mock_conn = MagicMock()
        mock_db = MagicMock()
        mock_db.engine.connect.return_value.__enter__.return_value = mock_conn
        mock_db_connection.return_value = mock_db

        mock_session = MagicMock()
        mock_session_cls.return_value.__enter__.return_value = mock_session

        missing_date = datetime.date(2026, 1, 2)
        station = MagicMock(station_name="Jowhar", swalim_internal_id=301)
        mock_get_station_mapping.return_value = [station]
        # Range includes 3 days but only 2 existing records, so one gap.
        mock_get_existing_data_range.return_value = (
            datetime.date(2026, 1, 1),
            datetime.date(2026, 1, 3),
            2,
        )
        mock_identify_gaps.return_value = [missing_date]
        mock_fetch_data.return_value = []

        result = station_river_data.fill_gaps_using_public_schema(config=MagicMock())

        self.assertFalse(result)
        mock_fetch_data.assert_called_once_with(mock_session, 301, [missing_date])
        mock_insert_missing_data.assert_not_called()


if __name__ == "__main__":
    unittest.main()
