

import datetime
import pandas as pd
from flood_forecaster.data_ingestion.openmeteo.weather_location import get_weather_locations
from flood_forecaster.data_model.weather import ForecastWeather, HistoricalWeather
from flood_forecaster.utils.database_helper import DatabaseConnection
from src.flood_forecaster.data_ingestion.openmeteo.district import District
from src.flood_forecaster.data_ingestion.openmeteo.historical_weather import get_daily_data_historical, get_historical_weather
from src.flood_forecaster.utils.configuration import Config
from sqlalchemy.orm import Session

from openmeteo_sdk import WeatherApiResponse
from src.flood_forecaster.data_model.station import Station

from src.flood_forecaster.data_ingestion.openmeteo.forecast_weather import get_daily_data_actual, get_weather_forecast

from functools import partial

def get_station_data(config: Config, get_data_function , get_forecast_function, manage_function):
    print(f"Reading {get_data_function} data...")
    data = get_data_function()
    latitudes = [s.latitude for s in data]
    longitudes = [s.longitude for s in data]

    
    responses = get_forecast_function(latitudes, longitudes, config)
    manage_function(config, data, responses)
    

def manage_weather_forecast(config, stations, responses):
    daily_dfs = []
    data_path = config.get_store_base_path()
    for station, response in zip(stations, responses):
        print(f"The Label is {station.label}")
        print(f"Coordinates {response.Latitude()}°N {response.Longitude()}°E")
        print(f"Elevation {response.Elevation()} m asl")
        print(f"Timezone {response.Timezone()} {response.TimezoneAbbreviation()}")
        print(f"Timezone difference to GMT+0 {response.UtcOffsetSeconds()} s")

        daily_df = append_station_information(response, station, get_daily_data_actual)
        daily_dfs.append(daily_df)

    daily_combined = pd.concat(daily_dfs, ignore_index=True)

    if isinstance(station, Station):
        type = "station"
    else:
        type = "distinct"
    

    basename = data_path + f"forecast_station_weather_{type}"
    daily_filename = "{}_daily_{:%Y-%m-%d}.csv".format(
        basename, datetime.datetime.now()
    )
    # add the logic to write to database

    if config.use_database_weather().lower() == "true":
            # Convert each row in daily_combined DataFrame to ForecastWeather objects
            daily_combined = daily_combined.drop(columns=["forecast_latitude"])
            daily_combined = daily_combined.drop(columns=["forecast_longitude"])
            forecast_weather_objects = ForecastWeather.from_dataframe(daily_combined)

            with database_connection.engine.connect() as conn:
                with Session(bind=conn) as session:
                    session.add_all(forecast_weather_objects)
                    session.commit()
                    print(f"Inserted {len(forecast_weather_objects)} river levels into the database.")
            
    else:
        daily_combined.to_csv(daily_filename, index=False)


def manage_historical_forecast(config, stations, responses):
    daily_dfs = []
    data_path = config.get_store_base_path()

    for station, response in zip(stations, responses):
        print(f"Coordinates {response.Latitude()}°N {response.Longitude()}°E")
        print(f"Elevation {response.Elevation()} m asl")
        print(f"Timezone {response.Timezone()} {response.TimezoneAbbreviation()}")
        print(f"Timezone difference to GMT+0 {response.UtcOffsetSeconds()} s")

        daily_df = append_station_information(response, station, get_daily_data_historical)
        daily_dfs.append(daily_df)

    daily_combined = pd.concat(daily_dfs, ignore_index=True)

    if isinstance(station, Station):
        type = "station"
    else:
        type = "distinct"

    daily_filename = data_path + "historical__" + f"{type}_" +"weather_daily_{:%Y-%m-%d}.csv".format(
        datetime.datetime.now()
    )

    if config.use_database_weather().lower() == "true":
            # Convert each row in daily_combined DataFrame to ForecastWeather objects
            daily_combined = daily_combined.drop(columns=["forecast_latitude"])
            daily_combined = daily_combined.drop(columns=["forecast_longitude"])
            forecast_weather_objects = HistoricalWeather.from_dataframe(daily_combined)

            with database_connection.engine.connect() as conn:
                with Session(bind=conn) as session:
                    session.add_all(forecast_weather_objects)
                    session.commit()
                    print(f"Inserted {len(forecast_weather_objects)} river levels into the database.")
    else:
        daily_combined.to_csv(daily_filename)



def append_station_information(response: WeatherApiResponse, station, function):
    # Get the daily data as a pandas DataFrame,
    daily_data = function(response) # We will apply the function based on the type of data we want (actual or historical)

    # Check if the station is an object type "Station" or "distinct"

    daily_data["location_name"] = station.label
    
    df = pd.DataFrame(data=daily_data)
    print(f"Daily data for {station.label}")
    return df


config = Config(config_file_path="config/config.ini")
database_connection = DatabaseConnection(config)

#Empty the table for the forecast weather data
database_connection.empty_table(ForecastWeather)       
print("Emptying the table for the forecast weather data")

get_station_function = partial(get_weather_locations, config.get_station_data__path())

# get the mag date from the db 
max_date = database_connection.get_max_date(HistoricalWeather)

print(f"Max date in the database: {max_date}")

get_station_data(
    config,
    get_station_function,
    partial(get_historical_weather, max_date=max_date),
    manage_historical_forecast
)
