import configparser
import json
import os
from configparser import ConfigParser
from dataclasses import dataclass
from enum import Enum
from typing import List

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

    def get_database_config(self):
        return dict(self._config.items("database"))
    
    def load_data_config(self):
        return dict(self._config.items("data"))

    def load_data_csv_config(self):
        return dict(self._config.items("data.csv"))

    def load_data_database_config(self):
        return dict(self._config.items("data.database"))

    def get_openmeteo_config(self):
        return dict(self._config.items("openmeteo"))

    def load_static_data_config(self):
        return dict(self._config.items("data.static"))

    def load_model_config(self):
        return dict(self._config.items("model"))

    def load_station_mapping(self):
        data_path = self.load_data_config()["data_path"]
        return load_station_mapping(data_path + self._config.get("data.static", "river_stations_mapping_path"))

    def get_data_source_type(self) -> DataSourceType:
        return DataSourceType.from_string(self._config.get("data", "data_source"))

    def get_swalim_config(self):
        return dict(self._config.items("swalim"))
    
    def get_store_base_path(self):
        return self._config.get("openmeteo", "store_base_path")
    
    def get_openmeteo_api_url(self):
        return self._config.get("openmeteo", "api_url")
    
    def get_openmeteo_api_archive_url(self):
        return self._config.get("openmeteo", "api_archive_url")
    
    def get_station_metadata_path(self):
        return self._config.get("data.ingestion", "river_stations_metadata_path")
    
    def get_district_data_path(self):
        return self._config.get("data.ingestion", "district_data_file")
    
    def get_station_data__path(self):
        return self._config.get("data.ingestion", "station_data_file")
    
    def get_use_database(self):
        return self._config.get("data.ingestion", "use_database")
    def get_river_data_config(self):
        return dict(self._config.items("river_data"))


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


# TODO move to data_model or weather module
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
