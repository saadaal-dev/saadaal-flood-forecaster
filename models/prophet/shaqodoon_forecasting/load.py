import pandas as pd

from .settings import INPUT_DIR


def load_station(station_name, path):
    df = pd.read_csv(INPUT_DIR + f"stations/{path}")
    df = df.drop(["id", "station_number"], axis=1)
    df = df.rename({"level(m)": "level__m"}, axis=1)

    df["station"] = station_name

    df['date'] = pd.to_datetime(df['date'], dayfirst=True)
    df = df.set_index('date')

    return df.sort_index()


def load_station_belet_weyne():
    df = load_station("belet_weyne", "BeletWeyne_river_station.csv")
    df = df[df.index > '2021']
    return df


def load_station_bulo_burti():
    df = load_station("bulo_burti", "bulo_burti_river_station.csv")
    df = df[df.index > '2021']
    return df


DATA_LOADERS_STATIONS = {
    "belet_weyne": load_station_belet_weyne,
    "bulo_burti": load_station_bulo_burti,
}


def load_all_stations(stations):
    dfs = {}
    for station in stations:
        dfs[station] = DATA_LOADERS_STATIONS[station]()
    return dfs


def load_historical_weather(path):
    df = pd.read_csv(INPUT_DIR + f'weather/{path}')
    df = df.iloc[:, 1:]  # drop unnamed column
    df['date'] = pd.to_datetime(df['date']).dt.date
    df = df.set_index('date')
    return df.sort_index()


def load_weather_ethiopia_tullu_dimtu():
    df = load_historical_weather('river_source_Tullu Dimtu_historical_weather_daily_2024-11-19.csv')
    df['weather_location'] = 'ethiopia_tullu_dimtu'
    return df


def load_weather_ethiopia_fafen_haren():
    df = load_historical_weather('Ethiopia_Haren_Fafen_river_source_historical_weather_daily_2024-11-19.csv')
    df['weather_location'] = 'ethiopia_fafen_haren'
    return df


def load_weather_ethiopia_fafen_gebredarre():
    df = load_historical_weather('Ethiopia_Haren_Fafen_river_source_historical_weather_daily_2024-11-19.csv')
    df['weather_location'] = 'ethiopia_fafen_gebredarre'
    return df


def load_weather_ethiopia_shabelle_gode():
    df = load_historical_weather('Ethiopia_Gode_city_historical_weather_daily_2024-11-19.csv')
    df['weather_location'] = 'ethiopia_shabelle_gode'
    return df


def load_weather_belet_weyne():
    df = load_historical_weather('BeletWeyne_historical_weather_daily_2024-11-19.csv')
    df['weather_location'] = 'belet_weyne'
    return df


def load_weather_buro_burti():
    df = load_historical_weather('BuloBurti_historical_weather_daily_2024-11-19.csv')
    df['weather_location'] = 'bulo_burti'
    return df


DATA_LOADERS_HISTORICAL_WEATHER = {
    "ethiopia_tullu_dimtu": load_weather_ethiopia_tullu_dimtu,
    "ethiopia_fafen_haren": load_weather_ethiopia_fafen_haren,
    "ethiopia_fafen_gebredarre": load_weather_ethiopia_fafen_gebredarre,
    "ethiopia_shabelle_gode": load_weather_ethiopia_shabelle_gode,
    "belet_weyne": load_weather_belet_weyne,
    "bulo_burti": load_weather_buro_burti,
}


def load_all_historical_weather(weather_locations):
    dfs = {}
    for location in weather_locations:
        dfs[location] = DATA_LOADERS_HISTORICAL_WEATHER[location]()
    return dfs


def load_all_by_station_metadata(station_metadata):
    return {
        "station": station_metadata["station"],
        "river": station_metadata["river"],
        "stations": load_all_stations(station_metadata["stations"]),
        "weathers": load_all_historical_weather(station_metadata["weathers"])
    }
