import json
import os
from datetime import datetime
from typing import Optional, Tuple, List

import numpy as np
import pandas as pd

from flood_forecaster.data_ingestion.load import (
    load_inference_river_levels, load_inference_weather,
    load_modelling_river_levels, load_modelling_weather
)
from flood_forecaster.data_model.river_station import get_river_station_metadata
from flood_forecaster.ml_model.inference import infer_from_raw_data, store_inference_result
from flood_forecaster.ml_model.modelling import corr_chart, eval_chart
from flood_forecaster.ml_model.preprocess import preprocess_diff
from flood_forecaster.ml_model.registry import MODEL_MANAGER_REGISTRY
from flood_forecaster.utils.configuration import Config, DataOutputType
from flood_forecaster.utils.database_helper import DatabaseConnection

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
- list_available_model_params(config, station=None, forecast_days=None, model_type=None),
  to list the model parameters of the available pretrained models
"""


MODEL_NAME_FORMAT_STR = "{preprocessor_type}-f{forecast_days}-{model_type}-{station}"


def __get_model_name(config, station, forecast_days, model_type):
    model_config = config.load_model_config()
    preprocessor_type = model_config["preprocessor_type"]
    return MODEL_NAME_FORMAT_STR.format(
        preprocessor_type=preprocessor_type,
        forecast_days=forecast_days,
        model_type=model_type,
        station=station,
    )


def get_model_params_from_model_name(model_name: str) -> Tuple[str, int, str, str]:
    """
    Extracts the model parameters from the model name.
    The model name is expected to be in the format specified by MODEL_NAME_FORMAT_STR
    """
    # Logic baseed on the expected format of the model name
    parts = model_name.split("-", 4)
    if len(parts) < 4:
        raise ValueError(f"Model name '{model_name}' does not match expected format '{MODEL_NAME_FORMAT_STR}'.")
    
    preprocessor_type = parts[0]
    forecast_days = int(parts[1][1:])  # remove 'f' prefix
    model_type = parts[2]
    station = parts[3]
    return preprocessor_type, forecast_days, model_type, station


def list_model_params_from_model_path(
    model_path: str,
    station: Optional[str] = None,
    forecast_days: Optional[int] = None,
    model_type: Optional[str] = None,
) -> List[Tuple[str, Optional[int], str, str]]:
    """
    Extracts the list of available model parameters from the pretrained models stored in model_path.
    The model path is expected to contain model files named according to MODEL_NAME_FORMAT_STR.
    :param model_path: The path to the directory containing the model files.
    :param station: Optional filter for the station name. If provided, only models for this station will be returned.
    :param forecast_days: Optional filter for the forecast days. If provided, only models for this number of forecast days will be returned.
    :param model_type: Optional filter for the model type. If provided, only models of this type will be returned.
    :return: A list of tuples containing the model parameters (preprocessor_type, forecast_days, model_type, station).
    """
    model_files = [f for f in os.listdir(model_path) if os.path.isfile(os.path.join(model_path, f))]
    model_params = []
    for model_file in model_files:
        try:
            _preprocessor_type, _forecast_days, _model_type, _station = get_model_params_from_model_name(model_file)

            # Apply filters if specified
            # preprocessor_type not considered here, as it is not a parameter (driven by model)
            if station is not None and _station != station:
                continue
            if forecast_days is not None and _forecast_days != forecast_days:
                continue
            if model_type is not None and _model_type != model_type:
                continue

            model_params.append((_preprocessor_type, _forecast_days, _model_type, _station))

        except ValueError:
            # skip files that do not match the expected format
            continue

    return model_params


def list_available_dummy_model_params(
    config: Config,
    station: Optional[str] = None,
    forecast_days: Optional[int] = None,
    model_type: Optional[str] = None,
) -> List[Tuple[str, Optional[int], str, str]]:
    """
    List the available dummy model parameters.
    This function will return a list of tuples containing the model parameters
    (preprocessor_type, forecast_days, model_type, station).
    """
    stations = [station] if station else config.load_station_mapping().keys()
    
    model_params = []
    for model_type in MODEL_MANAGER_REGISTRY.keys():
        if "dummy" not in model_type.lower():
            continue

        for station in stations:
            # Add dummy models for each model type
            # NOTE: preprocessor_type is deprecated and will be removed in the future (moved as part of the model)
            # NOTE: forecast_days is not used for dummy models, so it is set to None (supporting all forecast days)
            model_params.append((None, None, model_type, station))

    return model_params


def __get_preprocessed_data_path(config, station, forecast_days, suffix=".csv"):
    model_config = config.load_model_config()
    preprocessed_data_path = model_config["preprocessed_data_path"]
    preprocessor_type = model_config["preprocessor_type"]
    return preprocessed_data_path + preprocessor_type + f"-f{forecast_days}-{station}{suffix}"


def __get_analysis_global_output_path(config, forecast_days, suffix):
    model_config = config.load_model_config()
    analysis_data_path = model_config["analysis_data_path"]
    preprocessor_type = model_config["preprocessor_type"]
    return analysis_data_path + preprocessor_type + f"-f{forecast_days}-global_analysis-{suffix}"


def __get_analysis_output_path(config, station, forecast_days, suffix):
    model_config = config.load_model_config()
    analysis_data_path = model_config["analysis_data_path"]
    preprocessor_type = model_config["preprocessor_type"]
    return analysis_data_path + preprocessor_type + f"-f{forecast_days}-{station}-analysis-{suffix}"


def __get_training_data_path(config, station, forecast_days):
    model_config = config.load_model_config()
    training_data_path = model_config["training_data_path"]
    preprocessor_type = model_config["preprocessor_type"]
    return training_data_path + preprocessor_type + f"-f{forecast_days}-{station}.csv"


def __get_eval_data_path(config, station, forecast_days):
    model_config = config.load_model_config()
    evaluation_data_path = model_config["evaluation_data_path"]
    preprocessor_type = model_config["preprocessor_type"]
    return evaluation_data_path + preprocessor_type + f"-f{forecast_days}-{station}.csv"


def __get_eval_output_path(config, station, forecast_days, model_type, suffix):
    model_config = config.load_model_config()
    evaluation_data_path = model_config["evaluation_data_path"]
    preprocessor_type = model_config["preprocessor_type"]
    return evaluation_data_path + preprocessor_type + f"-f{forecast_days}-{station}-{model_type}{suffix}"


def preprocess(station, config: Config, forecast_days=None):
    print("Preprocessing data...")
    model_config = config.load_model_config()

    station_metadata = config.load_station_mapping()[station]
    # print(f"Station mapping:\n{json.dumps(station_metadata.__dict__, indent=2)}")

    if forecast_days is None:
        forecast_days = int(model_config["forecast_days"])

    stations_df = load_modelling_river_levels(config, station_metadata.upstream_stations)
    print(f"Loaded {len(stations_df):,.0f} river level entries for station {station}.")

    weather_df = load_modelling_weather(config, station_metadata.weather_locations)
    print(f"Loaded {len(weather_df):,.0f} weather entries for station {station}.")

    if stations_df.empty:
        raise ValueError(f"No river level data found for station {station}. Please check the data source.")
    
    if weather_df.empty:
        raise ValueError(f"No weather data found for station {station}. Please check the data source.")

    station_lag_days = json.loads(model_config["river_station_lag_days"])
    weather_lag_days = json.loads(model_config["weather_lag_days"])

    # DUMB CHECK: ensure that there are at least max(station_lag_days) days of data available
    if len(stations_df) < max(station_lag_days):
        raise ValueError(f"Not enough river level data available for station {station}. "
                         f"Expected at least {max(station_lag_days)} days, but found only {len(stations_df)} days.")
    if len(weather_df) < max(weather_lag_days):
        raise ValueError(f"Not enough weather data available for station {station}. "
                         f"Expected at least {max(weather_lag_days)} days, but found only {len(weather_df)} days.")

    # TODO: add support for other preprocessors
    df = preprocess_diff(station_metadata, stations_df, weather_df, station_lag_days=station_lag_days, weather_lag_days=weather_lag_days, forecast_days=forecast_days)

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
    # WARNING: all stations are processed
    dfs = []
    for station in config.load_station_mapping().keys():
        preprocessed_data_path = __get_preprocessed_data_path(config, station, forecast_days, suffix=".csv")
        try:
            df = pd.read_csv(preprocessed_data_path)
        except FileNotFoundError:
            print(f"WARNING: Preprocessed data for station {station} not found at {preprocessed_data_path}. Skipping analysis for this station.")
            continue
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
    
    corr_chart_path = __get_analysis_global_output_path(config, forecast_days, suffix="_corr_chart.png")
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

    # add error message if train or test set is empty (not enough data or wrong split date)
    if train_df.empty:
        raise RuntimeError(f"Training data is empty after split. Please check the split date '{split_date}' and the available data.")
    if test_df.empty:
        raise RuntimeError(f"Evaluation data is empty after split. Please check the split date '{split_date}' and the available data.")

    # print boundaries
    print(f"Training data from {train_df['date'].min()} to {train_df['date'].max()} ({len(train_df):,.0f} entries).")
    print(f"Evaluation data from {test_df['date'].min()} to {test_df['date'].max()} ({len(test_df):,.0f} entries).")

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


def rmse(a, b):
    """
    Calculate the Root Mean Square Error between two arrays.
    The RMSE is a measure of the differences between predicted and actual values where larger errors are penalized more heavily.
    It is calculated as the square root of the average of the squared differences between predicted and actual values.

    :param a: First array.
    :param b: Second array.
    :return: The RMSE value.
    """
    return ((a - b)**2).mean()**0.5


def weighted_rmse(a, b, weights):
    """
    Calculate the Weighted Root Mean Square Error between two arrays.
    The Weighted RMSE is a measure of the differences between predicted and actual values where larger errors are penalized more heavily,
    with additional weights applied to each error term.
    It is calculated as the square root of the weighted average of the squared differences between predicted and actual values.

    :param a: First array.
    :param b: Second array.
    :param weights: Weights to apply to each error term.
    :return: The Weighted RMSE value.
    """
    return (weights * (a - b)**2).sum() / weights.sum()**0.5


def plateau_sigmoid_weight(x, threshold, max_threshold=None, steepness=2.0):
    """
    Function for calculating sigmoid weights based on 2 thresholds:
    - threshold: the level at which the weight starts increasing
    - max_threshold: the river level at which the weight reaches its maximum and remains constant thereafter

    The sigmoid function is defined as:
    weight = 1 / (1 + exp(-steepness * (x - threshold)))
    where steepness controls how quickly the weight increases as x approaches the threshold.
    Above max_threshold, the weight is set to 1.0 (maximum weight).

    :param x: Input value or array of values.
    :param threshold: The level at which the weight starts increasing.
    :param max_threshold: The river level at which the weight reaches its maximum and remains constant thereafter.
    :param steepness: Controls how quickly the weight increases as x approaches the threshold.
    :return: The calculated weight(s).
    """
    if max_threshold is not None:
        if hasattr(x, 'values'):
            x_values = x.values
        else:
            x_values = x
        above_max = x_values >= max_threshold
        result = 1 / (1 + np.exp(-steepness * (x_values - threshold)))
        result[above_max] = 1.0
        return result
    else:
        return 1 / (1 + np.exp(-steepness * (x - threshold)))


def get_weights(levels, level_moderate, level_high):
    """
    This weighting scheme is designed to put more emphasis on higher river levels where accurate predictions are critical.

    Calculate weights based on river levels using a progressive sigmoid function until level_moderate,
    and adds a constant weight above level_high (all events are considered equally important above this threshold,
    a discontinuity is introduced here to highlight the criticality of these events).
    The weights increase as the river level approaches and exceeds the moderate and high thresholds.

    The weights are calculated as follows:
    1. Base weight of 1.0 for all levels.
    2. Additional weight of up to 4.0 as levels approach the moderate threshold (smoothened using a sigmoid function).
    3. Additional weight of 5.0 for levels exceeding the high threshold (on top of the base and moderate weights).

    Example weights:
    - Level 0 (low): Weight = 1.0
    - Level at moderate threshold: Weight = 1.0 + 4.0 = 5.0
    - Level at high threshold: Weight = 1.0 + 4.0 + 5.0 = 10.0
    - Level above high threshold: Weight = 1.0 + 4.0 + 5.0 = 10.0
    
    :param levels: Array of river levels.
    :param level_moderate: Moderate threshold for river levels.
    :param level_high: High threshold for river levels.
    :return: Array of weights corresponding to the input river levels.
    """
    base_weight = 1.0
    moderate_addition = 4.0
    high_addition = 5.0

    moderate_component = plateau_sigmoid_weight(
        levels,
        threshold=level_moderate,
        max_threshold=level_high,  # same always at high river levels
        steepness=2.0
    ) * moderate_addition

    high_mask = levels >= level_high
    high_component = np.zeros(len(levels))
    high_component[high_mask] = high_addition
    weights = base_weight + moderate_component + high_component
    return weights


def eval(station_name: str, config: Config, forecast_days=None, model_type=None):
    print("Evaluating model...")
    model_config = config.load_model_config()

    # load station metadata from file
    station_metadata = get_river_station_metadata(config, station_name)

    # extract river level thresholds from pd.Series object
    level_moderate = station_metadata.moderate_threshold
    level_high = station_metadata.high_threshold
    level_full = station_metadata.full_threshold

    if forecast_days is None:
        forecast_days = int(model_config["forecast_days"])

    if model_type is None:
        model_type = model_config["model_type"]

    model_manager = MODEL_MANAGER_REGISTRY[model_type]

    # TODO: add support for other input formats
    eval_df = pd.read_csv(__get_eval_data_path(config, station_name, forecast_days))
    eval_df['date'] = pd.to_datetime(eval_df['date'], utc=False, format="%Y-%m-%d").dt.tz_localize(None)
    print(f"Evaluation data loaded, {len(eval_df):,.0f} entries.")

    model_path = model_config["model_path"]
    model = model_manager.load(model_path=model_path,
                               model_name=__get_model_name(config, station_name, forecast_days, model_type))

    pred_df = model_manager.eval(model, eval_df.drop(columns=["location"])).reset_index()

    pred_df_path = __get_eval_output_path(config, station_name, forecast_days, model_type, "-predictions.csv")
    print(f"Storing predictions in {pred_df_path}.")
    pred_df.to_csv(pred_df_path, index=False)

    def __plot_eval_chart(df: pd.DataFrame, abs: bool, start_date: Optional[str] = None, end_date: Optional[str] = None,
                          suffix: str = ""):
        suffix = ("-abs" if abs else "-diff") + suffix

        if start_date is not None:
            df = df[df["date"] >= start_date]
        if end_date is not None:
            df = df[df["date"] < end_date]

        eval_chart_path = __get_eval_output_path(config, station_name, forecast_days, model_type, suffix + ".png")

        fig, ax = eval_chart(
            df,
            level_moderate=level_moderate,
            level_high=level_high,
            level_full=level_full,
            abs=abs,
        )
        ax.set_title(f"{station_name}: " + ax.get_title() + f" - Forecast at {forecast_days} days")
        fig.savefig(eval_chart_path)
        print(f"Stored evaluation chart ({suffix}) in {eval_chart_path}.")

    for abs in [True, False]:
        __plot_eval_chart(pred_df, abs=abs)
        __plot_eval_chart(pred_df, abs=abs, start_date="2023-10", end_date="2023-12", suffix="-zoom_1")
        __plot_eval_chart(pred_df, abs=abs, start_date="2024-04", end_date="2024-06", suffix="-zoom_2")
        __plot_eval_chart(pred_df, abs=abs, start_date="2024-07", end_date="2024-10", suffix="-zoom_3")

    # print evaluation metrics
    print("Evaluation metrics:")
    print("Diff pred vs test")
    print((pred_df["abs_pred_y"] - pred_df["abs_test_y"]).describe())

    print(pred_df[["abs_pred_y", "abs_test_y"]])
    print(eval_df["y"].describe())

    # NOTE: shift by <forecast_days> to replicate previous river level as prediction
    # FIXME: this should target the diff, not the absolute level
    baseline_pred_y = eval_df[f"lagabs{forecast_days:02}__level__m"]

    baseline_rmse_value = rmse(baseline_pred_y, eval_df["y"])
    print("Baseline RMSE: {:.2f}".format(baseline_rmse_value))

    baseline_weighted_rmse_value = weighted_rmse(
        baseline_pred_y,
        eval_df["y"],
        get_weights(eval_df["y"], level_moderate, level_high)
    )
    print("Baseline Weighted RMSE: {:.2f}".format(baseline_weighted_rmse_value))

    rmse_value = rmse(pred_df["abs_pred_y"], pred_df["abs_test_y"])
    print("Model RMSE: {:.2f}".format(rmse_value))

    weighted_rmse_value = weighted_rmse(
        pred_df["abs_pred_y"],
        pred_df["abs_test_y"],
        get_weights(pred_df["abs_test_y"], level_moderate, level_high)
    )
    print("Model Weighted RMSE: {:.2f}".format(weighted_rmse_value))


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


def infer(
        station,
        config: Config,
        forecast_days: Optional[int] = None,
        date: datetime = datetime.now(),
        model_type: Optional[str] = None,
        output_type: DataOutputType = DataOutputType.STDOUT,
):
    """
    Run inference for a given station, look ahead <forecast_days> days and
    return the predicted river level at the given date + (forecast_days-1).
    This function will load the preprocessed data for the given station,
    apply the model and return the predicted river level.

    Parameters:
    :station (str): The station name to run inference for.
    :config (Config): The configuration object containing the model and data paths.
    :forecast_days (int, optional): The number of days to look ahead for the prediction.
        Defaults to None, which will use the value from the model config.
    :date (datetime.date, optional): The date to run inference for. Defaults to today.
    :model_type (str, optional): The type of model to use for inference.
        Defaults to None, which will use the value from the model config.
    :output_type (DataOutputType): The type of output behaviour. Defaults to DataOutputType.STDOUT.
    Returns:
    :float: The predicted river level at the given date + (forecast_days-1).
    """
    model_config = config.load_model_config()

    print("Running inference...")
    station_metadata = config.load_station_mapping()[station]
    # print(f"Station mapping:\n{json.dumps(station_metadata.__dict__, indent=2)}")
    station_lag_days = json.loads(model_config["river_station_lag_days"])
    weather_lag_days = json.loads(model_config["weather_lag_days"])

    if forecast_days is None:
        forecast_days = int(model_config["forecast_days"])

    if model_type is None:
        model_type = model_config["model_type"]
    model_manager = MODEL_MANAGER_REGISTRY[model_type]

    weather_df = load_inference_weather(config, station_metadata.weather_locations, date=date)
    stations_df = load_inference_river_levels(config, station_metadata.upstream_stations, date=date)

    # Check that at least one entry is available for the given date
    if stations_df.empty:
        raise ValueError(f"No river level data found for station {station} on {date}. Please check the data source.")
    if weather_df.empty:
        raise ValueError(f"No weather data found for station {station} on {date}. Please check the data source.")
    
    # Check that all expected data is available
    stations_min_date = (date - pd.Timedelta(days=max(station_lag_days))).date()
    stations_max_date = date.date()
    weather_min_date = (date - pd.Timedelta(days=max(weather_lag_days))).date()
    weather_max_date = (date + pd.Timedelta(days=-min(weather_lag_days))).date()  # reminder: weather_lag_days are negative, so we subtract the minimum lag day

    # # River Levels
    for location in station_metadata.upstream_stations:
        stations_date_range = pd.date_range(start=stations_min_date, end=stations_max_date)
        # Ensure that the stations_df contains all dates in the range for the given location
        _expected_len = len(stations_date_range)
        _actual_df = stations_df.merge(
            pd.DataFrame({"date": stations_date_range, "location": location}),
            on=["date", "location"],
            how='inner'
        )

        _len_actual_df = len(_actual_df)
        if _len_actual_df < _expected_len:
            _diff_dates = stations_date_range.difference(_actual_df['date'].to_list())
            print(f"Missing dates for station {station}: {_diff_dates.to_list()}")
            raise ValueError(f"Not enough river level data available for station {station}. "
                             f"Expected at least {_expected_len} days, but found only {_len_actual_df} days. "
                             f"Please check the data source.")

    # # Weather data
    for location in station_metadata.weather_locations:
        weather_date_range = pd.date_range(start=weather_min_date, end=weather_max_date)
        # Ensure that the weather_df contains all dates in the range for the given location
        _expected_len = len(weather_date_range)
        _actual_df = weather_df.merge(
            pd.DataFrame({"date": weather_date_range, "location": location}),
            on=["date", "location"],
            how='inner'
        )

        _len_actual_df = len(_actual_df)
        if _len_actual_df < _expected_len:
            _diff_dates = weather_date_range.difference(_actual_df['date'].to_list())
            print(f"Missing dates for station {station}: {_diff_dates.to_list()}")
            raise ValueError(f"Not enough weather data available for station {station}. "
                             f"Expected at least {_expected_len} days, but found only {_len_actual_df} days. "
                             f"Please check the data source.")

    weather_df['date'] = pd.to_datetime(weather_df['date'], utc=False, format="%Y-%m-%d %H:%M:%S%z").dt.tz_localize(None).dt.date.astype("datetime64[ns]")
    stations_df['date'] = pd.to_datetime(stations_df['date'], utc=False, format="%d/%m/%Y").dt.tz_localize(None).dt.date.astype("datetime64[ns]")

    model_path = model_config["model_path"]
    model_name = __get_model_name(config, station, forecast_days, model_type)
    inference_df = infer_from_raw_data(
        model_manager, model_path, model_name,
        station_metadata, stations_df, weather_df,
        station_lag_days, weather_lag_days, forecast_days
    )

    if inference_df.empty:
        raise RuntimeError("Inference DataFrame is empty. Please check the input data and preprocessing steps.")
    
    # print first entry of inference_df as a JSON
    # print("Inference DataFrame:")
    # Convert Timestamp objects to strings to avoid serialization errors
    inference_record = inference_df.head(1).to_dict(orient='records')[0]
    for key, value in inference_record.items():
        if isinstance(value, pd.Timestamp) or isinstance(value, datetime):
            inference_record[key] = value.isoformat()
    # print(json.dumps(inference_record, indent=2))
    # print()

    y_diff = inference_df['y'].values[0]
    y = inference_df['lagabs01__level__m'].values[0] + y_diff
    if pd.isna(y):
        raise RuntimeError("Predicted river level is NaN. Please check the input data and preprocessing steps.")

    date_str = date.strftime("%Y-%m-%d")
    target_date_str = (date + pd.Timedelta(days=forecast_days - 1)).strftime("%Y-%m-%d")
    y_diff_str = "river level going " + (f"up by {y_diff:.2f} m" if y_diff > 0 else f"down by {y_diff:.2f} m" if y_diff < 0 else "unchanged")
    print(f"[{date_str}] Predicted river level for {station} for {target_date_str} is {y:.2f} m ({y_diff_str}).")
    
    if output_type == DataOutputType.DATABASE:
        # store the prediction in the database using:
        # location_name,
        # date,
        # ml_model_name,
        # forecast_days,
        # level_m,
        # prediction_date = date + pd.Timedelta(days=forecast_days - 1)  # TODO: not yet implemented in DB
        db_connection = DatabaseConnection(config)

        store_inference_result(
            db_connection=db_connection,
            location=station_metadata.location,
            model_name=model_name,
            forecast_days=forecast_days,
            date=date,
            level_m=y
        )

    return y
