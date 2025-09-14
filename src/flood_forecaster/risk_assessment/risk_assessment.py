from sqlalchemy import update

from flood_forecaster.data_model.river_level import PredictedRiverLevel
from flood_forecaster.data_model.river_station import get_river_stations_static, RiverStation
from flood_forecaster.utils.configuration import Config
from flood_forecaster.utils.database_helper import DatabaseConnection


def create_update_statement(river_station: RiverStation, risk_level: str) -> update:
    """
    Create an SQL update statement to set the risk level for a river station.
    
    :param river_station: The river station for which the risk level is being set.
    :param risk_level: The risk level to be set (e.g., 'low', 'moderate', 'high', 'full').
    :return: An SQLAlchemy update statement.
    """
    match risk_level:
        case "low":
            return update(PredictedRiverLevel)\
                .values(risk_level=risk_level)\
                .where(PredictedRiverLevel.location_name == str(river_station.name))\
                .where(PredictedRiverLevel.risk_level.is_(None))\
                .where(PredictedRiverLevel.level_m < river_station.moderate_threshold)
        case "moderate":
            return update(PredictedRiverLevel)\
                .values(risk_level=risk_level)\
                .where(PredictedRiverLevel.location_name == str(river_station.name))\
                .where(PredictedRiverLevel.risk_level.is_(None))\
                .where(PredictedRiverLevel.level_m >= river_station.moderate_threshold)\
                .where(PredictedRiverLevel.level_m < river_station.high_threshold)
        case "high":
            return update(PredictedRiverLevel)\
                .values(risk_level=risk_level)\
                .where(PredictedRiverLevel.location_name == str(river_station.name))\
                .where(PredictedRiverLevel.risk_level.is_(None))\
                .where(PredictedRiverLevel.level_m >= river_station.high_threshold)\
                .where(PredictedRiverLevel.level_m < river_station.full_threshold)
        case "full":
            return update(PredictedRiverLevel)\
                .values(risk_level=risk_level)\
                .where(PredictedRiverLevel.location_name == str(river_station.name))\
                .where(PredictedRiverLevel.risk_level.is_(None))\
                .where(PredictedRiverLevel.level_m >= river_station.full_threshold)
    return None


def execute_sql_update(river_station: RiverStation, risk_level: str, database_connection: DatabaseConnection):
    """
    Execute an SQL update statement to set the risk level for a river station.
    
    :param river_station: The river station for which the risk level is being set.
    :param risk_level: The risk level to be set (e.g., 'low', 'moderate', 'high', 'full').
    :param database_connection: Database connection object.
    """
    update_stmt = create_update_statement(river_station, risk_level)
    with database_connection.engine.connect() as conn:
        result = conn.execute(update_stmt)
        conn.commit()
        # print(f"Row(s) updated for station {river_station.id} with risk level {risk_level}: {result.rowcount}")


def main():
    """
    Main function to execute the risk assessment updates for river stations.
    """
    # Load configuration and database connection
    config = Config(config_file_path="config/config.ini")
    database_connection = DatabaseConnection(config)
    
    # Get river stations
    river_stations = get_river_stations_static(config)
    
    # Define thresholds
    thresholds = ["low", "moderate", "high", "full"]
    
    # Process each river station
    for river_station in river_stations:
        print(f"Processing station: {river_station.name}")
        print(f"Moderate threshold: {river_station.moderate_threshold}, High threshold: {river_station.high_threshold}, Full threshold: {river_station.full_threshold}")
        for threshold in thresholds:
            execute_sql_update(river_station, threshold, database_connection)


if __name__ == "__main__":
    main()
