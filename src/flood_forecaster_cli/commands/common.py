"""
Common methods for cli commands
"""

import click
from flood_forecaster.utils.configuration import Config


def common_options(function):
    """
    Reads the configuration based on --config-file
    if not set, it takes the default file
    """

    @click.option(
        "--configfile",
        "-c",
        required=False,
        default="../../config/config.ini",
        help="File with configuration",
    )
    def updated_func(*args, **kwargs):
        configfile = kwargs["configfile"]
        configuration = Config(configfile)
        kwargs["configuration"] = configuration

        # Remove unneed function parameters
        del kwargs["configfile"]

        function(*args, **kwargs)

    return updated_func
