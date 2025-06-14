from datetime import datetime

import click

from src.flood_forecaster.utils.configuration import Config, DataOutputType
from src.flood_forecaster.utils import configuration
from src.flood_forecaster.ml_model.registry import MODEL_MANAGER_REGISTRY
from src.flood_forecaster.ml_model import api

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


# custom validation for click post-context initialization checks
def build_post_context_validation_command(validation_fn):
    class PostContextValidationCommand(click.Command):
        def make_context(self, *args, **kwargs):
            ctx = super(PostContextValidationCommand, self).make_context(*args, **kwargs)
            validation_fn(ctx)
            return ctx
    return PostContextValidationCommand


# custom validation for the station based on the config_path file
def validate_station(ctx):
    config = configuration.Config(ctx.params['config_path'])
    value = ctx.params['station']
    if value not in config.load_station_mapping():
        raise click.BadParameter(f"Station {value} not supported. Supported stations: {list(configuration.STATION_MAPPING.keys())}")
    return value


@click.group()
def cli():
    """
    Commands for modelling and forecasting

    NOTE: forecast_days is the number of days to look ahead for the forecast.
          A different forecast_days value requires a different model.
          forecast_days=1 means the model will predict today's river level.
    """
    pass


@cli.command(cls=build_post_context_validation_command(validate_station))
@click.argument('station')
@click.argument('config_path', type=click.Path(exists=True, dir_okay=False), default=configuration.DEFAULT_CONFIG_FILE_PATH)
@click.option('-f', '--forecast_days', type=click.IntRange(1, None), default=None)
def preprocess(station, config_path, forecast_days):
    config = Config(config_path)
    api.preprocess(station, config, forecast_days)


@cli.command()
@click.argument('config_path', type=click.Path(exists=True, dir_okay=False), default=configuration.DEFAULT_CONFIG_FILE_PATH)
@click.option('-f', '--forecast_days', type=click.IntRange(1, None), default=None)
def analyze(config_path, forecast_days):
    config = Config(config_path)
    api.analyze(config, forecast_days)


@cli.command(cls=build_post_context_validation_command(validate_station))
@click.argument('station')
@click.argument('config_path', type=click.Path(exists=True, dir_okay=False), default=configuration.DEFAULT_CONFIG_FILE_PATH)
@click.option('-f', '--forecast_days', type=click.IntRange(1, None), default=None)
def split(station, config_path, forecast_days):
    config = Config(config_path)
    api.split(station, config, forecast_days)


@cli.command(cls=build_post_context_validation_command(validate_station))
@click.argument('station')
@click.argument('config_path', type=click.Path(exists=True, dir_okay=False), default=configuration.DEFAULT_CONFIG_FILE_PATH)
@click.option('-f', '--forecast_days', type=click.IntRange(1, None), default=None)
@click.option('-m', '--model_type', type=click.Choice(MODEL_MANAGER_REGISTRY.keys()), default=None)
def train(station, config_path, forecast_days, model_type):
    config = Config(config_path)
    api.train(station, config, forecast_days, model_type)


@cli.command(cls=build_post_context_validation_command(validate_station))
@click.argument('station')
@click.argument('config_path', type=click.Path(exists=True, dir_okay=False), default=configuration.DEFAULT_CONFIG_FILE_PATH)
@click.option('-f', '--forecast_days', type=click.IntRange(1, None), default=None)
@click.option('-m', '--model_type', type=click.Choice(MODEL_MANAGER_REGISTRY.keys()), default=None)
def eval(station, config_path, forecast_days, model_type):
    config = Config(config_path)
    api.eval(station, config, forecast_days, model_type)


# Command to run the preprocessing, analysis, split, training and evaluation steps
@cli.command(cls=build_post_context_validation_command(validate_station))
@click.argument('station')
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
    config = Config(config_path)
    api.preprocess(station, config, forecast_days)
    api.analyze(config, forecast_days)
    api.split(station, config, forecast_days)
    api.train(station, config, forecast_days, model_type)
    api.eval(station, config, forecast_days, model_type)


@cli.command(cls=build_post_context_validation_command(validate_station))
@click.argument('station')
@click.argument('config_path', type=click.Path(exists=True, dir_okay=False), default=configuration.DEFAULT_CONFIG_FILE_PATH)
@click.option('-f', '--forecast_days', type=click.IntRange(1, None), default=None)
@click.option('-d', '--date', type=click.DateTime(formats=["%Y-%m-%d"]), default=None)
@click.option('-m', '--model_type', type=click.Choice(MODEL_MANAGER_REGISTRY.keys()), default=None)
@click.option('-o', '--output_type', type=click.Choice(['stdout', 'database']), default='stdout')
def infer(station, config_path, forecast_days, date, model_type, output_type):
    """
    Predict the river level on a specific date+forcast_days-1 using the specified model type.
    The date is the reference date for the forecast is executed.
    The forecast_days parameter indicates how many days ahead the model should predict (1=today).
    """
    # DATABASE mode is supported only if the date is not provided
    # Reasoning: the date stored in the DB is a timestamp associated to the moment the prediction is made.
    #            If the date is provided, it is assumed to be the date for which the prediction is made.
    output_type = DataOutputType.from_string(output_type)
    if output_type == DataOutputType.DATABASE and date is not None:
        raise ValueError("DATABASE output type is supported only when date is not provided. Please use STDOUT or other output types.")

    # If date is not provided, use the current datetime
    # Will be used as the reference date for the forecast
    if date is None:
        date = datetime.now()

    # QUICKFIX: access the ConfigParser object directly
    config = configuration.Config(config_path)
    api.infer(station, config, forecast_days, date, model_type, output_type)


@cli.command()
def list_models():
    print("Supported model types:")
    for model_key in MODEL_MANAGER_REGISTRY.keys():
        print(" - " + model_key)
