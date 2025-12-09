"""
The CLI entry point
"""

import os

import click

from flood_forecaster.utils.logging_config import setup_logging
from flood_forecaster_cli.commands import (database_model, data_ingestion, ml, run_alert, run_risk_assessment)


@click.group(help="flood_forecaster client tool")
def cli():
    """
    Entrypoint
    """
    # Initialize logging and Sentry at CLI startup
    log_level = os.getenv('LOG_LEVEL', 'INFO')
    setup_logging(level=log_level)


cli.add_command(database_model)
cli.add_command(data_ingestion)
cli.add_command(ml, "ml")
cli.add_command(run_risk_assessment, "risk-assessment")
cli.add_command(run_alert, "alert")
# cli.add_command(config)


def main():
    """Main function for console_scripts entry point."""
    cli()


if __name__ == "__main__":
    cli()
