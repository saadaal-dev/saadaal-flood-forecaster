import click

from flood_forecaster.alert_module.alert import main


@click.group()
def cli():
    """
    Run the flood alert main process with no parameters
    """
    pass


@click.command()
def run_alert():
    """Run the flood alert main process with no parameters."""
    main()
