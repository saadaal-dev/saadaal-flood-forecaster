import csv
from typing import List

from src.flood_forecaster.data_model.station import Station


# TODO replace with read from data_model RiverStationMetadata
class RiverStation(Station):
    def __init__(self, id: int, name: str, latitude: float, longitude: float, region: str, district: str, moderate_threshold: float, high_threshold: float, full_threshold: float = 0.0):
        super().__init__(id, name, latitude, longitude)
        self.moderate_threshold = moderate_threshold
        self.high_threshold = high_threshold
        self.full_threshold = full_threshold
        self.region = region
        self.district = district


def get_river_stations_static(config) -> List[RiverStation]:
    """
    Get river station metadata from the static data CSV file.

    :param config: Configuration object containing the path to the CSV file.
    :return: List of RiverStation objects with metadata.
    """
    data_static_config = config.load_static_data_config()
    csv_path = data_static_config['river_stations_metadata_path']
    with open(csv_path, mode="r", newline="") as location_file:
        reader = csv.reader(location_file)
        stations: List[RiverStation] = []
        next(reader, None)  # skip the headers
        for row in reader:
            station = RiverStation(
                id=int(row[0]),
                name=row[1],
                latitude=float(row[3]),
                longitude=float(row[4]),
                region=row[5],
                district=row[6],
                moderate_threshold=float(row[7]),
                high_threshold=float(row[8]),
                full_threshold=float(row[9])
            )
            stations.append(station)
        return stations


# TODO replace from db read
def get_river_station_names(config):
    river_stations = get_river_stations_static(config)
    return [station.name for station in river_stations]


def get_river_station_metadata(config, station) -> RiverStation:
    """
    Get river station metadata for a specific station.

    :param config: Configuration object containing the path to the CSV file.
    :param station: Name of the river station.
    :return: RiverStation object with metadata.
    """
    river_stations = get_river_stations_static(config)
    for river_station in river_stations:
        if river_station.name == station:
            return river_station
    raise ValueError(f"River station {station} not found in the static data file.")
