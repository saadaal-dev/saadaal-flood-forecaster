from datetime import datetime
import json
from typing import Optional

import pandas as pd

from .inference import infer_from_raw_data

from ..utils import configuration
from ..utils.configuration import Config
from ..data_ingestion.load import load_inference_river_levels, load_inference_weather
from .preprocess import preprocess_diff
from .modelling import corr_chart, eval_chart
from .registry import MODEL_MANAGER_REGISTRY
from ..data_ingestion.openmeteo.station import get_stations


"""
Functions to interact with the model building pipeline.

The following functions are available:
- preprocess(station, config, forecast_days=None), to prepare the data for modellization
- analyze(config, forecast_days=None), to analyze the data and provide insights
- split(station, config, forecast_days=None), to split the data into training and testing sets
- train(station, config, forecast_days=None, model_type=None), to create the model
- eval(station, config, forecast_days=None, model_type=None), to test the model
- build_model(station, config, forecast_days=None, model_type=None), to run the full model building pipeline
- infer(station, config, forecast_days=None, date=datetime.now().date(), model_type=None), to predict the river level for a given date
"""


def __get_model_name(config, station, forecast_days, model_type):
    model_config = config.load_model_config()
    preprocessor_type = model_config["preprocessor_type"]
    return preprocessor_type + f"_f{forecast_days}_" + model_type + f"_{station}"


def __get_preprocessed_data_path(config, station, forecast_days, suffix=".csv"):
    model_config = config.load_model_config()
    preprocessed_data_path = model_config["preprocessed_data_path"]
    preprocessor_type = model_config["preprocessor_type"]
    return preprocessed_data_path + preprocessor_type + f"_f{forecast_days}_{station}{suffix}"


def __get_analysis_output_path(config, station, forecast_days, suffix):
    model_config = config.load_model_config()
    analysis_data_path = model_config["analysis_data_path"]
    preprocessor_type = model_config["preprocessor_type"]
    return analysis_data_path + preprocessor_type + f"_f{forecast_days}_{station}_analysis{suffix}"


def __get_training_data_path(config, station, forecast_days):    
    model_config = config.load_model_config()
    training_data_path = model_config["training_data_path"]
    preprocessor_type = model_config["preprocessor_type"]
    return training_data_path + preprocessor_type + f"_f{forecast_days}_{station}.csv"


def __get_eval_data_path(config, station, forecast_days):
    model_config = config.load_model_config()
    evaluation_data_path = model_config["evaluation_data_path"]
    preprocessor_type = model_config["preprocessor_type"]
    return evaluation_data_path + preprocessor_type + f"_f{forecast_days}_{station}.csv"


def __get_eval_output_path(config, station, forecast_days, model_type, suffix):
    model_config = config.load_model_config()
    evaluation_data_path = model_config["evaluation_data_path"]
    preprocessor_type = model_config["preprocessor_type"]
    return evaluation_data_path + preprocessor_type + f"_f{forecast_days}_{station}_{model_type}{suffix}.png"


def preprocess(station, config: Config, forecast_days=None):
    print("Preprocessing data...")
    model_config = config.load_model_config()
    csv_config = config.load_data_csv_config()

    station_metadata = config.load_station_mapping()[station]
    print(f"Station mapping:\n{json.dumps(station_metadata.__dict__, indent=2)}")

    if forecast_days is None:
        forecast_days = int(model_config["forecast_days"])

    # TODO: add support for other input formats
    stations_df = pd.read_csv(csv_config["river_stations_data_path"])
    stations_df['date'] = pd.to_datetime(stations_df['date'], utc=False, format="%d/%m/%Y").dt.tz_localize(None).dt.date.astype("datetime64[ns]")
    weather_history_df = pd.read_csv(csv_config["weather_history_data_path"])    
    weather_history_df['date'] = pd.to_datetime(weather_history_df['date'], utc=False, format="%Y-%m-%d %H:%M:%S%z").dt.tz_localize(None).dt.date.astype("datetime64[ns]")

    station_lag_days = json.loads(model_config["river_station_lag_days"])
    weather_lag_days = json.loads(model_config["weather_lag_days"])

    # TODO: add support for other preprocessors
    df = preprocess_diff(station_metadata, stations_df, weather_history_df, station_lag_days=station_lag_days, weather_lag_days=weather_lag_days, forecast_days=forecast_days)

    output_data_path = __get_preprocessed_data_path(config, station, forecast_days, suffix=".csv")
    print(f"Preprocessing data complete, storing {len(df):,.0f} entries in {output_data_path}.")
    df.to_csv(output_data_path, index=False)

    output_config_path = __get_preprocessed_data_path(config, station, forecast_days, suffix="_config.ini")
    print(f"Storing associated configuration in {output_config_path}.")
    with open(output_config_path, "w") as f:
        config._config.write(f)


def analyze(config, forecast_days=None):
    print("Analyzing data...")
    
    if forecast_days is None:
        forecast_days = int(config.load_model_config()["forecast_days"])
    
    # TODO: add support for other input formats
    dfs = []
    for station in config.load_station_mapping().keys():
        preprocessed_data_path = __get_preprocessed_data_path(config, station, forecast_days, suffix=".csv")
        df = pd.read_csv(preprocessed_data_path)
        dfs.append(df)
    df = pd.concat(dfs, axis=0)

    # QA
    print("Checking for gaps in dates...")
    date_range = pd.date_range(start=df["date"].min(), end=df["date"].max())
    missing_dates = date_range[~date_range.isin(df["date"])]
    if len(missing_dates) > 0:
        # format datetimes as dates as strings
        missing_dates = missing_dates.astype(str)
        print("WARNING: Missing dates found:\n - " + '\n - '.join(missing_dates.to_list()))
    
    corr_chart_path = __get_analysis_output_path(config, station, forecast_days, suffix="_corr_chart.png")
    print(f"Storing correlation chart in {corr_chart_path}.")
    corr_chart(df, store_path=corr_chart_path)

    print(f"Data analysis complete, {len(df):,.0f} entries analyzed.")


def split(station, config, forecast_days=None):
    print("Splitting data...")
    model_config = config.load_model_config()
    
    if forecast_days is None:
        forecast_days = int(model_config["forecast_days"])
    
    # TODO: add support for other input formats
    preprocessed_data_path = __get_preprocessed_data_path(config, station, forecast_days, suffix=".csv")
    df = pd.read_csv(preprocessed_data_path)

    split_date = model_config["train_test_date_split"]
    train_df, test_df = df[df["date"] < split_date], df[df["date"] >= split_date]
    output_training_data_path = __get_training_data_path(config, station, forecast_days)
    output_eval_data_path = __get_eval_data_path(config, station, forecast_days)
    print(f"Splitting data complete, storing training data in {output_training_data_path} and evaluation data in {output_eval_data_path}.")
    
    # add buffer for lag
    station_lag_days = json.loads(model_config["river_station_lag_days"])
    weather_lag_days = json.loads(model_config["weather_lag_days"])
    test_df = test_df.iloc[max([max(station_lag_days), max(weather_lag_days)]):, :]

    # print boundaries
    print(json.dumps({
        "train_df": (train_df["date"].min(), train_df["date"].max()),
        "test_df": (test_df["date"].min(), test_df["date"].max())
    }, indent=2))

    # print % splits
    print("Training data split: {:.2%} ({:,.0f} entries)".format(len(train_df) / len(df), len(train_df)))
    print("Evaluation data split: {:.2%} ({:,.0f} entries)".format(len(test_df) / len(df), len(test_df)))

    train_df.to_csv(output_training_data_path, index=False)
    test_df.to_csv(output_eval_data_path, index=False)


def train(station, config, forecast_days=None, model_type=None):
    print("Training model...")
    model_config = config.load_model_config()
    
    if forecast_days is None:
        forecast_days = int(model_config["forecast_days"])

    if model_type is None:
        model_type = model_config["model_type"]
    model_manager = MODEL_MANAGER_REGISTRY[model_type]

    # TODO: add support for other input formats
    df = pd.read_csv(__get_training_data_path(config, station, forecast_days))
    df['date'] = pd.to_datetime(df['date'], utc=False, format="%Y-%m-%d").dt.tz_localize(None)
    print(f"Training data loaded, {len(df):,.0f} entries.")

    # TODO: add support for other models
    model_path = model_config["model_path"]
    model, model_full_path = model_manager.train_and_serialize(df, model_path=model_path, model_name=__get_model_name(config, station, forecast_days, model_type))

    print(f"Model training complete, stored in {model_full_path}.")


def eval(station, config, forecast_days=None, model_type=None):
    print("Evaluating model...")
    static_data_config = config.load_static_data_config()
    model_config = config.load_model_config()
    river_stations_metadata_path = static_data_config["river_stations_metadata_path"]

    # load station metadata file
    for s in get_stations(river_stations_metadata_path):
        if s.name == station:
            station_metadata = s
            break
    else:
        raise ValueError(f"Station {station} not found in {river_stations_metadata_path}.")
    
    # extract river level thresholds from pd.Series object
    level_moderate = station_metadata.moderate
    level_high = station_metadata.high
    level_full = station_metadata.full

    if forecast_days is None:
        forecast_days = int(model_config["forecast_days"])

    if model_type is None:
        model_type = model_config["model_type"]
    
    model_manager = MODEL_MANAGER_REGISTRY[model_type]

    # TODO: add support for other input formats
    eval_df = pd.read_csv(__get_eval_data_path(config, station, forecast_days))
    eval_df['date'] = pd.to_datetime(eval_df['date'], utc=False, format="%Y-%m-%d").dt.tz_localize(None)
    print(f"Evaluation data loaded, {len(eval_df):,.0f} entries.")

    model_path = model_config["model_path"]
    model = model_manager.load(model_path=model_path, model_name=__get_model_name(config, station, forecast_days, model_type))

    pred_df = model_manager.eval(model, eval_df.drop(columns=["location"])).reset_index()

    def __plot_eval_chart(df: pd.DataFrame, abs: bool, start_date: Optional[str] = None, end_date: Optional[str] = None, suffix: str = ""):
        suffix = ("" if abs else "_diff") + suffix

        if start_date is not None:
            df = df[df["date"] >= start_date]
        if end_date is not None:
            df = df[df["date"] < end_date]
        
        eval_chart_path = __get_eval_output_path(config, station, forecast_days, model_type, suffix)

        fig, ax = eval_chart(
            df,
            level_moderate=level_moderate,
            level_high=level_high,
            level_full=level_full,
            abs=abs,
        )
        ax.set_title(f"{station}: " + ax.get_title() + f" - Forecast at {forecast_days} days")
        fig.savefig(eval_chart_path)
        print(f"Stored evaluation chart ({suffix}) in {eval_chart_path}.")

    for abs in [True, False]:
        __plot_eval_chart(pred_df, abs=abs)
        __plot_eval_chart(pred_df, abs=abs, start_date="2023-10", end_date="2023-12", suffix="_zoom_1")
        __plot_eval_chart(pred_df, abs=abs, start_date="2024-04", end_date="2024-06", suffix="_zoom_2")
        __plot_eval_chart(pred_df, abs=abs, start_date="2024-07", end_date="2024-10", suffix="_zoom_3")

    # print evaluation metrics
    print("Evaluation metrics:")
    print("Diff pred vs test")
    print((pred_df["abs_pred_y"] - pred_df["abs_test_y"]).describe())

    print("RMSE: {:.2f}".format(((pred_df["abs_pred_y"] - pred_df["abs_test_y"])**2).mean()**0.5))

    # Baseline RMSE:
    # replicate previous day's river level as prediction
    baseline_pred_y = eval_df["y"].shift(1).dropna()
    print("Baseline RMSE: {:.2f}".format(((baseline_pred_y - eval_df["y"].dropna())**2).mean()**0.5))


def build_model(station, config, forecast_days=None, model_type=None):
    """
    Run the full model building pipeline.
    This includes the following steps:
    - Preprocessing
    - Analysis
    - Splitting
    - Training
    - Evaluation
    """
    preprocess(station, config, forecast_days)
    analyze(config, forecast_days)
    split(station, config, forecast_days)
    train(station, config, forecast_days, model_type)
    eval(station, config, forecast_days, model_type)


def infer(station, config: Config, forecast_days=None, date=datetime.now().date(), model_type=None):
    model_config = config.load_model_config()

    print("Running inference...")
    station_metadata = config.load_station_mapping()[station]
    print(f"Station mapping:\n{json.dumps(station_metadata.__dict__, indent=2)}")
    station_lag_days = json.loads(model_config["river_station_lag_days"])
    weather_lag_days = json.loads(model_config["weather_lag_days"])
    
    if forecast_days is None:
        forecast_days = int(model_config["forecast_days"])
    
    if model_type is None:
        model_type = model_config["model_type"]
    model_manager = MODEL_MANAGER_REGISTRY[model_type]

    weather_df = load_inference_weather(config, station_metadata.weather_locations, date=date)
    stations_df = load_inference_river_levels(config, station_metadata.upstream_stations, date=date)

    weather_df['date'] = pd.to_datetime(weather_df['date'], utc=False, format="%Y-%m-%d %H:%M:%S%z").dt.tz_localize(None).dt.date.astype("datetime64[ns]")
    stations_df['date'] = pd.to_datetime(stations_df['date'], utc=False, format="%d/%m/%Y").dt.tz_localize(None).dt.date.astype("datetime64[ns]")

    model_path = model_config["model_path"]
    model_name = __get_model_name(config, station, forecast_days, model_type)
    print(infer_from_raw_data(
        model_manager, model_path, model_name, 
        station_metadata, stations_df, weather_df, 
        station_lag_days, weather_lag_days, forecast_days
    ))
