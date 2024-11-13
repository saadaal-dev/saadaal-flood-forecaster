import csv


class District:
    def __init__(self, region: str, name: str, latitude: float, longitude: float):
        self.region = region
        self.name = name
        self.latitude = latitude
        self.longitude = longitude

    def __str__(self):
        return f"District: {self.name}, Region: {self.region}, Latitude: {self.latitude}, Longitude: {self.longitude}"


def get_districts(csv_path: str) -> list[District]:
    with open(csv_path, mode="r", newline="") as location_file:
        reader = csv.reader(location_file)
        districts: list[District] = []
        next(reader, None)  # skip the headers
        for row in reader:
            district = District(
                region=row[0],
                name=row[1],
                latitude=float(row[2]),
                longitude=float(row[3]),
            )
            print(district)
            districts.append(district)
        return districts
