import datetime
from typing import Any, Dict, List, Optional

import pandas as pd
from openmeteo_sdk import WeatherApiResponse
from sqlalchemy.orm import Session
from sqlalchemy.sql import func

from flood_forecaster import DatabaseConnection
from flood_forecaster.data_ingestion.openmeteo.common import (
    fetch_openmeteo_data,
    prepare_weather_locations,
    process_weather_responses,
    persist_weather_data,
    parse_daily_data,
)
from flood_forecaster.data_model.weather import HistoricalWeather
from flood_forecaster.utils.configuration import Config


def remove_duplicates_historical_weather_from_db(config: Config, dry_run: bool = True):
    """
    Remove duplicate historical weather entries from the database based on date and location.
    This function is used to ensure that the historical weather data in the database is unique.
    It checks for duplicate entries and removes them if found.
    :param config: Configuration object containing settings.
    :param dry_run: If True, only prints the duplicates without deleting them.
    """
    database_connection = DatabaseConnection(config)
    with database_connection.engine.connect() as conn:
        with Session(bind=conn) as session:
            # Get all historical weather entries where the key has more than one entry (key: location_name and date columns only)
            duplicates = session.query(
                HistoricalWeather.location_name,
                func.date(HistoricalWeather.date).label("date"),
            ).group_by(
                HistoricalWeather.location_name,
                func.date(HistoricalWeather.date),
            ).having(
                func.count(HistoricalWeather.id) > 1
            ).order_by(
                HistoricalWeather.location_name,
                func.date(HistoricalWeather.date)
            ).all()

            if not duplicates:
                print("No duplicate historical weather entries found.")
                return
            
            print(f"Found {len(duplicates)} duplicate historical weather entries:")
            for duplicate in duplicates:
                print(f" - Location: {duplicate.location_name}, Date: {duplicate.date}")
            
            if not dry_run:
                # Bulk delete duplicates
                for duplicate in duplicates:
                    # get the id of latest entry (max date) for this location and date
                    latest_entry = session.query(HistoricalWeather).filter(
                        HistoricalWeather.location_name == duplicate.location_name,
                        func.date(HistoricalWeather.date) == duplicate.date
                    ).order_by(HistoricalWeather.date.desc()).first()

                    if not latest_entry:
                        print(f"WARNING: No latest entry found for {duplicate.location_name} on {duplicate.date}, skipping... (this should never happen)")
                        continue

                    # delete all entries except one (keep latest entry)
                    session.query(HistoricalWeather).filter(
                        HistoricalWeather.location_name == duplicate.location_name,
                        func.date(HistoricalWeather.date) == duplicate.date,
                        HistoricalWeather.id != latest_entry.id
                    ).delete(synchronize_session=False)
                session.commit()
                print("Duplicate historical weather entries removed from the database.")


def create_historical_params(start_date: datetime.datetime, end_date: datetime.datetime,
                             latitudes: List[float], longitudes: List[float]) -> Dict[str, Any]:
    """Create parameters for historical API call"""
    return {
        "latitude": latitudes,
        "longitude": longitudes,
        "start_date": start_date.strftime("%Y-%m-%d"),
        # FIXME: having issue resolving the historical data for yesterday... (API returns empty values)
        "end_date": end_date.strftime("%Y-%m-%d"),
        "daily": [
            "temperature_2m_max",
            "temperature_2m_min",
            "precipitation_sum",
            "rain_sum",
            "precipitation_hours",
        ],
        "timezone": "auto",
    }


def fetch_historical(config: Config, openmeteo):
    """Fetch historical weather data for all locations defined in the config file."""
    # Get the latest date from the HistoricalWeather table
    print("Fetching the latest date from the database...")
    conn = DatabaseConnection(config)

    max_date = conn.get_max_date(HistoricalWeather)
    if max_date:
        print(f"Latest historical weather date in the database: {max_date.strftime('%Y-%m-%d')}")

    location_labels, latitudes, longitudes = prepare_weather_locations(config)
    historical_df = get_historical_weather(location_labels, latitudes, longitudes, config, openmeteo, max_date)

    if historical_df is None:
        print("No historical weather data fetched.")
        return None

    persist_weather_data(config, historical_df, "historical_weather_daily", HistoricalWeather)
    return historical_df


def get_historical_weather(location_labels: List[str],
                           latitudes: List[float], longitudes: List[float],
                           config: Config, openmeteo,
                           max_date: Optional[datetime.datetime] = None) -> Optional[pd.DataFrame]:
    """Get historical weather data for the specified locations and date range."""
    # Use yesterday as the end date to avoid fetching today's data
    end_date = datetime.datetime.now() - datetime.timedelta(days=1)

    if max_date is not None:
        # Start from the day after the latest date in the database
        start_date = max_date + datetime.timedelta(days=1)   # FIXME this creates duplicates
    else:
        # Default to 10 years of historical data
        start_date = end_date - datetime.timedelta(days=10 * 365)

    print(f"DEBUG: max_date: {max_date}, start_date: {start_date}, end_date: {end_date}")

    if start_date > end_date:
        print("You have the most updated data in the historical weather :)")
        return None
    
    print("Fetching historical weather data from Open-Meteo API...")
    print(f"Start date: {start_date.strftime('%Y-%m-%d')}, End date: {end_date.strftime('%Y-%m-%d')}")
    
    # Create API parameters and fetch data
    params = create_historical_params(start_date, end_date, latitudes, longitudes)
    url = config.get_openmeteo_api_archive_url()
    responses = fetch_openmeteo_data(openmeteo, url, params)

    # Process responses into DataFrame
    return process_weather_responses(responses, location_labels, parse_daily_historical_response)


def parse_daily_historical_response(response: WeatherApiResponse):
    """Parse historical response to extract daily data."""
    return parse_daily_data(response, forecast=False)
