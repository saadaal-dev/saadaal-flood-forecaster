import configparser
import json
import os
from configparser import ConfigParser, ExtendedInterpolation
from enum import Enum
from pathlib import Path

from flood_forecaster.data_model.weather import StationMapping

# Find the project root by looking for key files
def _find_project_root():
    """Find the project root directory by looking for characteristic files."""
    current_path = Path(__file__).resolve()
    
    # Look for project root markers
    for parent in current_path.parents:
        if (parent / "config" / "config.ini").exists():
            return parent / "config" / "config.ini"

    # Fallback to relative path from current file location
    fallback_path = os.path.dirname(os.path.realpath(__file__)) + "/../../../config/config.ini"
    return fallback_path

DEFAULT_CONFIG_FILE_PATH = str(_find_project_root())


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


# Output type
class DataOutputType(Enum):
    STDOUT = "stdout"
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

    def load_river_data_config(self):
        return dict(self._config.items("river_data"))

    def load_static_data_config(self):
        return dict(self._config.items("data.static"))

    def load_model_config(self):
        return dict(self._config.items("model"))

    def load_mailjet_config(self):
        return dict(self._config.items("mailjet_config"))

    def load_station_mapping(self):
        return _load_json_station_mapping(self._config.get("data.static", "river_stations_mapping_path"))

    def get_data_source_type(self) -> DataSourceType:
        return DataSourceType.from_string(self._config.get("data", "data_source"))

    def get_store_base_path(self):
        return self._config.get("openmeteo", "store_base_path")

    def get_openmeteo_api_url(self):
        return self._config.get("openmeteo", "api_url")

    def get_openmeteo_api_archive_url(self):
        return self._config.get("openmeteo", "api_archive_url")

    def get_weather_location_metadata_path(self):
        return self.load_static_data_config()["weather_location_data_path"]

    def use_database_weather(self) -> bool:
        return self._config.get("data.ingestion", "use_database", fallback="false").lower() == "true"

    @staticmethod
    def _load_config(config_file_path: str) -> configparser.ConfigParser:
        """
        Load configuration from the given file path.

        :param config_file_path: Path to the configuration file
        :return: ConfigParser object
        """
        if not os.path.exists(config_file_path):
            raise FileNotFoundError(f"Config file '{config_file_path}' not found.")

        config = configparser.ConfigParser(interpolation=ExtendedInterpolation())
        config.read(config_file_path)
        return config


def _load_json_station_mapping(path) -> dict[str, StationMapping]:
    with open(path, "r") as f:
        d = json.load(f)
        for k, v in d.items():
            d[k] = StationMapping(**v)
        return d
