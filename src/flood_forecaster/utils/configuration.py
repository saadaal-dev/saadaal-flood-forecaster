import configparser
import os
from configparser import ConfigParser


class Config:
    def __init__(self, config_file_path: str) -> None:
        self._config: ConfigParser = self._load_config(config_file_path)

    def get_database_config(self):
        return dict(self._config.items("database"))

    def get_openmeteo_config(self):
        return dict(self._config.items("openmeteo"))

    def get_swalim_config(self):
        return dict(self._config.items("swalim"))

    def get_station_metadata_path(self):
        return (self._config.get("csv", "data_path") +
                self._config.get("csv", "station_metadata_path"))

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
