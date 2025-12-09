from datetime import datetime

import pandas as pd
from sqlalchemy import select, func

from flood_forecaster.data_model.river_level import PredictedRiverLevel
from flood_forecaster.utils.logging_config import get_logger

logger = get_logger(__name__)


def get_df_by_date(db_client, date_begin: datetime, risk_level='full') -> pd.DataFrame:
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
