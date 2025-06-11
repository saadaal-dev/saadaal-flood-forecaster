import csv
from dataclasses import dataclass
from typing import List


@dataclass
class Station:
    id: int
    name: str
    latitude: float
    longitude: float
    region: str
    district: str
    moderate: float
    high: float
    full: float

    def __str__(self):
        return f"Station [{self.id}]: {self.name}, Latitude: {self.latitude}, Longitude: {self.longitude}"


def get_stations(csv_path: str) -> List[Station]:
    with open(csv_path, mode="r", newline="") as location_file:
        reader = csv.reader(location_file)
        stations: List[Station] = []
        next(reader, None)  # skip the headers
        for row in reader:
            station = Station(
                id=int(row[0]),
                name=row[1],
                latitude=float(row[3]),
                longitude=float(row[4]),
                region=row[5],
                district=row[6],
                moderate=float(row[7]),
                high=float(row[8]),
                full=float(row[9]),
            )
            stations.append(station)
        return stations
