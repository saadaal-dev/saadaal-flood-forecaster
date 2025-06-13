from src.flood_forecaster.data_model.river_level import PredictedRiverLevel
from src.flood_forecaster.utils.database_helper import DatabaseConnection
from src.flood_forecaster.utils.configuration import Config
from sqlalchemy import select, func
from datetime import datetime, timedelta
import pandas as pd
import logging
 
logger = logging.getLogger(__name__)
 
def get_df_by_date(db_client, date_begin: datetime, risk_level = 'full') -> pd.DataFrame:
    logger.debug(f"Getting risk level for date: {date_begin}")
    # only check the dd/mm/yyyy part of the date
    stations_risk = (
        select(PredictedRiverLevel)
        .where(func.date(PredictedRiverLevel.date) >= date_begin.date())
        .where(PredictedRiverLevel.risk_level.ilike(risk_level))
    )
    result_df = pd.read_sql(stations_risk, db_client.engine)
   
    # Create a new table with custom columns
    if result_df.empty:
        logger.info("No matching risk levels found. Returning an empty DataFrame.")
        return pd.DataFrame(columns=[
            'location_name', 'flood_risk', 'water_level_m', 'predicted_flood_date'
        ])
   
    result_df['forecast_date'] = result_df['date'] + pd.to_timedelta(result_df['forecast_days'], unit='D')
    result_df['forecast_date'] = result_df['date'].dt.date
    alert_table = result_df[['location_name', 'risk_level', 'level_m', 'forecast_date']]
    alert_table = alert_table.rename(columns={
        'location_name': 'Station',
        'risk_level': 'Flood risk',
        'level_m': 'Water level (m)',
        'forecast_date': 'Prediction date'
    })
 
    return alert_table
 
def get_latest_date(db_client, last_x_days = 1) -> datetime:
    """
    Reads postgres database and returns the latest date from the river level table.
    Returns:
        datetime: The latest date found in the river level table.
    """
    query = select(PredictedRiverLevel.date).order_by(PredictedRiverLevel.date.desc()).limit(last_x_days)
    with db_client.engine.connect() as conn:
        result = conn.execute(query).fetchone()
    if result:
        return result[0]
    else:
        raise ValueError("No dates found in the river level table.")

### This function is not supported now, It will be used in the future when we have a CSV file with station metadata.
def get_station_name_from_csv(csv_path: str, station_number: int) -> str:
    """
    Reads the CSV file and retrieves the station name corresponding to the given station number.
   
    Args:
        csv_path (str): Path to the CSV file containing station metadata.
        station_number (int): The station number to look up.
   
    Returns:
        str: The station name corresponding to the station number, or None if not found.
    """
    try:
        station_data = pd.read_csv(csv_path, index_col=False, dtype={'id': str, 'name': str})
        station_row = station_data.loc[station_data['id'] == station_number]
        if not station_row.empty:
            return station_row.iloc[0]['name']
        else:
            print(f"Station number {station_number} not found in the CSV file.")
            return None
    except Exception as e:
        print(f"Error reading CSV file: {e}")
        return None
    
    