"""
Common methods for cli commands
"""

import click
import openmeteo_requests
import requests_cache
from retry_requests import retry

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


def create_openmeteo_client(
        expire_after: int = 3600,  # 1 hour cache
        retries: int = 5,
        backoff_factor: float = 0.2,
) -> openmeteo_requests.Client:
    """
    Create an Open-Meteo API client with caching and retry logic.
        :param expire_after: Cache expiration time in seconds (-1 = no expiration). Default is 3600 (1 hour).
        :param retries: Number of retry attempts for failed requests. Default is 5.
        :param backoff_factor: Backoff factor for retry attempts. Default is 0.2.
        :return: An Open-Meteo API client instance.
    """
    # Set up the Open-Meteo API client with cache and retry on error
    cache_session = requests_cache.CachedSession(".cache", expire_after=expire_after)
    retry_session = retry(cache_session, retries=retries, backoff_factor=backoff_factor)
    openmeteo = openmeteo_requests.Client(session=retry_session)
    return openmeteo
