import click
from src.flood_forecaster.alert_module import main as alert_main

@click.command()
def run_alert():
    """Run the flood alert main process with no parameters."""
    alert_main.main()
    
    