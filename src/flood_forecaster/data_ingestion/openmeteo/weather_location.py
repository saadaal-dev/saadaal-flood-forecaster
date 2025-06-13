import csv
from typing import List

class WeatherLocation:
    def __init__(self, label: str, region: str, district: str, latitude: float, longitude: float, remarks: str):
        self.label = label
        self.region = region
        self.district = district
        self.latitude = latitude
        self.longitude = longitude
        self.remarks = remarks

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