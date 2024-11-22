INPUT_DIR = 'data/raw/'

STATION_LAG_DAYS = [1, 3, 7, 14]
WEATHER_LAG_DAYS = (
    # lags
    [1, 3, 7, 14] +
     
    # forecasts
    [-1, -3, -7]
)


STATION_METADATA = {
    "belet_weyne": {
        "station": "belet_weyne", 
        "river": "shabelle",
        "stations": ["belet_weyne"],
        "weathers": ["ethiopia_tullu_dimtu", "ethiopia_fafen_haren", "ethiopia_fafen_gebredarre", "ethiopia_shabelle_gode"],
        "thresholds": {
            "moderate_risk": 6.5,
            "high_risk": 7.3,
            "bank_full": 8.3,
        }
    },
    "bulo_burti": {
        "station": "bulo_burti",
        "river": "shabelle",
        "stations": ["bulo_burti", "belet_weyne"],
        "weathers": ["ethiopia_tullu_dimtu", "ethiopia_fafen_haren", "ethiopia_fafen_gebredarre", "ethiopia_shabelle_gode"],
        "thresholds": {
            "moderate_risk": 6.5,
            "high_risk": 7.2,
            "bank_full": 8,
        }
    }
}

TRAIN_TEST_DATE_SPLIT = "2023-10-01"
TEST_DATE_END = None  # e.g., "2024" - used to zoom in on a time frame