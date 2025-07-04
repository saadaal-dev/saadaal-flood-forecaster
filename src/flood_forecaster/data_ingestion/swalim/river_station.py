import csv
from typing import List

from src.flood_forecaster.data_ingestion.openmeteo.station import Station

class RiverStation(Station):
    def __init__(self, id: int, name: str, latitude: float, longitude: float, region: str, district: str, moderate_threshold: float, high_threshold: float, full_threshold: float = 0.0):
        super().__init__(id, name, latitude, longitude)
        self.moderate_threshold = moderate_threshold
        self.high_threshold = high_threshold
        self.full_threshold = full_threshold
        self.region = region
        self.district = district

def get_river_stations(csv_path: str) -> List[RiverStation]:
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
