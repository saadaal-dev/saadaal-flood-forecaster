from unittest import TestCase

from src.flood_forecaster.utils.configuration import Config
from src.flood_forecaster.utils.database_helper import DatabaseConnection

CONFIG_FILE_PATH = "../../../config/config.ini"


class Test(TestCase):
    def test_database_connection(self):
        conf = Config(CONFIG_FILE_PATH)
        db = DatabaseConnection(conf, "password")
        self.assertEquals(db.port, 5432)
