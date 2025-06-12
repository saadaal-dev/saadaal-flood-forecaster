

import datetime
import pandas as pd
from flood_forecaster.data_ingestion.swalim.river_station import get_river_stations
from src.flood_forecaster.data_ingestion.openmeteo.district import District
from src.flood_forecaster.data_ingestion.openmeteo.historical_weather import get_daily_data_historical, get_historical_weather
from src.flood_forecaster.data_model.station import get_stations
from src.flood_forecaster.utils.configuration import Config

from openmeteo_sdk import WeatherApiResponse
from src.flood_forecaster.data_model.station import Station
from src.flood_forecaster.data_ingestion.openmeteo.district import District, get_districts

from src.flood_forecaster.data_ingestion.openmeteo.forecast_weather import get_daily_data_actual, get_hourly_data, get_weather_forecast

from functools import partial

def get_station_data(config: Config, get_data_function , get_forecast_function, manage_function):
    print(f"Reading {get_data_function} data...")
    data = get_data_function()
    latitudes = [s.latitude for s in data]
    longitudes = [s.longitude for s in data]

    
    responses = get_forecast_function(latitudes, longitudes, config)
    manage_function(config, data, responses)
    

def manage_weather_forecast(config, stations, responses):
    hourly_dfs = []
    daily_dfs = []
    data_path = config.get_store_base_path()
    for station, response in zip(stations, responses):
        print(f"Coordinates {response.Latitude()}°N {response.Longitude()}°E")
        print(f"Elevation {response.Elevation()} m asl")
        print(f"Timezone {response.Timezone()} {response.TimezoneAbbreviation()}")
        print(f"Timezone difference to GMT+0 {response.UtcOffsetSeconds()} s")

        hourly_df = get_hourly_data_frame(response, station)
        hourly_dfs.append(hourly_df)

        daily_df = get_daily_data_frame(response, station, get_daily_data_actual)
        daily_dfs.append(daily_df)

    hourly_combined = pd.concat(hourly_dfs, ignore_index=True)
    daily_combined = pd.concat(daily_dfs, ignore_index=True)

    if isinstance(station, Station):
        type = "station"
    else:
        type = "distinct"
    

    basename = data_path + f"forecast_station_weather_{type}"
    hourly_filename = "{}_hourly_{:%Y-%m-%d}.csv".format(
        basename, datetime.datetime.now()
    )
    daily_filename = "{}_daily_{:%Y-%m-%d}.csv".format(
        basename, datetime.datetime.now()
    )

    hourly_combined.to_csv(hourly_filename)
    daily_combined.to_csv(daily_filename)


def manage_historical_forecast(config, stations, responses):
    daily_dfs = []
    data_path = config.get_store_base_path()

    for station, response in zip(stations, responses):
        print(f"Coordinates {response.Latitude()}°N {response.Longitude()}°E")
        print(f"Elevation {response.Elevation()} m asl")
        print(f"Timezone {response.Timezone()} {response.TimezoneAbbreviation()}")
        print(f"Timezone difference to GMT+0 {response.UtcOffsetSeconds()} s")

        daily_df = get_daily_data_frame(response, station, get_daily_data_historical)
        daily_dfs.append(daily_df)

    daily_combined = pd.concat(daily_dfs, ignore_index=True)

    if isinstance(station, Station):
        type = "station"
    else:
        type = "distinct"

    daily_filename = data_path + f"{type}_" + "historical__weather_daily_{:%Y-%m-%d}.csv".format(
        datetime.datetime.now()
    )
    daily_combined.to_csv(daily_filename)


def get_daily_data_frame(response: WeatherApiResponse, station, function):
    # Get the daily data as a pandas DataFrame,
    daily_data = function(response) # We will apply the function based on the type of data we want (actual or historical)

    # Check if the station is an object type "Station" or "distinct"
    if isinstance(station, Station):
        daily_data["station_id"] = station.id
    else:
        daily_data["region"] = station.region
    
    daily_data["station_name"] = station.name
    daily_data["station_latitude"] = station.latitude
    daily_data["station_longitude"] = station.longitude

    df = pd.DataFrame(data=daily_data)
    print(f"Daily data for {station.name}")
    return df


def get_hourly_data_frame(response: WeatherApiResponse, station):
    # Get the daily data as a pandas DataFrame,
    daily_data = get_hourly_data(response)

    # Check if the station is an object type "Station" or "distinct"
    if isinstance(station, Station):
        daily_data["station_id"] = station.id
    else:
        daily_data["region"] = station.region
    
    daily_data["station_name"] = station.name
    daily_data["station_latitude"] = station.latitude
    daily_data["station_longitude"] = station.longitude

    df = pd.DataFrame(data=daily_data)
    print(f"Daily data for {station.name}")
    return df



config = Config("config/config.ini")

get_station_function = partial(get_river_stations, config.get_station_data__path())
get_distinct_function = partial(get_districts, config.get_district_data_path())

# Get DataForActualForecast
get_station_data(config, get_station_function, get_weather_forecast, manage_weather_forecast)
# Get DataForHistoricalForecast
get_station_data(config, get_station_function, get_historical_weather, manage_historical_forecast)



# Get DataForActualForecast
get_station_data(config, get_distinct_function, get_weather_forecast, manage_weather_forecast)
# Get DataForHistoricalForecast
get_station_data(config, get_distinct_function, get_historical_weather, manage_historical_forecast)

