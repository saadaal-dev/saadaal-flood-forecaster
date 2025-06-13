from src.flood_forecaster.data_model.river_level import PredictedRiverLevel
from src.flood_forecaster.utils.database_helper import DatabaseConnection
from src.flood_forecaster.utils.configuration import Config
from sqlalchemy import select
from datetime import datetime, timedelta
import pandas as pd

def get_risk_level(config: Config, date_begin: datetime) -> pd.DataFrame:
    print(f"Getting risk level for date: {date_begin}")
    stations_risk = (select(PredictedRiverLevel)
            .where(PredictedRiverLevel.date >= date_begin)
            .where(PredictedRiverLevel.risk_level.ilike('full')))
    database = DatabaseConnection(config)
    result_df = pd.read_sql(stations_risk, database.engine)
    
    # Create a new table with custom columns
    if result_df.empty:
        print("No matching risk levels found. Returning an empty DataFrame.")
        return pd.DataFrame(columns=[
            'station_id', 'river_station_name', 'flood_risk', 'water_level_m', 'predicted_flood_date'
        ])
    
    result_df['forecast_date'] = result_df['date'] + pd.to_timedelta(result_df['forecast_days'], unit='D')
    alert_table = result_df[['level_m', 'station_number', 'risk_level', 'forecast_date']]
    alert_table = alert_table.rename(columns={
        'location_name': 'Station',
        'risk_level': 'Flood risk',
        'level_m': 'Water level (m)',
        'forecast_date': 'Prediction date'
    })
    
    ### TO be removed
    # # Add river_station_name to the table
    # river_station_metadata = config.load_static_data_config()["river_stations_metadata_path"]
    # alert_table['river_station_name'] = alert_table['station_id'].apply(
    #     lambda station_id: get_station_name_from_csv(river_station_metadata, station_id)
    # )
    # alert_table = alert_table[[
    #     'station_id', 'river_station_name', 'flood_risk', 'water_level_m', 'predicted_flood_date'
    # ]]
    
    return alert_table

### This function is not needed anymore, to be removed
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
