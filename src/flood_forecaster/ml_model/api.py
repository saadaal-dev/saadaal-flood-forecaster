import json
from datetime import datetime
from typing import Optional

import numpy as np
import pandas as pd

from src.flood_forecaster.data_ingestion.load import load_inference_river_levels, load_inference_weather, \
    load_modelling_river_levels, load_modelling_weather
from src.flood_forecaster.data_model.river_station import get_river_station_metadata
from src.flood_forecaster.ml_model.inference import infer_from_raw_data, store_inference_result
from src.flood_forecaster.ml_model.modelling import corr_chart, eval_chart
from src.flood_forecaster.ml_model.preprocess import preprocess_diff
from src.flood_forecaster.ml_model.registry import MODEL_MANAGER_REGISTRY
from src.flood_forecaster.utils.configuration import Config, DataOutputType
from src.flood_forecaster.utils.database_helper import DatabaseConnection

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


def __get_analysis_global_output_path(config, forecast_days, suffix):
    model_config = config.load_model_config()
    analysis_data_path = model_config["analysis_data_path"]
    preprocessor_type = model_config["preprocessor_type"]
    return analysis_data_path + preprocessor_type + f"_f{forecast_days}_global_analysis{suffix}"


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

    station_metadata = config.load_station_mapping()[station]
    print(f"Station mapping:\n{json.dumps(station_metadata.__dict__, indent=2)}")

    if forecast_days is None:
        forecast_days = int(model_config["forecast_days"])

    stations_df = load_modelling_river_levels(config, station_metadata.upstream_stations)
    weather_df = load_modelling_weather(config, station_metadata.weather_locations)

    station_lag_days = json.loads(model_config["river_station_lag_days"])
    weather_lag_days = json.loads(model_config["weather_lag_days"])

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

    def __plot_eval_chart(df: pd.DataFrame, abs: bool, start_date: Optional[str] = None, end_date: Optional[str] = None, suffix: str = ""):
        suffix = ("" if abs else "_diff") + suffix

        if start_date is not None:
            df = df[df["date"] >= start_date]
        if end_date is not None:
            df = df[df["date"] < end_date]

        eval_chart_path = __get_eval_output_path(config, station_name, forecast_days, model_type, suffix)

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
    # TODO: should it be forecast_days instead of 1?
    baseline_pred_y = eval_df["y"].shift(1).dropna()
    print("Baseline RMSE: {:.2f}".format(((baseline_pred_y - eval_df["y"].dropna())**2).mean()**0.5))


    # Weighted RMSE using progressive sigmoid function with weights based on river level thresholds
    errors = (pred_df["abs_pred_y"] - pred_df["abs_test_y"])**2
    base_weight = 1.0
    moderate_addition = 4.0
    high_addition = 5.0

    def plateau_sigmoid_weight(x, threshold, max_threshold=None, steepness=2.0):
        """function for calculating sigmoid weights based on river level thresholds"""

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
    
    moderate_component = plateau_sigmoid_weight(
        pred_df["abs_test_y"], 
        threshold=level_moderate,
        max_threshold=level_high,  # same always at high river levels
        steepness=2.0
    ) * moderate_addition

    high_mask = pred_df["abs_test_y"] >= level_high
    high_component = np.zeros(len(pred_df))
    high_component[high_mask] = high_addition
    weights = base_weight + moderate_component + high_component
    weighted_errors = errors * weights
    weighted_rmse = (weighted_errors.sum() / weights.sum())**0.5
    
    print(f"Plateau Sigmoid Weighted RMSE: {weighted_rmse:.2f}")


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
        date: Optional[datetime] = datetime.now(),
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
    :forecast_days (int, optional): The number of days to look ahead for the prediction. Defaults to None, which will use the value from the model config.
    :date (datetime.date, optional): The date to run inference for. Defaults to today.
    :model_type (str, optional): The type of model to use for inference. Defaults to None, which will use the value from the model config.
    :output_type (DataOutputType): The type of output behaviour. Defaults to DataOutputType.STDOUT.
    Returns:
    :float: The predicted river level at the given date + (forecast_days-1).
    """
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
    inference_df = infer_from_raw_data(
        model_manager, model_path, model_name,
        station_metadata, stations_df, weather_df,
        station_lag_days, weather_lag_days, forecast_days
    )
    # print(inference_df)

    if inference_df.empty:
        raise RuntimeError("Inference DataFrame is empty. Please check the input data and preprocessing steps.")
    
    if output_type == DataOutputType.STDOUT:
        # print first entry of inference_df as a JSON
        print("Inference DataFrame:")
        # Convert Timestamp objects to strings to avoid serialization errors
        inference_record = inference_df.head(1).to_dict(orient='records')[0]
        for key, value in inference_record.items():
            if isinstance(value, pd.Timestamp) or isinstance(value, datetime):
                inference_record[key] = value.isoformat()
        print(json.dumps(inference_record, indent=2))
        print()

    y_diff = inference_df['y'].values[0]
    y = inference_df['lag01__level__m'].values[0] + y_diff
    if pd.isna(y):
        raise RuntimeError("Predicted river level is NaN. Please check the input data and preprocessing steps.")

    if output_type == DataOutputType.STDOUT:
        date_str = date.strftime("%Y-%m-%d")
        y_diff_str = "river level going " + (f"up by {y_diff:.2f} m" if y_diff > 0 else f"down by {y_diff:.2f} m" if y_diff < 0 else "unchanged")
        print(f"Predicted river level for {station} on {date_str} is {y:.2f} m ({y_diff_str}).")
    
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
