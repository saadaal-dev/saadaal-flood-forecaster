import openmeteo_requests
from openmeteo_sdk import WeatherApiResponse
import csv
import datetime
import requests_cache
import pandas as pd
from retry_requests import retry
from station import Station

# Setup the Open-Meteo API client with cache and retry on error
cache_session = requests_cache.CachedSession(".cache", expire_after=-1)
retry_session = retry(cache_session, retries=5, backoff_factor=0.2)
openmeteo = openmeteo_requests.Client(session=retry_session)


def get_historical_weather(stations: list[Station]):
    latitudes = [s.latitude for s in stations]
    longitudes = [s.longitude for s in stations]

    # Make sure all required weather variables are listed here
    # The order of variables in hourly or daily is important to assign them correctly below
    url = "https://archive-api.open-meteo.com/v1/archive"
    end_date = datetime.datetime.now()
    start_date = end_date - datetime.timedelta(days=3 * 365)
    params = {
        "latitude": latitudes,
        "longitude": longitudes,
        "start_date": start_date.strftime("%Y-%m-%d"),
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
    responses = openmeteo.weather_api(url, params=params, verify=False)
    return responses


# Get the daily data as a pandas DataFrame
def get_daily_dataframe(response: WeatherApiResponse, station: Station):
    # Process daily data. The order of variables needs to be the same as requested.
    daily = response.Daily()
    daily_temperature_2m_max = daily.Variables(0).ValuesAsNumpy()
    daily_temperature_2m_min = daily.Variables(1).ValuesAsNumpy()
    daily_precipitation_sum = daily.Variables(2).ValuesAsNumpy()
    daily_rain_sum = daily.Variables(3).ValuesAsNumpy()
    daily_precipitation_hours = daily.Variables(4).ValuesAsNumpy()

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

    daily_dataframe = pd.DataFrame(data=daily_data)
    print(daily_dataframe)
    return daily_dataframe


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
    responses = get_historical_weather(stations)

    hourly_dfs = []
    daily_dfs = []
    for station, response in zip(stations, responses):
        print(f"Coordinates {response.Latitude()}°N {response.Longitude()}°E")
        print(f"Elevation {response.Elevation()} m asl")
        print(f"Timezone {response.Timezone()} {response.TimezoneAbbreviation()}")
        print(f"Timezone difference to GMT+0 {response.UtcOffsetSeconds()} s")

        daily_df = get_daily_dataframe(response, station)
        daily_dfs.append(daily_df)

    daily_combined = pd.concat(daily_dfs, ignore_index=True)
    daily_filename = "historical_weather_daily_{:%Y-%m-%d}.csv".format(
        datetime.datetime.now()
    )
    daily_combined.to_csv(daily_filename)
