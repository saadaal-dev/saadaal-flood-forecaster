from datetime import datetime

from sqlalchemy.dialects.postgresql import insert as pg_insert

from flood_forecaster.data_model.river_level import PredictedRiverLevel
from flood_forecaster.ml_model.preprocess import preprocess_diff
from flood_forecaster.ml_model.registry import ModelManager
from flood_forecaster.utils.database_helper import DatabaseConnection


def infer_from_raw_data(model_manager: ModelManager, model_path, model_name, station_metadata, stations_df, weather_df, station_lag_days, weather_lag_days, forecast_days):
    """
    Infer a prediction from raw data.
    
    Args:
        model_manager: The model manager (responsible for providing a trained model and an inference function).
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
):
    """
    Create an SQL UPSERT statement to store inference results.
    Uses INSERT ... ON CONFLICT UPDATE to update existing predictions instead of creating duplicates.

    Args:
        location: The location of the station.
        model_name: The name of the model used for inference.
        forecast_days: how many days ahead the prediction is made for (1=today).
        date: The datetime of the inference (will be converted to date only).
        level_m: The predicted river level in meters.
    
    Returns:
        An SQLAlchemy PostgreSQL insert statement with ON CONFLICT UPDATE.
    """
    # Convert datetime to date only (strip time component)
    date_only = date.date() if isinstance(date, datetime) else date

    # Create PostgreSQL-specific insert statement with UPSERT capability
    stmt = pg_insert(PredictedRiverLevel).values(
        location_name=location,
        ml_model_name=model_name,
        forecast_days=forecast_days,
        date=date_only,
        level_m=level_m
    )

    # On conflict (duplicate location_name, date, ml_model_name), update the existing row
    stmt = stmt.on_conflict_do_update(
        constraint='uq_prediction_location_date_model',
        set_={
            'level_m': stmt.excluded.level_m,
            'forecast_days': stmt.excluded.forecast_days,
            'updated_at': datetime.now()
        }
    )

    return stmt


def store_inference_result(db_connection: DatabaseConnection, location, model_name, forecast_days, date, level_m):
    """
    Store the inference result in the database.
    
    Args:
        :param db_connection:
        :param location: The location of the station.
        :param model_name: The name of the model used for inference.
        :param forecast_days: how many days ahead the prediction is made for (1=today).
        :param date: The timestamp of the inference.
        :param level_m: The predicted river level in meters.
    """
    with db_connection.engine.connect() as conn:
        insert_stmt = create_inference_insert_statement(location, model_name, forecast_days, date, level_m)
        conn.execute(insert_stmt)
        conn.commit()
        print(f"Inserted inference result for {location} with model {model_name} for {forecast_days} days ahead on {date} with level {level_m} m.")
