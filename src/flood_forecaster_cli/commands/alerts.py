import click
from src.flood_forecaster.alert_module import main as alert_main

@click.command()
def run_alert():
    """Run the flood alert main process with no parameters."""
    alert_main.main()

# If you use a Click group, add:
# cli.add_command(run_alert)