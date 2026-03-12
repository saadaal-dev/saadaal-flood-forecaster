"""
Rainfall-based flood risk assessment for non-functional river monitoring stations.

Non-functional river stations lack operational water level sensors.
This module infers flood risk from nearby IoT sensor rainfall data using calibrated
daily (24 h) and multi-day (72 h) accumulation thresholds.

Sensor stations are associated with non-functional river stations via the
``sensor_stations`` field in data/static/station-mapping.json.  Only stations
present in that field are evaluated; all others are silently skipped.

Typical usage:
    from flood_forecaster.risk_assessment.rainfall_risk import assess_rainfall_flood_risk
    df = assess_rainfall_flood_risk(config)
"""
from datetime import date, datetime, timedelta
import json

import pandas as pd
from sqlalchemy import select

from flood_forecaster.data_model.sensor_readings import SensorReading
from flood_forecaster.utils.configuration import Config
from flood_forecaster.utils.database_helper import DatabaseConnection
from flood_forecaster.utils.logging_config import get_logger

logger = get_logger(__name__)

# ---------------------------------------------------------------------------
# Rainfall flood-risk thresholds (mm).
# Evaluated from highest to lowest severity; the first matching rule wins.
# Calibrated for the Shabelle and Juba basins in southern Somalia based on
# WFP/ICPAC East-Africa rainfall impact thresholds.
# ---------------------------------------------------------------------------
_THRESHOLDS = [
    # label       24 h (mm)   72 h (mm)
    ("full",        100.0,      300.0),
    ("high",         50.0,      150.0),
    ("moderate",     25.0,       75.0),
    ("low",          10.0,       25.0),
]

# Sentinel strings emitted by sensor firmware that represent "no reading".
_SENSOR_INVALID_VALUES = frozenset({"---", "", "null", "-999.99", "0", "0.0"})


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _clean_sensor_value(series: pd.Series) -> pd.Series:
    """Cast raw VARCHAR sensor values to float, replacing known invalid sentinels with NaN."""
    cleaned = series.str.strip().str.lower()
    cleaned = cleaned.where(~cleaned.isin(_SENSOR_INVALID_VALUES), other=float("nan"))
    numeric = pd.to_numeric(cleaned, errors="coerce")
    # Drop implausible negatives that indicate sensor error codes
    numeric = numeric.where(numeric >= -100, other=float("nan"))
    return numeric


def _classify_risk(rain_24h: float, rain_72h: float) -> str:
    """Return the highest matching risk level, or 'none' if below all thresholds."""
    for label, thr_24h, thr_72h in _THRESHOLDS:
        if rain_24h >= thr_24h or rain_72h >= thr_72h:
            return label
    return "none"


def _load_non_functional_with_sensors(config: Config) -> list:
    """
    Return metadata for non-functional river stations that have at least one
    sensor station configured in station-mapping.json.

    Each entry is a dict:
        {station_name, station_number, river, sensor_stations: list[str]}
    """
    static_cfg = config.load_static_data_config()

    metadata_path = static_cfg.get("river_stations_full_metadata_path")
    if not metadata_path:
        raise ValueError(
            "Missing 'river_stations_full_metadata_path' in [data.static] config. "
            "Expected key pointing to data/static/river_stations_metadata.csv."
        )

    mapping_path = static_cfg["river_stations_mapping_path"]
    with open(mapping_path) as fh:
        station_mapping = json.load(fh)

    meta_df = pd.read_csv(metadata_path)
    meta_df.columns = meta_df.columns.str.strip()

    results = []
    for _, row in meta_df.iterrows():
        if str(row.get("status", "")).strip() != "Non Functional":
            continue
        name = str(row["station_name"]).strip()
        sensor_stations = station_mapping.get(name, {}).get("sensor_stations", [])
        if not sensor_stations:
            logger.debug(
                f"Non-functional station '{name}' has no sensor_stations in mapping — skipping."
            )
            continue
        results.append({
            "station_name": name,
            "station_number": str(row["station_number"]).strip(),
            "river": str(row["river_name"]).strip(),
            "sensor_stations": sensor_stations,
        })

    return results


def _query_sensor_rainfall(
    config: Config,
    sensor_station_ids: list,
    date_begin: date,
    date_end: date,
) -> pd.DataFrame:
    """
    Query public.sensor_readings for daily-aggregated rainfall for a list of
    sensor station IDs.

    Returns a DataFrame with columns:
        station_id, date (Timestamp), precipitation_sum (mm), precipitation_hours
    """
    sensor_config = config.load_sensor_config()
    rainfall_keyword = sensor_config.get("rainfall_sensor_meaning", "Rainfall")

    _dt_begin = pd.Timestamp(date_begin).replace(hour=0, minute=0, second=0, microsecond=0)
    _dt_end = pd.Timestamp(date_end).replace(hour=23, minute=59, second=59, microsecond=0)

    stmt = (
        select(SensorReading)
        .where(SensorReading.station_id.in_(sensor_station_ids))
        .where(SensorReading.sensor_meaning.ilike(f"%{rainfall_keyword}%"))
        .where(SensorReading.reading_ts >= _dt_begin)
        .where(SensorReading.reading_ts <= _dt_end)
    )
    database = DatabaseConnection(config)
    df = pd.read_sql(stmt, database.engine)
    logger.info(f"Loaded {len(df)} raw sensor rainfall rows for stations {sensor_station_ids}")

    if df.empty:
        logger.warning(
            f"No sensor rainfall rows found for {sensor_station_ids} "
            f"between {date_begin} and {date_end}."
        )
        return pd.DataFrame(
            columns=["station_id", "date", "precipitation_sum", "precipitation_hours"]
        )

    df = df.copy()
    df["value_clean"] = _clean_sensor_value(df["value"])
    df = df.dropna(subset=["value_clean"]).copy()

    df["reading_ts"] = pd.to_datetime(df["reading_ts"], utc=True)
    df["date"] = pd.to_datetime(df["reading_ts"].dt.date)

    agg = (
        df.groupby(["station_id", "date"], as_index=False)
        .agg(
            precipitation_sum=("value_clean", "sum"),
            precipitation_hours=("value_clean", "count"),
        )
    )
    return agg


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def assess_rainfall_flood_risk(
    config: Config,
    assessment_date: date | None = None,
) -> pd.DataFrame:
    """
    Assess flood risk at non-functional river stations using nearby sensor rainfall.

    For each non-functional station whose station-mapping.json entry contains a
    ``sensor_stations`` list, this function:

    1. Queries public.sensor_readings for the 3 days preceding *assessment_date*.
    2. Computes the 24 h (last day) and 72 h (last 3 days) accumulated rainfall
       totals from the nearest IoT sensor station.
    3. Classifies the accumulated rainfall into a risk level using the thresholds
       defined in ``_THRESHOLDS`` (``none`` | ``low`` | ``moderate`` | ``high`` | ``full``).

    The result is returned as a pandas DataFrame — it is NOT written to the
    database; callers may persist it as needed.

    Returns a DataFrame with columns:
        station_name        river station name (e.g. "Afgoi")
        station_number      SWALIM station code (e.g. "SH006")
        river               river basin name (e.g. "Shabelle")
        sensor_station_id   IoT sensor providing the reading (e.g. "MOHADM_AFG")
        rainfall_24h_mm     rainfall total over the most recent 24 h (mm)
        rainfall_72h_mm     rainfall total over the most recent 72 h (mm)
        risk_level          "none" | "low" | "moderate" | "high" | "full"
        assessment_date     calendar date on which the assessment was run
    """
    if assessment_date is None:
        assessment_date = datetime.now().date()

    stations = _load_non_functional_with_sensors(config)
    if not stations:
        logger.info(
            "No non-functional stations with sensor coverage found — "
            "add 'sensor_stations' to station-mapping.json entries to enable rainfall risk."
        )
        return pd.DataFrame(columns=[
            "station_name", "station_number", "river", "sensor_station_id",
            "rainfall_24h_mm", "rainfall_72h_mm", "risk_level", "assessment_date",
        ])

    # Collect all unique sensor IDs to minimise DB round-trips
    all_sensor_ids = list({sid for s in stations for sid in s["sensor_stations"]})
    # Sensor readings have a ~1-day ingestion lag; query up to yesterday
    date_end = assessment_date - timedelta(days=1)
    date_begin = assessment_date - timedelta(days=3)

    logger.info(
        f"Querying rainfall for sensors {all_sensor_ids} "
        f"from {date_begin} to {date_end}"
    )
    rainfall_df = _query_sensor_rainfall(config, all_sensor_ids, date_begin, date_end)

    rows = []
    for station in stations:
        name = station["station_name"]
        for sensor_id in station["sensor_stations"]:
            sensor_data = rainfall_df[rainfall_df["station_id"] == sensor_id].copy()

            # 72 h total (all 3 available days)
            rain_72h = float(sensor_data["precipitation_sum"].sum()) if not sensor_data.empty else 0.0

            # 24 h total — only the most recent day in the window
            rain_24h = 0.0
            if not sensor_data.empty:
                latest_date = sensor_data["date"].max()
                rain_24h = float(
                    sensor_data.loc[
                        sensor_data["date"] == latest_date, "precipitation_sum"
                    ].sum()
                )

            risk = _classify_risk(rain_24h, rain_72h)
            logger.info(
                f"[{name} / {station['station_number']}] "
                f"sensor={sensor_id}  24h={rain_24h:.1f} mm  72h={rain_72h:.1f} mm  "
                f"→ risk={risk}"
            )

            rows.append({
                "station_name": name,
                "station_number": station["station_number"],
                "river": station["river"],
                "sensor_station_id": sensor_id,
                "rainfall_24h_mm": rain_24h,
                "rainfall_72h_mm": rain_72h,
                "risk_level": risk,
                "assessment_date": assessment_date,
            })

    return pd.DataFrame(rows)


def main() -> None:
    """Entry point: run rainfall flood risk assessment and log results."""
    config = Config(config_file_path="config/config.ini")
    result_df = assess_rainfall_flood_risk(config)

    if result_df.empty:
        logger.info(
            "Rainfall risk assessment produced no results — "
            "no non-functional stations with sensor coverage."
        )
        return

    for _, row in result_df.iterrows():
        logger.info(
            f"Rainfall risk  [{row['station_name']} / {row['station_number']}]  "
            f"risk_level={row['risk_level']}  "
            f"24h={row['rainfall_24h_mm']:.1f} mm  "
            f"72h={row['rainfall_72h_mm']:.1f} mm  "
            f"(sensor: {row['sensor_station_id']})"
        )
