import configparser
from dataclasses import dataclass
import json
import os
from typing import List
from configparser import ConfigParser


DEFAULT_CONFIG_FILE_PATH = os.path.dirname(os.path.realpath(__file__)) + "/../../../config/config.ini"


class Config:
    def __init__(self, config_file_path: str) -> None:
        self._config: ConfigParser = self._load_config(config_file_path)

    def load_database_config(self):
        return dict(self._config.items("database"))

    def load_openmeteo_config(self):
        return dict(self._config.items("openmeteo"))

    @staticmethod
    def _load_config(config_file_path: str) -> configparser.ConfigParser:
        """
        Load configuration from the given file path.

        :param config_file_path: Path to the configuration file
        :return: ConfigParser object
        """
        if not os.path.exists(config_file_path):
            raise FileNotFoundError(f"Config file '{config_file_path}' not found.")

        config = configparser.ConfigParser()
        config.read(config_file_path)
        return config


@dataclass
class StationMapping:
    """
    A data class to store metadata for a weather station.

    Attributes:
        location (str): The location of the weather station.
        river (str): The river associated with the weather station.
        upstream_stations (List[str]): A list of upstream stations related to the weather station.
        weather_conditions (List[str]): A list of weather conditions relevant to the weather station.
    """
    location: str
    river: str
    upstream_stations: List[str]
    weather_locations: List[str]


def load_station_mapping(path):
    with open(path, "r") as f:
        d = json.load(f)
        for k, v in d.items():
            d[k] = StationMapping(**v)
        return d


# QUICKFIX: load config file from default path, expose config object
CONFIG = Config(DEFAULT_CONFIG_FILE_PATH)._config

# TODO: move into Config class
STATION_MAPPING = load_station_mapping(CONFIG.get("static-data", "river_stations_mapping_path"))
