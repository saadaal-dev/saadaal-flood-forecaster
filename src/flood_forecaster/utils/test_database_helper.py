from unittest import TestCase

from src.flood_forecaster.utils.database_helper import DatabaseConnection


class Test(TestCase):
    def test_database_connection(self):
        db = DatabaseConnection("../../../config/config.ini")
        self.assertEquals(db.port, 5432)
