import configparser
import os
from configparser import ConfigParser


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
