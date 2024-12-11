import configparser
from dataclasses import dataclass
import json
import os
from typing import List
from configparser import ConfigParser
from enum import Enum


DEFAULT_CONFIG_FILE_PATH = os.path.dirname(os.path.realpath(__file__)) + "/../../../config/config.ini"


class DataSourceType(Enum):
    CSV = "csv"
    DATABASE = "database"

    @classmethod
    def from_string(cls, source_type: str):
        source_type = source_type.strip().lower()
        for item in cls:
            if item.value == source_type:
                return item
        raise ValueError(f"Unsupported data source type: {source_type}")


class Config:
    def __init__(self, config_file_path: str) -> None:
        self._config: ConfigParser = self._load_config(config_file_path)

    def load_data_config(self):
        return dict(self._config.items("data"))
    
    def load_data_csv_config(self):
        return dict(self._config.items("data.csv"))

    def load_data_database_config(self):
        return dict(self._config.items("data.database"))

    def load_openmeteo_config(self):
        return dict(self._config.items("openmeteo"))
    
    def load_static_data_config(self):
        return dict(self._config.items("static-data"))
    
    def load_model_config(self):
        return dict(self._config.items("model"))
    
    def load_station_mapping(self):
        return load_station_mapping(self._config.get("static-data", "river_stations_mapping_path"))
    
    def get_data_source_type(self) -> DataSourceType:
        return DataSourceType.from_string(self._config.get("data", "data_source"))


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
