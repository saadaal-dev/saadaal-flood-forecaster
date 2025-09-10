"""
Common methods for cli commands
"""

import click
from src.flood_forecaster.utils.configuration import Config


def common_options(function):
    """
    Reads the configuration based on --config-file
    if not set, it takes the default file
    """

    @click.option(
        "--configfile",
        "-c",
        required=False,
        default="./config/config.ini",
        help="File with the configuration",
    )
    def updated_func(*args, **kwargs):
        configfile = kwargs["configfile"]
        configuration = Config(configfile)
        kwargs["configuration"] = configuration

        # Remove unneeded function parameters
        del kwargs["configfile"]

        function(*args, **kwargs)

    return updated_func
