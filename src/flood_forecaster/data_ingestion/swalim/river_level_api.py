from typing import List

import pandas as pd
import requests
from bs4 import BeautifulSoup
from sqlalchemy.orm import Session

from src.flood_forecaster import DatabaseConnection
from src.flood_forecaster.data_ingestion.swalim.river_station import get_river_station_names
from src.flood_forecaster.data_model.river_level import HistoricalRiverLevel
from src.flood_forecaster.utils.configuration import Config


def fetch_latest_river_data(config: Config) -> List[HistoricalRiverLevel]:
    """
    Fetches the latest river data from the SWALIM website
    :param config:
    :return: list of HistoricalRiverLevel objects with the latest river data
    """
    url = config.get_river_data_config().get("swalim_api_url")
    try:
        response = requests.get(url)
        response.raise_for_status()

        # Parse the response: Dependent on the structure of the html
        parsed_response = BeautifulSoup(response.content, "html.parser")
        data_table = parsed_response.find("table", id="maps-data-grid")
        df = pd.read_html(str(data_table))[0]
        df = df.head(7)  # Get the 7 stations

        return _get_new_river_levels(config, df)

    except requests.exceptions.HTTPError as http_err:
        print(f"HTTP error occurred: {http_err}")
        print("Couldn't fetch the latest river data")

    except requests.exceptions.RequestException as err:
        print(f"Error occurred: {err}")
        print("Couldn't fetch the latest river data")

    return []


def _get_new_river_levels(config, df) -> List[HistoricalRiverLevel]:
    river_station_names = get_river_station_names(config)

    new_level_data = []
    for station in river_station_names:
        # find in df the only row where station name is equal to station
        row_list = df[df["Station"].astype(str) == station].head(1).to_dict(orient="records")
        if row_list:
            data_dict = row_list[0]
            station_level = HistoricalRiverLevel(
                location_name=station,
                date=pd.to_datetime(data_dict["Date"], format="%d-%m-%Y"),
                level_m=pd.to_numeric(data_dict["Observed River Level (m)"], errors="coerce"),
                station_number=station  # TODO: add station number to station class and metadata csv file
                # TODO delete station_number from HistoricalRiverLevel????
            )
            new_level_data.append(station_level)
    return new_level_data


# Insert river data into database
def insert_river_data(river_levels: List[HistoricalRiverLevel], config: Config):
    database_connection = DatabaseConnection(config)

    with database_connection.engine.connect() as conn:
        with Session(bind=conn) as session:
            session.add_all(river_levels)
            session.commit()
            print(f"Inserted {len(river_levels)} river levels into the database.")


# Gets river data from database to pandas df -> in load.py
