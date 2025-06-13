from datetime import datetime

from src.flood_forecaster.ml_model.preprocess import preprocess_diff
from src.flood_forecaster.ml_model.registry import ModelManager
from src.flood_forecaster.utils.database_helper import DatabaseConnection
from sqlalchemy import insert


DB_PREDICTED_RIVER_LEVEL = "predicted_river_level"


def infer_from_raw_data(model_manager: ModelManager, model_path, model_name, station_metadata, stations_df, weather_df, station_lag_days, weather_lag_days, forecast_days):
    """
    Infer a prediction from raw data.
    
    Args:
        model_manager: The model manager (responsible of providing a trained model and an inference function).
        model_path: The path to the directory containing the model files.
        model_name: The name of the model (used to identify a model in the model files).
        station_metadata: The metadata for the station.
        stations_df: The DataFrame with the station data.
        weather_df: The DataFrame with the weather data.
        station_lag_days: The number of lag days for the station data.
        weather_lag_days: The number of lag days for the weather data.
        forecast_days: The number of forecast days (used to identify a model in the model files).
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


def create_inference_insert_statement(
        location: str,
        model_name: str,
        forecast_days: int,
        date: datetime,
        level_m: float,
) -> insert:
    """
    Create an SQL insert statement to store inference results.
    
    Args:
        location: The location of the station.
        model_name: The name of the model used for inference.
        forecast_days: how many days ahead the prediction is made for (1=today).
        date: The timestamp of the inference.
        level_m: The predicted river level in meters.
    
    Returns:
        An SQLAlchemy insert statement.
    """
    return insert(DB_PREDICTED_RIVER_LEVEL).values(
        location=location,
        model_name=model_name,
        forecast_days=forecast_days,
        date=date,
        level_m=level_m
    )


def store_inference_result(db_connection: DatabaseConnection, location, model_name, forecast_days, date, level_m):
    """
    Store the inference result in the database.
    
    Args:
        location: The location of the station.
        model_name: The name of the model used for inference.
        forecast_days: how many days ahead the prediction is made for (1=today).
        date: The timestamp of the inference.
        level_m: The predicted river level in meters.
    """
    with db_connection.engine.connect() as conn:
        insert_stmt = create_inference_insert_statement(location, model_name, forecast_days, date, level_m)
        conn.execute(insert_stmt)
        conn.commit()
