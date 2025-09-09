import click

from flood_forecaster.alert_module import main as alert_main


@click.group()
def cli():
    """
    Run the flood alert main process with no parameters
    """
    pass


@click.command()
def run_alert():
    """Run the flood alert main process with no parameters."""
    alert_main.main()
