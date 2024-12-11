from datetime import datetime

import click

from ..utils import configuration
from .registry import MODEL_MANAGER_REGISTRY
from . import api

"""
Supports the following commands:
- preprocess(station, config_path, forecast_days), to prepare the data for modellization
- analyze(config_path, forecast_days), to analyze the data and provide insights
- split(station, config_path, forecast_days), to split the data into training and testing sets
- train(station, config_path, forecast_days, model_type), to create the model
- eval(station, config_path, forecast_days, model_type), to test the model
- infer(station, config_path, forecast_days, date, model_type), to predict the river level for a given date
- build_model(station, config_path, forecast_days, model_type), to run the full model building pipeline
- list_models(), to list all supported model types
"""


@click.group()
def cli():
    pass


@cli.command()
@click.argument('station', type=click.Choice(configuration.STATION_MAPPING.keys()))
@click.argument('config_path', type=click.Path(exists=True, dir_okay=False), default=configuration.DEFAULT_CONFIG_FILE_PATH)
@click.option('-f', '--forecast_days', type=click.IntRange(1, None), default=None)
def preprocess(station, config_path, forecast_days):
    config = configuration.read_config(config_path)
    api.preprocess(station, config, forecast_days)


@cli.command()
@click.argument('config_path', type=click.Path(exists=True, dir_okay=False), default=configuration.DEFAULT_CONFIG_FILE_PATH)
@click.option('-f', '--forecast_days', type=click.IntRange(1, None), default=None)
def analyze(config_path, forecast_days):
    config = configuration.read_config(config_path)
    api.analyze(config, forecast_days)


@cli.command()
@click.argument('station', type=click.Choice(configuration.STATION_MAPPING.keys()))
@click.argument('config_path', type=click.Path(exists=True, dir_okay=False), default=configuration.DEFAULT_CONFIG_FILE_PATH)
@click.option('-f', '--forecast_days', type=click.IntRange(1, None), default=None)
def split(station, config_path, forecast_days):
    config = configuration.read_config(config_path)
    api.split(station, config, forecast_days)


@cli.command()
@click.argument('station', type=click.Choice(configuration.STATION_MAPPING.keys()))
@click.argument('config_path', type=click.Path(exists=True, dir_okay=False), default=configuration.DEFAULT_CONFIG_FILE_PATH)
@click.option('-f', '--forecast_days', type=click.IntRange(1, None), default=None)
@click.option('-m', '--model_type', type=click.Choice(MODEL_MANAGER_REGISTRY.keys()), default=None)
def train(station, config_path, forecast_days, model_type):
    config = configuration.read_config(config_path)
    api.train(station, config, forecast_days, model_type)


@cli.command()
@click.argument('station', type=click.Choice(configuration.STATION_MAPPING.keys()))
@click.argument('config_path', type=click.Path(exists=True, dir_okay=False), default=configuration.DEFAULT_CONFIG_FILE_PATH)
@click.option('-f', '--forecast_days', type=click.IntRange(1, None), default=None)
@click.option('-m', '--model_type', type=click.Choice(MODEL_MANAGER_REGISTRY.keys()), default=None)
def eval(station, config_path, forecast_days, model_type):
    config = configuration.read_config(config_path)
    api.eval(station, config, forecast_days, model_type)


# Command to run the preprocessing, analysis, split, training and evaluation steps
@cli.command()
@click.argument('station', type=click.Choice(configuration.STATION_MAPPING.keys()))
@click.argument('config_path', type=click.Path(exists=True, dir_okay=False), default=configuration.DEFAULT_CONFIG_FILE_PATH)
@click.option('-f', '--forecast_days', type=click.IntRange(1, None), default=None)
@click.option('-m', '--model_type', type=click.Choice(MODEL_MANAGER_REGISTRY.keys()), default=None)
def build_model(station, config_path, forecast_days, model_type):
    """
    Run the full model building pipeline.
    This includes the following steps:
    - Preprocessing
    - Analysis
    - Splitting
    - Training
    - Evaluation
    """
    config = configuration.read_config(config_path)
    api.preprocess(station, config, forecast_days)
    api.analyze(config, forecast_days)
    api.split(station, config, forecast_days)
    api.train(station, config, forecast_days, model_type)
    api.eval(station, config, forecast_days, model_type)


@cli.command()
@click.argument('station', type=click.Choice(configuration.STATION_MAPPING.keys()))
@click.argument('config_path', type=click.Path(exists=True, dir_okay=False), default=configuration.DEFAULT_CONFIG_FILE_PATH)
@click.option('-f', '--forecast_days', type=click.IntRange(1, None), default=None)
@click.option('-d', '--date', type=click.DateTime(formats=["%Y-%m-%d"]), default=datetime.now().date())
@click.option('-m', '--model_type', type=click.Choice(MODEL_MANAGER_REGISTRY.keys()), default=None)
def infer(station, config_path, forecast_days, date, model_type):
    # QUICKFIX: access the ConfigParser object directly
    config = configuration.Config(config_path)._config
    api.infer(station, config, forecast_days, date, model_type)


@cli.command()
def list_models():
    print("Supported model types:")
    for model_key in MODEL_MANAGER_REGISTRY.keys():
        print(" - " + model_key)
