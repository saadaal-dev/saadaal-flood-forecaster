import json

import click
import pandas as pd

from . import load
from . import preprocess as preprocess_
from . import train as train_
from . import utils
from . import settings as settings_
from .train import MODEL_REGISTRY


@click.group()
def cli():
    pass

@cli.command()
def list_models():
    print("Supported model types:")
    for model_key in MODEL_REGISTRY.keys():
        print(" - " + model_key)

@cli.command()
@click.argument('station')
@click.option('-o', '--output_data_path', required=True, type=click.Path(exists=False, dir_okay=False))
@click.option('-s', '--settings_path', required=True, type=click.Path(exists=True, dir_okay=False))
def preprocess(station, output_data_path, settings_path):
    settings = utils.load_settings(settings_path)

    station_metadata = settings_.STATION_METADATA[station]

    dfs = load.load_all_by_station_metadata(station_metadata)

    preprocess_.preprocess(
        dfs, station_lag_days=settings.STATION_LAG_DAYS, weather_lag_days=settings.WEATHER_LAG_DAYS
    ).to_csv(output_data_path, index=False)

@cli.command()
@click.argument('data_path', type=click.Path(exists=True, dir_okay=False))
@click.option('-d', '--split_date', required=True)
@click.option('-t', '--training_data_path', required=True, type=click.Path(exists=False, dir_okay=False))
@click.option('-e', '--eval_data_path', required=True, type=click.Path(exists=False, dir_okay=False))
@click.option('-s', '--settings_path', required=True, type=click.Path(exists=True, dir_okay=False))
def split(data_path, split_date, training_data_path, eval_data_path, settings_path):
    settings = utils.load_settings(settings_path)

    TRAIN_TEST_DATE_SPLIT = split_date

    df = pd.read_csv(data_path)

    train_df, test_df = (
        df[(df["ds"] < TRAIN_TEST_DATE_SPLIT)],
        df[(df["ds"] >= TRAIN_TEST_DATE_SPLIT)],
    )

    # add buffer for lag
    test_df = test_df.iloc[max([max(settings.STATION_LAG_DAYS), max(settings.WEATHER_LAG_DAYS)]):, :]

    print(json.dumps({
        "train_df": (train_df["ds"].min(), train_df["ds"].max()), 
        "test_df": (test_df["ds"].min(), test_df["ds"].max())
    }, indent=2))

    train_df.to_csv(training_data_path, index=False)
    test_df.to_csv(eval_data_path, index=False)

@cli.command()
@click.argument('data_path', type=click.Path(exists=True, dir_okay=False))
@click.option('-m', '--model_type', required=True)
@click.option('-o', '--output_model_path', required=True, type=click.Path(exists=False))
@click.option('-s', '--settings_path', required=True, type=click.Path(exists=False))
def train(data_path, model_type, output_model_path, settings_path):
    data = pd.read_csv(data_path)
    data['ds'] = pd.to_datetime(data['ds'])
    train_.train_and_serialize(data, model_type, output_model_path)

@cli.command()
@click.argument('model_path', type=click.Path(exists=True, dir_okay=False))
@click.argument('model_type')
@click.argument('data_path', type=click.Path(exists=True, dir_okay=False))
@click.option('-o', '--output_dir', required=True, type=click.Path(exists=False, file_okay=False))
@click.option('-t', '--test_start_date', required=True)
@click.option('-T', '--test_end_date', required=True)
def eval(model_path, model_type, data_path, output_dir, test_start_date, test_end_date):
    data = pd.read_csv(data_path)
    data['ds'] = pd.to_datetime(data['ds'])
    
    if test_start_date:
        data = data[data['ds'] >= test_start_date]
    if test_end_date:
        data = data[data['ds'] < test_end_date]
    
    train_.eval(data, model_type, model_path, output_dir)

@cli.command()
@click.argument('model_path', type=click.Path(exists=True, dir_okay=False))
@click.argument('model_type')
@click.argument('data_path', type=click.Path(exists=True, dir_okay=False))
def infer(model_path, model_type, data_path):
    data = pd.read_csv(data_path)
    data['ds'] = pd.to_datetime(data['ds'])
    print(train_.infer(data, model_type, model_path))

@cli.command()
@click.argument('station')
@click.option('-o', '--output_path', required=True, type=click.Path(exists=False, dir_okay=False))
@click.option('-s', '--settings_path', required=True, type=click.Path(exists=True, dir_okay=False))
def gen_infer_template(station, output_path, settings_path):
    # FIXME: quickfix loads all data to finally keep only one line (example)    
    settings = utils.load_settings(settings_path)

    station_metadata = settings_.STATION_METADATA[station]

    dfs = load.load_all_by_station_metadata(station_metadata)
    
    preprocess_.preprocess(
        dfs, station_lag_days=settings.STATION_LAG_DAYS, weather_lag_days=settings.WEATHER_LAG_DAYS
    ).iloc[:1,:].to_csv(output_path, index=False)


if __name__ == '__main__':
    cli()
