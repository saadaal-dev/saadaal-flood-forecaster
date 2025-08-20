from dataclasses import dataclass


@dataclass
class Station:
    id: int
    name: str
    latitude: float
    longitude: float

    def __str__(self):
        return f"Station [{self.id}]: {self.name}, Latitude: {self.latitude}, Longitude: {self.longitude}"
