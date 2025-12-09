import itertools
from datetime import datetime
from typing import List

import click

from flood_forecaster.ml_model import api
from flood_forecaster.ml_model.registry import MODEL_MANAGER_REGISTRY
from flood_forecaster.utils import configuration
from flood_forecaster.utils.configuration import Config, DataOutputType

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


def __get_stations(config: Config) -> List[str]:
    """
    Get the list of stations.
    The configuration is used to resolve the station mapping.
    :param config: The configuration object.
    :return: A list of station names.
    """
    station_mapping = config.load_station_mapping()
    return list(station_mapping.keys())


# custom validation for the station based on the config_path file
def validate_station(ctx):
    config = configuration.Config(ctx.params['config_path'])
    value = ctx.params['station']
    station_mapping = config.load_station_mapping()
    if value not in station_mapping:
        raise click.BadParameter(f"Station {value} not supported. Supported stations: {list(station_mapping.keys())}")
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
@click.option('-m', '--model_type', type=click.Choice(list(MODEL_MANAGER_REGISTRY.keys())), default=None)
def train(station, config_path, forecast_days, model_type):
    config = Config(config_path)
    api.train(station, config, forecast_days, model_type)


@cli.command(cls=build_post_context_validation_command(validate_station))
@click.argument('station')
@click.argument('config_path', type=click.Path(exists=True, dir_okay=False), default=configuration.DEFAULT_CONFIG_FILE_PATH)
@click.option('-f', '--forecast_days', type=click.IntRange(1, None), default=None)
@click.option('-m', '--model_type', type=click.Choice(list(MODEL_MANAGER_REGISTRY.keys())), default=None)
def eval(station, config_path, forecast_days, model_type):
    config = Config(config_path)
    api.eval(station, config, forecast_days, model_type)


# Command to run the preprocessing, analysis, split, training and evaluation steps
@cli.command(cls=build_post_context_validation_command(validate_station))
@click.argument('station')
@click.argument('config_path', type=click.Path(exists=True, dir_okay=False), default=configuration.DEFAULT_CONFIG_FILE_PATH)
@click.option('-f', '--forecast_days', type=click.IntRange(1, None), default=None)
@click.option('-m', '--model_type', type=click.Choice(list(MODEL_MANAGER_REGISTRY.keys())), default=None)
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
@click.option('-m', '--model_type', type=click.Choice(list(MODEL_MANAGER_REGISTRY.keys())), default=None)
@click.option('-o', '--output_type', type=click.Choice(['stdout', 'database']), default='stdout')
def infer(station, config_path, forecast_days, date, model_type, output_type):
    """
    Predict the river level on a specific date+forcast_days-1 using the specified model type.
    The date is the reference date for the forecast is executed.
    The forecast_days parameter indicates how many days ahead the model should predict (1=today).
    """
    # DATABASE mode has limitations if the date is not provided
    # Reasoning: the date stored in the DB is a timestamp associated to the moment the prediction is made.
    #            If the date is provided, it is assumed to be the date for which the prediction is made.
    output_type = DataOutputType.from_string(output_type)
    if output_type == DataOutputType.DATABASE and date is not None:
        click.echo(
            "WARNING: date in DATABASE won't contain the time component, only the date part. This can generate misleading data.")

    # If date is not provided, use the current datetime
    # Will be used as the reference date for the forecast
    if date is None:
        date = datetime.now()

    # QUICKFIX: access the ConfigParser object directly
    config = configuration.Config(config_path)
    api.infer(station, config, forecast_days, date, model_type, output_type)


@cli.command()
@click.argument('stations', nargs=-1)
@click.option('-f', '--forecast_days', type=click.IntRange(1, None), multiple=True, default=[1])
@click.option('-m', '--model_types', type=click.Choice(list(MODEL_MANAGER_REGISTRY.keys())), multiple=True, default=None)
@click.option('-c', '--config_path', type=click.Path(exists=True, dir_okay=False), default=configuration.DEFAULT_CONFIG_FILE_PATH)
@click.option('-o', '--output_type', type=click.Choice(['stdout', 'database']), default='stdout')
def bulk_infer(stations: List[str], forecast_days: List[int], model_types: List[str], config_path: str, output_type: str):
    """
    Bulk infer river levels for multiple stations and forecast days using specified model types.
    All possible combinations of stations, forecast_days and model_types are used.
    The results are printed to stdout or stored in the database, depending on the output_type.
    """
    config = configuration.Config(config_path)
    _output_type = DataOutputType.from_string(output_type)

    # FIXME: naive solution:
    # an insert will be made for each combination of station, forecast_days and model_type
    # NOTE: infer actually returns the predicted river level so we could externalize the database insert logic here
    for station, forecast_day, model_type in itertools.product(stations, forecast_days, model_types):
        click.echo(f"Running inference for station: {station}, forecast_days: {forecast_day}, model_type: {model_type}")
        try:
            api.infer(station, config, forecast_day, None, model_type, _output_type)
        except Exception as e:
            click.echo(
                f"Error during inference for station {station}, forecast_days {forecast_day}, model_type {model_type}: {e}")


@cli.command()
def list_model_types():
    click.echo("Supported model types:")
    for model_key in MODEL_MANAGER_REGISTRY.keys():
        click.echo(" - " + model_key)


@cli.command()
@click.option('-c', '--config_path', type=click.Path(exists=True, dir_okay=False), default=configuration.DEFAULT_CONFIG_FILE_PATH)
def list_stations(config_path):
    """
    List all supported stations based on the configuration file.
    """
    config = Config(config_path)
    stations = __get_stations(config)
    click.echo("Supported stations:")
    for station in stations:
        click.echo(" - " + station)


@cli.command()
@click.option('-c', '--config_path', type=click.Path(exists=True, dir_okay=False), default=configuration.DEFAULT_CONFIG_FILE_PATH)
def list_models(config_path):
    """
    List all available pretrained models.
    """
    config = Config(config_path)
    model_path = config.load_model_config().get("model_path", None)

    if model_path is None:
        click.echo("No model path configured. Please check your configuration file.")
        return

    click.echo("Available pretrained models:")
    model_params = api.list_model_params_from_model_path(model_path)

    # QICKFIX: replace forecast_days=None with * to make more explicit the wildcard
    model_params += [
        (t[0], "*", t[2], t[3])
        for t in api.list_available_dummy_model_params(config)
    ]

    if not model_params:
        click.echo("No pretrained models found.")
        return
    
    # sort models by station, forecast_days and model_type
    model_params.sort(key=lambda x: (x[3], x[1], x[2]))

    for preprocessor_type, forecast_days, model_type, station in model_params:
        click.echo(f" - Station: \"{station}\", Forecast Days: {forecast_days}, Model Type: {model_type}")
