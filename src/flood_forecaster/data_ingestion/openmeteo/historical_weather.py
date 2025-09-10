import datetime
from typing import Any, Dict, List, Optional

import pandas as pd
from openmeteo_sdk.WeatherApiResponse import WeatherApiResponse

from src.flood_forecaster import DatabaseConnection
from src.flood_forecaster.data_ingestion.openmeteo.common import (
    fetch_openmeteo_data,
    prepare_weather_locations,
    process_weather_responses,
    persist_weather_data,
    parse_daily_data,
)
from src.flood_forecaster.data_model.weather import HistoricalWeather
from src.flood_forecaster.utils.configuration import Config


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
        print("No historical weather data to fetch.")
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
