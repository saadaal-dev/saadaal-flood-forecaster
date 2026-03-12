import click

from flood_forecaster.risk_assessment.rainfall_risk import main


@click.command()
def run_rainfall_risk_assessment():
    """Run rainfall-based flood risk assessment for non-functional river stations."""
    main()
