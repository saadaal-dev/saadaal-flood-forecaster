from typing import List

import pandas as pd
from openmeteo_sdk import WeatherApiResponse

from flood_forecaster.data_ingestion.openmeteo.common import (
    fetch_openmeteo_data,
    prepare_weather_locations,
    process_weather_responses,
    persist_weather_data,
    create_forecast_params,
    parse_daily_weather
)
from flood_forecaster.data_model.weather import ForecastWeather
from flood_forecaster.utils.configuration import Config


def fetch_forecast(config: Config, openmeteo):
    """Fetch weather forecast for all locations defined in the config file."""
    location_labels, latitudes, longitudes = prepare_weather_locations(config)
    forecast_df = get_weather_forecast(location_labels, latitudes, longitudes, config, openmeteo)

    persist_weather_data(config, forecast_df, "forecast_weather_daily", ForecastWeather, clear_existing=True)
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
    daily = response.Daily()
    daily_data = parse_daily_weather(daily)

    # Add forecast-specific fields
    daily_precipitation_probability_max = daily.Variables(5).ValuesAsNumpy()
    daily_wind_speed_10m_max = daily.Variables(6).ValuesAsNumpy()
    daily_data["precipitation_probability_max"] = daily_precipitation_probability_max
    daily_data["wind_speed_10m_max"] = daily_wind_speed_10m_max

    return daily_data
