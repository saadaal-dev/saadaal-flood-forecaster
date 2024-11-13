class Station:
    def __init__(self, id: int, name: str, latitude: float, longitude: float):
        self.id = id
        self.name = name
        self.latitude = latitude
        self.longitude = longitude

    def __str__(self):
        return f"Station [{self.id}]: {self.name}, Latitude: {self.latitude}, Longitude: {self.longitude}"
