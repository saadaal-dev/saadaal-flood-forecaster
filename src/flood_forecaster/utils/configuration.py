import configparser
import os

CONFIG_FILE_PATH = os.path.dirname(os.path.realpath(__file__)) + "/../../../config.ini"


def load_database_config(config_file_path: str):
    config = _load_config(config_file_path)
    return dict(config.items("database"))


def load_openmeteo_config(config_file_path: str):
    config = _load_config(config_file_path)
    return dict(config.items("openmeteo"))

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
