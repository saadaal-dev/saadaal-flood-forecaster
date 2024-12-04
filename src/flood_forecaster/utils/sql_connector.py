import os

from sqlalchemy import create_engine
from sqlalchemy.engine import URL

POSTGRES_PASSWORD = os.environ["POSTGRES_PASSWORD"]

class DatabaseConnection:
    def __init__(self, dbname, user, host, port, pwd = POSTGRES_PASSWORD) -> None:
        self.dbname=dbname
        self.user=user
        self.password=pwd
        self.host=host
        self.port=port
    
        url = URL.create(
            drivername="postgresql",
            username=self.user,
            host=self.host,
            database=self.dbname
            )

        self.engine = create_engine(url)