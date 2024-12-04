import configparser
import os

CONFIG_FILE_PATH = os.path.dirname(os.path.realpath(__file__)) + "/../../../config.ini"

def read_config():
    config = configparser.ConfigParser()
    config.read(CONFIG_FILE_PATH)
    return config

def load_database_config():
    config = read_config()
    return config["database"]

def load_openmeteo_config():
    config = read_config()
    return config["openmeteo"]