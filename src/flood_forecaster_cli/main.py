"""
The CLI entry point
"""

import click

from flood_forecaster_cli.commands.database_model import database_model


@click.group(help="flood_forecaster client tool")
def cli():
    """
    Entrypoint
    """


cli.add_command(database_model)
# cli.add_command(data_ingestion)
# cli.add_command(ml)


if __name__ == "__main__":
    cli()
