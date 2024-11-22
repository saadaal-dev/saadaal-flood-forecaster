import pandas as pd


DEFAULT_STATION_LAG_DAYS = [1, 3, 7, 14]

def preprocess_station(station_df, lag_days=DEFAULT_STATION_LAG_DAYS, only_lag_columns=False):
    """
    Preprocess a single station dataframe:
     - add lagged values for the level__m column
    """

    if only_lag_columns:
        df = station_df[[]]
    else:
        df = station_df[["level__m"]]

    for lag_days in lag_days:
        df = df.merge(station_df[["level__m"]].shift(lag_days).add_prefix(f"lag{lag_days}_"), left_index=True, right_index=True)
    
    return df


def preprocess_all_stations(ref_station_df, upstream_station_dfs, lag_days=DEFAULT_STATION_LAG_DAYS):
    # """
    # Preprocess all station dataframes:
    #  - add lagged values for the level__m column on all stations
    #  - remove rows with empty lagged values
    #  - merge all station data on a line (ref + upstreams)
    # """

    ref_station_df = preprocess_station(ref_station_df, lag_days, only_lag_columns=False)

    for station, station_df in upstream_station_dfs.items():
        df = preprocess_station(station_df, lag_days, only_lag_columns=True).add_prefix(f"{station}_")

        # add station data without empty lag values
        ref_station_df = ref_station_df.merge(df[max(lag_days):], left_index=True, right_index=True)

    return ref_station_df


DEFAULT_WEATHER_LAG_DAYS = [1, 3, 7, 14] + [-1, -3, -7]


def preprocess_historical_weather(weather_df, lag_days=DEFAULT_WEATHER_LAG_DAYS):
    """
    Preprocess a single station dataframe:
     - add lagged values for the precipitation_sum and precipitation_hours columns

    NOTE: negative values are forecasts
    """
    df = weather_df[["precipitation_sum", "precipitation_hours"]]

    for lag_days in lag_days:
        shift_df = weather_df[["precipitation_sum", "precipitation_hours"]].shift(lag_days)

        if lag_days < 0:
            shift_df = shift_df.add_prefix(f"forecast{-lag_days}_")
        else:
            shift_df = shift_df.add_prefix(f"lag{lag_days}_")
        df = df.merge(shift_df, left_index=True, right_index=True)
    
    return df


def preprocess_all_historical_weather(weather_dfs, lag_days=DEFAULT_WEATHER_LAG_DAYS):
    acc_df = None
    for weather_location, weather_df in weather_dfs.items():
        df = preprocess_historical_weather(weather_df, lag_days).add_prefix(f"{weather_location}_")

        if acc_df is None:
            acc_df = df
        else:
            # add weather data without empty lag values
            acc_df = acc_df.merge(df[max(lag_days):], left_index=True, right_index=True)

    return acc_df


def preprocess(d, station_lag_days=DEFAULT_STATION_LAG_DAYS, weather_lag_days=DEFAULT_WEATHER_LAG_DAYS, forecast_days=1):
    # TODO: keep ref and upstreams separate at load time?
    ref_station_df = None
    upstream_station_dfs = {}
    for station, df in d["stations"].items():
        if station == d["station"]:
            ref_station_df = df
        else:
            upstream_station_dfs[station] = df
    
    stations_df = preprocess_all_stations(ref_station_df, upstream_station_dfs, lag_days=station_lag_days)
    weathers_df = preprocess_all_historical_weather(d["weathers"], lag_days=weather_lag_days)

    df = pd.merge(stations_df, weathers_df, left_index=True, right_index=True)

    df['y'] = df['level__m']
    df = df.drop("level__m", axis=1)
    df = df.reset_index()
    df = df.rename({"date": "ds"}, axis=1)

    if forecast_days > 1:
        # shift for output data of <forecast_days>-1 (-1 since y contains the next day prediction by default)
        shift = -forecast_days+1
        df['y'] = df['y'].shift(shift)

        # data usable for a forecast (without output label, only input data):
        # # forecast dates (last <forecast_days> days not available)
        # forecast_df = df[shift:]

        # remove null entries (last <forecast_days> days not available)
        df = df[:shift]

    return df


def preprocess_diff(d, station_lag_days=DEFAULT_STATION_LAG_DAYS, weather_lag_days=DEFAULT_WEATHER_LAG_DAYS):
    # TODO: keep ref and upstreams separate at load time?
    ref_station_df = None
    upstream_station_dfs = {}
    for station, df in d["stations"].items():
        if station == d["station"]:
            ref_station_df = df
        else:
            upstream_station_dfs[station] = df
    
    stations_df = preprocess_all_stations(ref_station_df, upstream_station_dfs, lag_days=station_lag_days)
    weathers_df = preprocess_all_historical_weather(d["weathers"], lag_days=weather_lag_days)

    df = pd.merge(stations_df, weathers_df, left_index=True, right_index=True)

    # apply Prophet structure
    df['y'] = df['level__m'] - df['lag1_level__m']
    df = df.reset_index()
    df = df.rename({"date": "ds"}, axis=1)

    return df


def preprocess_to_csv(d, path):
    df = preprocess(d)
    
    # write output to csv file
    df.to_csv(path, index=False)
