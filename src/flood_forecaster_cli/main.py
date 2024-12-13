"""
The CLI entry point
"""

import click

from flood_forecaster_cli.commands import (database_model, data_ingestion)


@click.group(help="flood_forecaster client tool")
def cli():
    """
    Entrypoint
    """


cli.add_command(database_model)
cli.add_command(data_ingestion)
# cli.add_command(ml)
# cli.add_command(config)


if __name__ == "__main__":
    cli()
