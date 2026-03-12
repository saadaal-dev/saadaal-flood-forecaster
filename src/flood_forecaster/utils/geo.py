"""
Geospatial utilities for the flood forecaster pipeline.
"""
import math
from typing import Optional

import pandas as pd

from flood_forecaster.utils.logging_config import get_logger

logger = get_logger(__name__)


def haversine_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """
    Calculate the great-circle distance (km) between two points on Earth using the
    Haversine formula. Pure Python, no extra dependencies.

    :param lat1: Latitude of point 1 (degrees)
    :param lon1: Longitude of point 1 (degrees)
    :param lat2: Latitude of point 2 (degrees)
    :param lon2: Longitude of point 2 (degrees)
    :return: Distance in kilometres
    """
    R = 6371.0  # Earth's mean radius in km

    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)

    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2
    return 2 * R * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def build_sensor_location_mapping(
    sensor_stations_path: str,
    forecast_locations_path: str,
    max_distance_km: Optional[float] = None,
) -> dict:
    """
    Build a mapping from sensor station_id (as stored in public.sensor_readings) to the
    nearest pipeline location label (as used in WeatherDataFrameSchema / StationDataFrameSchema).

    Matching is done by nearest-neighbour haversine distance using the GPS coordinates in:
      - sensor_stations_path: data/static/sensor-stations.csv
            columns: sensor, label, latitude, longitude, type
            'label' corresponds to sensor_readings.station_id
      - forecast_locations_path: data/static/forecast-locations.csv
            columns: label, region, district, latitude, longitude, remarks
            'label' is the pipeline location key

    :param sensor_stations_path: Path to sensor-stations.csv
    :param forecast_locations_path: Path to forecast-locations.csv
    :param max_distance_km: If set, sensor stations further than this distance from any
                            forecast location are excluded from the mapping (returns warning).
    :return: dict mapping sensor station_id → nearest forecast location label
    """
    sensor_df = pd.read_csv(sensor_stations_path)
    sensor_df.columns = sensor_df.columns.str.strip()  # strip whitespace from column names

    forecast_df = pd.read_csv(forecast_locations_path)
    forecast_df.columns = forecast_df.columns.str.strip()

    # Deduplicate sensor stations — keep unique (label, latitude, longitude) rows.
    # The same label can appear multiple times with different sensor types (e.g. weather station
    # AND water level sensor at the same GPS position).
    sensor_df = sensor_df[["sensor", "label", "latitude", "longitude"]].drop_duplicates(subset=["label"])

    mapping: dict = {}
    for _, sensor_row in sensor_df.iterrows():
        station_label = str(sensor_row["label"]).strip()
        sensor_name = str(sensor_row["sensor"]).strip()
        s_lat, s_lon = sensor_row["latitude"], sensor_row["longitude"]

        best_loc_label: str | None = None
        best_dist = float("inf")

        for _, loc_row in forecast_df.iterrows():
            dist = haversine_distance(s_lat, s_lon, loc_row["latitude"], loc_row["longitude"])
            if dist < best_dist:
                best_dist = dist
                best_loc_label = loc_row["label"]

        if max_distance_km is not None and best_dist > max_distance_km:
            logger.warning(
                f"Sensor station '{station_label}' is {best_dist:.1f} km from the nearest "
                f"forecast location '{best_loc_label}' — exceeds max_distance_km={max_distance_km}. "
                f"Excluding from mapping."
            )
            continue

        logger.debug(f"Sensor '{station_label}' → location '{best_loc_label}' ({best_dist:.1f} km)")
        # Map both the device label (used as station_id in public.sensor_readings queries)
        # and the human-readable sensor name (convenient for CLI --location arguments).
        mapping[station_label] = best_loc_label
        if sensor_name and sensor_name != station_label:
            mapping[sensor_name] = best_loc_label

    return mapping


def map_sensors_to_non_functional_stations(
    sensor_stations_path: str,
    river_stations_metadata_path: str,
    max_distance_km: float = 50.0,
) -> dict:
    """
    Build a mapping from non-functional river station name to a list of nearby
    sensor station labels (as stored in public.sensor_readings station_id column).

    Only stations with status == "Non Functional" in river_stations_metadata.csv
    are considered.

    :param sensor_stations_path: Path to data/static/sensor-stations.csv
    :param river_stations_metadata_path: Path to data/static/river_stations_metadata.csv
    :param max_distance_km: Maximum distance (km) for a sensor to be considered nearby.
    :return: dict mapping river station name → list[str] of nearby sensor station labels
    """
    sensor_df = pd.read_csv(sensor_stations_path)
    sensor_df.columns = sensor_df.columns.str.strip()
    sensor_df = sensor_df[["sensor", "label", "latitude", "longitude"]].drop_duplicates(subset=["label"])

    meta_df = pd.read_csv(river_stations_metadata_path)
    meta_df.columns = meta_df.columns.str.strip()
    nf_df = meta_df[meta_df["status"].str.strip() == "Non Functional"].copy()
    nf_df["latitude"] = pd.to_numeric(nf_df["latitude"], errors="coerce")
    nf_df["longitude"] = pd.to_numeric(nf_df["longitude"], errors="coerce")
    nf_df = nf_df.dropna(subset=["latitude", "longitude"])

    result: dict = {}
    for _, rs_row in nf_df.iterrows():
        station_name = str(rs_row["station_name"]).strip()
        nearby: list = []
        for _, sensor_row in sensor_df.iterrows():
            dist = haversine_distance(
                rs_row["latitude"], rs_row["longitude"],
                sensor_row["latitude"], sensor_row["longitude"],
            )
            if dist <= max_distance_km:
                label = str(sensor_row["label"]).strip()
                logger.debug(
                    f"Non-functional station '{station_name}' ← sensor '{label}' ({dist:.1f} km)"
                )
                nearby.append(label)
        if nearby:
            result[station_name] = nearby
        else:
            logger.debug(
                f"Non-functional station '{station_name}': no sensor within {max_distance_km} km."
            )

    return result
