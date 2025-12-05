from typing import Any, Dict, List

import pandas as pd
from openmeteo_sdk import WeatherApiResponse

from flood_forecaster.data_ingestion.openmeteo.common import (
    fetch_openmeteo_data,
    prepare_weather_locations,
    process_weather_responses,
    persist_weather_data,
    parse_daily_data
)
from flood_forecaster.data_model.weather import ForecastWeather
from flood_forecaster.utils.configuration import Config


def create_forecast_params(latitudes: List[float], longitudes: List[float]) -> Dict[str, Any]:
    """Create parameters for forecast API call"""
    return {
        "latitude": latitudes,
        "longitude": longitudes,
        "forecast_days": 16,
        "daily": [
            "temperature_2m_max",
            "temperature_2m_min",
            "precipitation_sum",
            "rain_sum",
            "precipitation_hours",
            "precipitation_probability_max",
            "wind_speed_10m_max",
        ],
        "timezone": "auto",
    }


def fetch_forecast(config: Config, openmeteo):
    """Fetch weather forecast for all locations defined in the config file."""
    location_labels, latitudes, longitudes = prepare_weather_locations(config)
    print(f"DEBUG: Fetching forecast for {len(location_labels)} locations")

    forecast_df = get_weather_forecast(location_labels, latitudes, longitudes, config, openmeteo)

    print(f"DEBUG: Received forecast DataFrame with {len(forecast_df)} rows")
    if len(forecast_df) > 0:
        print(f"DEBUG: Forecast date range: {forecast_df['date'].min()} to {forecast_df['date'].max()}")
        print(f"DEBUG: Locations in forecast: {forecast_df['location_name'].unique().tolist()}")
    else:
        print("WARNING: Forecast DataFrame is empty!")

    persist_weather_data(config, forecast_df, "forecast_weather_daily", ForecastWeather, clear_existing=False)
    return forecast_df


def get_weather_forecast(location_labels: List[str], latitudes: List[float],
                         longitudes: List[float], config: Config, openmeteo) -> pd.DataFrame:
    """Get weather forecast for the specified weather locations."""
    # Create API parameters and fetch data
    params = create_forecast_params(latitudes, longitudes)
    url = config.get_openmeteo_api_url()
    responses = fetch_openmeteo_data(openmeteo, url, params)

    # Process responses into DataFrame
    return process_weather_responses(responses, location_labels, parse_daily_forecast_response)


def parse_daily_forecast_response(response: WeatherApiResponse):
    """Parse forecast response to extract daily data including forecast-specific fields."""
    return parse_daily_data(response, forecast=True)
