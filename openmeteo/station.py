import csv


class Station:
    def __init__(self, id: int, name: str, latitude: float, longitude: float):
        self.id = id
        self.name = name
        self.latitude = latitude
        self.longitude = longitude

    def __str__(self):
        return f"Station [{self.id}]: {self.name}, Latitude: {self.latitude}, Longitude: {self.longitude}"


def get_stations(csv_path: str) -> list[Station]:
    with open(csv_path, mode="r", newline="") as location_file:
        reader = csv.reader(location_file)
        stations: list[Station] = []
        next(reader, None)  # skip the headers
        for row in reader:
            station = Station(
                id=int(row[0]),
                name=row[1],
                latitude=float(row[3]),
                longitude=float(row[4]),
            )
            print(station)
            stations.append(station)
        return stations
