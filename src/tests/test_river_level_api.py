from src.flood_forecaster.data_ingestion.swalim.river_level_api import fetch_latest_river_data
from src.flood_forecaster.utils.configuration import Config


def test_fetch_latest_river_data():
    # Mock configuration
    config = Config("src/tests/mock_config.ini")
    historical_river_levels = fetch_latest_river_data(config)
    # print(historical_river_levels)
    # assert len(historical_river_levels) > 0, "Expected to fetch historical river levels"
