import openmeteo_requests
from openmeteo_sdk import WeatherApiResponse
import csv
import datetime
import requests_cache
import pandas as pd
from retry_requests import retry
from station import Station

# Setup the Open-Meteo API client with cache and retry on error
cache_session = requests_cache.CachedSession(".cache", expire_after=3600)
retry_session = retry(cache_session, retries=5, backoff_factor=0.2)
openmeteo = openmeteo_requests.Client(session=retry_session)


# Get the weather forecast for a specific location
def get_weather_forecast(stations: list[Station]):
    latitudes = [s.latitude for s in stations]
    longitudes = [s.longitude for s in stations]
    url = "https://api.open-meteo.com/v1/forecast"
    params = {
        "latitude": latitudes,
        "longitude": longitudes,
        "hourly": ["temperature_2m", "precipitation_probability", "precipitation"],
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
    responses = openmeteo.weather_api(url, params=params, verify=False)
    return responses


# Get the hourly data as a pandas DataFrame
def get_hourly_dataframe(response: WeatherApiResponse, station: Station):
    # Process hourly data. The order of variables needs to be the same as requested.
    hourly = response.Hourly()
    hourly_temperature_2m = hourly.Variables(0).ValuesAsNumpy()
    hourly_precipitation_probability = hourly.Variables(1).ValuesAsNumpy()
    hourly_precipitation = hourly.Variables(2).ValuesAsNumpy()

    hourly_data = {
        "date": pd.date_range(
            start=pd.to_datetime(hourly.Time(), unit="s", utc=True),
            end=pd.to_datetime(hourly.TimeEnd(), unit="s", utc=True),
            freq=pd.Timedelta(seconds=hourly.Interval()),
            inclusive="left",
        )
    }
    hourly_data["station_id"] = station.id
    hourly_data["station_name"] = station.name
    hourly_data["station_latitude"] = station.latitude
    hourly_data["station_longitude"] = station.longitude
    hourly_data["forecast_latitude"] = response.Latitude()
    hourly_data["forecast_longitude"] = response.Longitude()
    hourly_data["temperature_2m"] = hourly_temperature_2m
    hourly_data["precipitation_probability"] = hourly_precipitation_probability
    hourly_data["precipitation"] = hourly_precipitation

    df = pd.DataFrame(data=hourly_data)
    print(f"Hourly data for {station.name} [{station.id}]")
    print(df)
    return df


# Get the daily data as a pandas DataFrame
def get_daily_dataframe(response: WeatherApiResponse, station: Station):
    # Process daily data. The order of variables needs to be the same as requested.
    daily = response.Daily()
    daily_temperature_2m_max = daily.Variables(0).ValuesAsNumpy()
    daily_temperature_2m_min = daily.Variables(1).ValuesAsNumpy()
    daily_precipitation_sum = daily.Variables(2).ValuesAsNumpy()
    daily_rain_sum = daily.Variables(3).ValuesAsNumpy()
    daily_precipitation_hours = daily.Variables(4).ValuesAsNumpy()
    daily_precipitation_probability_max = daily.Variables(5).ValuesAsNumpy()
    daily_wind_speed_10m_max = daily.Variables(6).ValuesAsNumpy()

    daily_data = {
        "date": pd.date_range(
            start=pd.to_datetime(daily.Time(), unit="s", utc=True),
            end=pd.to_datetime(daily.TimeEnd(), unit="s", utc=True),
            freq=pd.Timedelta(seconds=daily.Interval()),
            inclusive="left",
        )
    }
    daily_data["station_id"] = station.id
    daily_data["station_name"] = station.name
    daily_data["station_latitude"] = station.latitude
    daily_data["station_longitude"] = station.longitude
    daily_data["forecast_latitude"] = response.Latitude()
    daily_data["forecast_longitude"] = response.Longitude()
    daily_data["temperature_2m_max"] = daily_temperature_2m_max
    daily_data["temperature_2m_min"] = daily_temperature_2m_min
    daily_data["precipitation_sum"] = daily_precipitation_sum
    daily_data["rain_sum"] = daily_rain_sum
    daily_data["precipitation_hours"] = daily_precipitation_hours
    daily_data["precipitation_probability_max"] = daily_precipitation_probability_max
    daily_data["wind_speed_10m_max"] = daily_wind_speed_10m_max

    df = pd.DataFrame(data=daily_data)
    print(f"Daily data for {station.name} [{station.id}]")
    return df


print("Reading station data...")
with open("station-data.csv", mode="r", newline="") as location_file:
    reader = csv.reader(location_file)
    stations = []
    next(reader, None)  # skip the headers row
    for row in reader:
        station = Station(
            id=int(row[0]), name=row[1], latitude=float(row[3]), longitude=float(row[4])
        )
        print(station)
        stations.append(station)
    responses = get_weather_forecast(stations)

    hourly_dfs = []
    daily_dfs = []
    for station, response in zip(stations, responses):
        print(f"Coordinates {response.Latitude()}°N {response.Longitude()}°E")
        print(f"Elevation {response.Elevation()} m asl")
        print(f"Timezone {response.Timezone()} {response.TimezoneAbbreviation()}")
        print(f"Timezone difference to GMT+0 {response.UtcOffsetSeconds()} s")

        hourly_df = get_hourly_dataframe(response, station)
        hourly_dfs.append(hourly_df)

        daily_df = get_daily_dataframe(response, station)
        daily_dfs.append(daily_df)

    hourly_combined = pd.concat(hourly_dfs, ignore_index=True)
    daily_combined = pd.concat(daily_dfs, ignore_index=True)

    hourly_filename = "forecast_weather_hourly_{:%Y-%m-%d}.csv".format(
        datetime.datetime.now()
    )
    daily_filename = "forecast_weather_daily_{:%Y-%m-%d}.csv".format(
        datetime.datetime.now()
    )

    hourly_combined.to_csv(hourly_filename)
    daily_combined.to_csv(daily_filename)
