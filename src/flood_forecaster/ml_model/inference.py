from src.flood_forecaster.ml_model.preprocess import preprocess_diff
from src.flood_forecaster.ml_model.registry import ModelManager


def infer_from_raw_data(model_manager: ModelManager, model_path, model_name, station_metadata, stations_df, weather_df, station_lag_days, weather_lag_days, forecast_days):
    """
    Infer a prediction from raw data.
    
    Args:
        model_manager: The model manager (responsible of providing a trained model and an inference function).
        station_metadata: The metadata for the station.
        stations_df: The DataFrame with the station data.
        weather_df: The DataFrame with the weather data.
        station_lag_days: The number of lag days for the station data.
        weather_lag_days: The number of lag days for the weather data.
        forecast_days: The number of forecast days.
    """
    df = preprocess_diff(
        station_metadata,
        stations_df, weather_df,
        station_lag_days=station_lag_days, weather_lag_days=weather_lag_days,
        forecast_days=forecast_days,
        infer=True,
    )
    
    model = model_manager.load(model_path, model_name)

    return model_manager.infer(model, df)
