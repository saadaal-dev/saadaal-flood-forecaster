from typing import List

import pandas as pd
import requests
from bs4 import BeautifulSoup

from src.flood_forecaster.data_model.river_level import HistoricalRiverLevel
from src.flood_forecaster.utils.configuration import Config


def fetch_latest_river_data(config: Config) -> List[HistoricalRiverLevel]:
    """
    Fetches the latest river data from the SWALIM website
    :param config:
    :return: list of HistoricalRiverLevel objects with the latest river data
    """
    url = config.get_swalim_config().get("river_level_api_url")
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
    river_stations = get_river_stations(config)  # TODO check if already in Thierry's code

    new_level_data = []
    for station in river_stations:
        # find in df the only row where station name is equal to station.name
        row_df = df[df["Station"].astype(str) == station.name].head()

        station_level = HistoricalRiverLevel(
            location_name=station.name,
            date=pd.to_datetime(row_df["Date"], format="%d-%m-%Y").dt.date,
            level_m=pd.to_numeric(row_df["Observed River Level (m)"], errors="coerce"),
            station_number=station.name  # TODO: add station number to station class and metadata csv file
            # TODO delete station_number from HistoricalRiverLevel????
        )
        new_level_data.append(station_level)
    return new_level_data


def get_river_stations(config):
    # Get the station metadata from the config
    station_metadata_path = config.get_station_metadata_path()
    # Read the station metadata csv file
    river_stations = pd.read_csv(station_metadata_path, usecols=["station_name"])
    return river_stations


# Insert river data into database
def insert_river_data():
    # TODO: Implement this function
    pass

# Gets river data from database to pandas df -> in load.py
