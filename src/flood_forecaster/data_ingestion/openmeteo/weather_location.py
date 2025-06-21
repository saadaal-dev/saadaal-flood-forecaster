import csv
from typing import List

from src.flood_forecaster.data_model.weather import WeatherLocation


def get_weather_locations(csv_path: str) -> List[WeatherLocation]:
    with open(csv_path, mode="r", newline="") as location_file:
        reader = csv.reader(location_file)
        locations: List[WeatherLocation] = []
        next(reader, None)  # skip the headers
        for row in reader:
            location = WeatherLocation(
                label=row[0],
                region=row[1],
                district=row[2],
                latitude=float(row[3]),
                longitude=float(row[4]),
                remarks=row[5]
            )
            locations.append(location)
        return locations