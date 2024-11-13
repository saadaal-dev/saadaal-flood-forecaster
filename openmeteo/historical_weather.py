import openmeteo_requests
from openmeteo_sdk import WeatherApiResponse
import datetime
import requests_cache
import pandas as pd
from retry_requests import retry
from station import Station, get_stations
from district import District, get_districts


def get_historical_weather(latitudes: list[float], longitudes: list[float]):
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


def get_daily_data(response: WeatherApiResponse):
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
    daily_data["forecast_latitude"] = response.Latitude()
    daily_data["forecast_longitude"] = response.Longitude()
    daily_data["temperature_2m_max"] = daily_temperature_2m_max
    daily_data["temperature_2m_min"] = daily_temperature_2m_min
    daily_data["precipitation_sum"] = daily_precipitation_sum
    daily_data["rain_sum"] = daily_rain_sum
    daily_data["precipitation_hours"] = daily_precipitation_hours
    return daily_data


def get_daily_station_data_frame(response: WeatherApiResponse, station: Station):
    # Get the daily data as a pandas DataFrame
    daily_data = get_daily_data(response)
    daily_data["station_id"] = station.id
    daily_data["station_name"] = station.name
    daily_data["station_latitude"] = station.latitude
    daily_data["station_longitude"] = station.longitude
    daily_df = pd.DataFrame(data=daily_data)
    print(daily_df)
    return daily_df


def get_daily_district_data_frame(response: WeatherApiResponse, district: District):
    # Get the daily data as a pandas DataFrame
    daily_data = get_daily_data(response)
    daily_data["region"] = district.region
    daily_data["district"] = district.name
    daily_data["district_latitude"] = district.latitude
    daily_data["district_longitude"] = district.longitude
    daily_df = pd.DataFrame(data=daily_data)
    print(daily_df)
    return daily_df


def get_station_data():
    print("Reading station data...")
    stations: list[Station] = get_stations("station-data.csv")
    latitudes = [s.latitude for s in stations]
    longitudes = [s.longitude for s in stations]
    responses = get_historical_weather(latitudes, longitudes)

    daily_dfs = []
    for station, response in zip(stations, responses):
        print(f"Coordinates {response.Latitude()}°N {response.Longitude()}°E")
        print(f"Elevation {response.Elevation()} m asl")
        print(f"Timezone {response.Timezone()} {response.TimezoneAbbreviation()}")
        print(f"Timezone difference to GMT+0 {response.UtcOffsetSeconds()} s")

        daily_df = get_daily_station_data_frame(response, station)
        daily_dfs.append(daily_df)

    daily_combined = pd.concat(daily_dfs, ignore_index=True)
    daily_filename = "historical_station_weather_daily_{:%Y-%m-%d}.csv".format(
        datetime.datetime.now()
    )
    daily_combined.to_csv(daily_filename)


def get_district_data():
    print("Reading district data...")
    districts = get_districts("district-data.csv")
    latitudes = [d.latitude for d in districts]
    longitudes = [d.longitude for d in districts]
    responses = get_historical_weather(latitudes, longitudes)

    daily_dfs = []
    for district, response in zip(districts, responses):
        print(f"Coordinates {response.Latitude()}°N {response.Longitude()}°E")
        print(f"Elevation {response.Elevation()} m asl")
        print(f"Timezone {response.Timezone()} {response.TimezoneAbbreviation()}")
        print(f"Timezone difference to GMT+0 {response.UtcOffsetSeconds()} s")

        daily_df = get_daily_district_data_frame(response, district)
        daily_dfs.append(daily_df)

    daily_combined = pd.concat(daily_dfs, ignore_index=True)
    daily_filename = "historical_district_weather_daily_{:%Y-%m-%d}.csv".format(
        datetime.datetime.now()
    )
    daily_combined.to_csv(daily_filename)


# Setup the Open-Meteo API client with cache and retry on error
cache_session = requests_cache.CachedSession(".cache", expire_after=-1)
retry_session = retry(cache_session, retries=5, backoff_factor=0.2)
openmeteo = openmeteo_requests.Client(session=retry_session)
get_station_data()
get_district_data()
