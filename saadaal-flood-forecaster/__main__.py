import click

from .flood_forecaster.ml_model import __main__ as ml_model_main


@click.group()
def cli():
    pass


cli.add_command(ml_model_main.cli, "ml")


if __name__ == '__main__':
    cli()
