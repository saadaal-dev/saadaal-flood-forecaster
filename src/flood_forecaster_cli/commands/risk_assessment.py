import click

from src.flood_forecaster.risk_assessment.risk_assessment import main


@click.command()
def run_risk_assessment():
    """Run the flood risk assessment main process with no parameters."""
    main()
