from collections import OrderedDict
from datetime import date, datetime
from typing import List, Optional

import pandas as pd
import pandera.pandas as pa
import requests
from bs4 import BeautifulSoup
from sqlalchemy import text
from sqlalchemy.orm import Session

from flood_forecaster import DatabaseConnection
from flood_forecaster.data_model.river_level import HistoricalRiverLevel, StationDataFrameSchema
from flood_forecaster.data_model.river_station import get_river_station_names, get_river_station_metadata
from flood_forecaster.utils.configuration import Config
from flood_forecaster.utils.logging_config import get_logger

logger = get_logger(__name__)

def fetch_latest_river_data(config: Config) -> List[HistoricalRiverLevel]:
    """
    Fetches the latest river data from the SWALIM website
    :param config:
    :return: list of HistoricalRiverLevel objects with the latest river data
    """
    url = config.load_river_data_config()["swalim_api_url"]
    try:
        response = requests.get(url, verify=False)
        response.raise_for_status()

        # Parse the response: Dependent on the structure of the html
        parsed_response = BeautifulSoup(response.content, "html.parser")
        data_table = parsed_response.find("table", id="maps-data-grid")
        df = pd.read_html(str(data_table))[0]
        df = df.head(7)  # Get the 7 stations

        # NOTE: station_number is not defined in the input HTML table
        # Ideally it should be resolved from the station name here.

        return _get_new_river_levels(config, df)

    except requests.exceptions.HTTPError as http_err:
        logger.error(f"HTTP error occurred: {http_err}")
        logger.error("Couldn't fetch the latest river data")

    except requests.exceptions.RequestException as err:
        logger.error(f"Error occurred: {err}")
        logger.error("Couldn't fetch the latest river data")

    logger.error("Error: No river data found")
    return []


def _get_new_river_levels(config, df) -> List[HistoricalRiverLevel]:
    river_station_names = get_river_station_names(config)

    new_level_data = []
    for station in river_station_names:
        # find in df the only row where station name is equal to station
        row_list = df[df["Station"].astype(str) == station].head(1).to_dict(orient="records")
        if row_list:
            data_dict = row_list[0]
            station_level = HistoricalRiverLevel(
                location_name=station,
                date=pd.to_datetime(data_dict["Date"], format="%d-%m-%Y"),
                level_m=pd.to_numeric(data_dict["Observed River Level (m)"], errors="coerce"),
                # NOTE: station_number is not defined in the input HTML table
                # TODO: station_number=resolve_station_number(data_dict["Station"]),
            )
            new_level_data.append(station_level)
    logger.debug(
        "Fetched latest river levels for stations: " + ", ".join([level.location_name for level in new_level_data]))
    return new_level_data


def _normalize_reading_date(value) -> Optional[date]:
    """
    Reduce any supported date representation to a calendar date.

    Callers supply a mix of `datetime.date`, `datetime.datetime` and
    `pandas.Timestamp`. Those never compare or hash equal to each other, so
    without normalization two representations of the same day look like two
    different days and slip past in-batch deduplication, only to collide in the
    database. `historical_river_level.date` is a DATE column, so the calendar day
    is the real key.
    """
    if value is None:
        return None
    if isinstance(value, pd.Timestamp):
        return value.date()
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    # Strings and numpy datetimes: let pandas do the parsing.
    parsed = pd.to_datetime(value, errors="coerce")
    return None if pd.isna(parsed) else parsed.date()


def _collapse_duplicate_levels(river_levels: List[HistoricalRiverLevel]) -> List[dict]:
    """
    Reduce a batch to at most one row per (location_name, date).

    `ON CONFLICT DO UPDATE` raises "cannot affect row a second time" if a single
    statement carries two rows with the same conflict key, so the batch has to be
    collapsed before it reaches the database.

    The rule is **the latest available measurement wins**: among the rows for one
    station-day, the last one carrying a reading is kept, and a NULL never displaces
    a reading that arrived earlier in the same batch.

        [4.70, NULL]        -> 4.70
        [4.70, 4.80, NULL]  -> 4.80
        [NULL, 4.70]        -> 4.70
        [4.80, 4.70, NULL]  -> 4.70   (latest reading, not the largest)
        [NULL, NULL]        -> NULL   (nothing was ever reported)

    Plain "last wins" would discard 4.70 in the first case. NULL means the reading
    was unavailable; it is not a measurement and it is not a retraction, so it must
    not outrank one. Expressing a genuine upstream retraction needs the
    representation DATA-010 will introduce; until then nothing in a batch can mean
    "delete the value I sent you a moment ago".

    This is the same preference applied at the other two layers, so all three now
    agree: `_river_level_upsert()` skips the UPDATE when the incoming level is NULL,
    and `remove_duplicates_historical_river_level_from_db()` ranks by
    `(level_m IS NOT NULL) DESC, id DESC`. Note it is recency among readings, not
    magnitude: the fourth example keeps 4.70 because it arrived after 4.80.

    Rows with no location or no usable date are dropped: they cannot be addressed by
    the uniqueness key.
    """
    collapsed: "OrderedDict[tuple, dict]" = OrderedDict()
    skipped = 0
    null_ignored = 0

    for level in river_levels:
        reading_date = _normalize_reading_date(level.date)
        if level.location_name is None or reading_date is None:
            skipped += 1
            continue

        key = (level.location_name, reading_date)
        level_m = None if pd.isna(level.level_m) else float(level.level_m)

        existing = collapsed.get(key)
        if existing is not None and level_m is None and existing["level_m"] is not None:
            # Keep the reading already seen for this station-day. Retains its
            # original position in the batch, since the entry is left untouched.
            null_ignored += 1
            continue

        collapsed[key] = {
            "location_name": level.location_name,
            "date": reading_date,
            "level_m": level_m,
        }

    if skipped:
        logger.warning(f"Skipped {skipped} river level(s) with no location name or no parsable date.")

    if null_ignored:
        logger.warning(
            f"Ignored {null_ignored} NULL river level(s) that would have displaced a reading "
            f"for the same station and date."
        )

    duplicates = len(river_levels) - skipped - len(collapsed)
    if duplicates > 0:
        logger.info(
            f"Collapsed {duplicates} duplicate (station, date) river level(s) within the batch; "
            f"latest available measurement wins."
        )

    return list(collapsed.values())


def _river_level_upsert(dialect_name: str, rows: List[dict]):
    """
    Build an INSERT ... ON CONFLICT (location_name, date) DO UPDATE for river levels.

    PostgreSQL is the production target; SQLite is supported so that the write
    path can be tested without a live server, the same way the RISK-006 alert
    regression tests do.

    A later reading replaces an earlier one for the same station and day. That is
    not an arbitrary choice: all nine conflicting (station, date) pairs in the
    2026-09-22 production snapshot were arbitrated against `public.station_river_data`
    and in every case the more recently ingested value was the correct one, three of
    them correcting a whole-metre transcription error. So a differing upstream value
    is treated as a correction, not as something to reject (DATA-005).

    The update is skipped when the incoming level is NULL, so a station that
    reports no reading cannot erase a reading already stored. NULL means "no usable
    reading" throughout the gap logic, and overwriting a real value with it would
    manufacture a gap (see DATA-010).
    """
    if dialect_name == "sqlite":
        from sqlalchemy.dialects.sqlite import insert as dialect_insert
    else:
        from sqlalchemy.dialects.postgresql import insert as dialect_insert

    statement = dialect_insert(HistoricalRiverLevel).values(rows)
    return statement.on_conflict_do_update(
        index_elements=["location_name", "date"],
        set_={"level_m": statement.excluded.level_m},
        where=statement.excluded.level_m.isnot(None),
    )


# Insert river data into database
def insert_river_data(river_levels: List[HistoricalRiverLevel], config: Config, avoid_duplicates: bool = True) -> int:
    """
    Upsert river levels, keyed on (location_name, date).

    Repeated runs over the same window are idempotent: an unchanged reading is a
    no-op and a changed reading updates in place. Before DATA-005 this function
    issued one SELECT per candidate row and then `add_all()`, which left a
    read-modify-write race and could not update a corrected value. The database
    now enforces uniqueness, so the guard is a single statement.

    :param river_levels: rows to store.
    :param config: configuration object.
    :param avoid_duplicates: deprecated and ignored. Duplicate suppression is no
        longer optional: `(location_name, date)` is enforced by the database.
    :return: number of rows written, counting inserts and updates.
    """
    if not avoid_duplicates:
        logger.warning(
            "insert_river_data(avoid_duplicates=False) is ignored: (location_name, date) "
            "uniqueness is enforced by the database. Duplicate rows can no longer be inserted."
        )

    rows = _collapse_duplicate_levels(river_levels)
    if not rows:
        logger.warning("No storable river levels in the batch; nothing to insert.")
        return 0

    database_connection = DatabaseConnection(config)

    with database_connection.engine.connect() as conn:
        with Session(bind=conn) as session:
            logger.debug(f"Upserting {len(rows)} river levels into the database...")
            result = session.execute(
                _river_level_upsert(session.bind.dialect.name, rows)
            )
            session.commit()

    written = result.rowcount if result.rowcount and result.rowcount > 0 else 0
    logger.info(
        f"Upserted {written} river level(s) into the database "
        f"({len(rows)} submitted after deduplication)."
    )
    return written


def remove_duplicates_historical_river_level_from_db(config: Config, dry_run: bool = True) -> int:
    """
    Collapse duplicate (location_name, date) rows in historical_river_level.

    Run this before applying `sql/add_historical_river_level_unique_constraint.sql`;
    the migration refuses to add the constraint while duplicates remain.

    Retention rule, in order: keep a row with a non-NULL `level_m` over a NULL one,
    then keep the highest `id`, i.e. the most recently ingested. The highest id was
    verified correct against `public.station_river_data` for all nine value-conflicting
    pairs in the 2026-09-22 snapshot. The non-NULL preference is a safety belt; no
    mixed NULL/real pair existed in that snapshot, but the rule must not be able to
    discard a real reading in favour of an empty one.

    :param config: configuration object.
    :param dry_run: when True, report what would be deleted and change nothing.
    :return: number of excess rows deleted, or that would be deleted in a dry run.
    """
    database_connection = DatabaseConnection(config)

    # Rank rows within each (location_name, date) group and keep rank 1.
    ranked = """
        SELECT id,
               location_name,
               date,
               level_m,
               ROW_NUMBER() OVER (
                   PARTITION BY location_name, date
                   ORDER BY (level_m IS NOT NULL) DESC, id DESC
               ) AS rn
        FROM flood_forecaster.historical_river_level
    """

    with database_connection.engine.connect() as conn:
        summary = conn.execute(text(f"""
            WITH ranked AS ({ranked})
            SELECT COUNT(*) AS excess_rows,
                   COUNT(DISTINCT (location_name, date)) AS affected_pairs
            FROM ranked WHERE rn > 1
        """)).fetchone()

        excess_rows, affected_pairs = (summary[0] or 0), (summary[1] or 0)

        if not excess_rows:
            logger.info("No duplicate (station, date) river levels found.")
            return 0

        logger.warning(
            f"Found {excess_rows} excess row(s) across {affected_pairs} duplicate (station, date) pair(s)."
        )

        # Report the pairs where the retained value actually differs from a discarded
        # one. These are the only cases where the retention rule changes a reading.
        conflicts = conn.execute(text(f"""
            WITH ranked AS ({ranked})
            SELECT location_name, date,
                   MAX(CASE WHEN rn = 1 THEN level_m END) AS kept,
                   MIN(level_m) AS lowest,
                   MAX(level_m) AS highest
            FROM ranked
            GROUP BY location_name, date
            HAVING COUNT(*) > 1 AND COUNT(DISTINCT level_m) > 1
            ORDER BY location_name, date
        """)).fetchall()

        if conflicts:
            logger.warning(
                f"{len(conflicts)} pair(s) hold conflicting values; keeping the most recently ingested:"
            )
            for row in conflicts:
                logger.warning(
                    f" - {row.location_name} {row.date}: keeping {row.kept} "
                    f"(range {row.lowest}..{row.highest})"
                )
        else:
            logger.info("All duplicate pairs agree on level_m; no reading changes value.")

        if dry_run:
            logger.info(f"Dry run: {excess_rows} row(s) would be deleted.")
            return excess_rows

        result = conn.execute(text(f"""
            DELETE FROM flood_forecaster.historical_river_level
            WHERE id IN (
                SELECT id FROM ({ranked}) ranked WHERE rn > 1
            )
        """))
        conn.commit()

        deleted = result.rowcount if result.rowcount and result.rowcount > 0 else 0
        logger.info(f"Deleted {deleted} duplicate river level row(s).")
        return deleted


def __load_snrfa_river_data(file_path: str, location_name: str) -> pa.typing.DataFrame[StationDataFrameSchema]:
    """
    Load river data from SNRFA CSV file into a pandas DataFrame.
    :param file_path: Path to the SNRFA CSV file.
    :param location_name: Name of the river location.
    :return: DataFrame containing the river data.
    """
    # header: id,date,station_number,level(m)
    df = pd.read_csv(file_path, parse_dates=["date"], date_format="%Y-%m-%d")
    df = df.rename(columns={"level(m)": "level__m"})

    df["location"] = location_name
    df = df[["date", "location", "level__m"]]
    df["level__m"] = df["level__m"].apply(pd.to_numeric, errors="coerce", downcast="float")
    df = df.dropna(subset=["level__m", "date"])

    return StationDataFrameSchema.validate(df)


def __load_swalim_river_data(file_path: str, location_name: str) -> pa.typing.DataFrame[StationDataFrameSchema]:
    """
    Load river data from SWALIM CSV file into a pandas DataFrame.
    :param file_path: Path to the SWALIM CSV file.
    :param location_name: Name of the river location (label).
    :return: DataFrame containing the river data.
    """
    # header: "date","bankfull","highfloodrisk","moderatefloodrisk","longtermmean","previousreadingvalue","readingvalue"
    # Where:
    # - date: Date of the observation in format "yyyy-mm-dd"
    # - bankfull: Bankfull level in meters
    # - highfloodrisk: High flood risk level in meters
    # - moderatefloodrisk: Moderate flood risk level in meters
    # - longtermmean: Long-term mean level in meters
    # - previousreadingvalue: River level in meters at the same date the previous year
    # - readingvalue: Observed river level in meters
    df = pd.read_csv(file_path, parse_dates=["date"], date_format="%Y-%m-%d")
    df = df.rename(columns={"readingvalue": "level__m"})
    df = df.rename(columns={"previousreadingvalue": "previous_year_level_m"})

    river_level_current_year = df[["date", "level__m"]].copy()
    river_level_current_year["location"] = location_name

    river_level_previous_year = df[["date", "previous_year_level_m"]].copy().rename(
        columns={"previous_year_level_m": "level__m"}
    )
    river_level_previous_year["location"] = location_name
    river_level_previous_year["date"] = river_level_previous_year["date"].apply(lambda d: d - pd.DateOffset(years=1))

    df = pd.concat([river_level_current_year, river_level_previous_year], ignore_index=True)
    df["level__m"] = df["level__m"].apply(pd.to_numeric, errors="coerce", downcast="float")
    df = df.dropna(subset=["level__m", "date"])

    df = df[["date", "location", "level__m"]]

    return StationDataFrameSchema.validate(df)


def fetch_river_data_from_chart_api(config: Config, station_name: str) -> pd.DataFrame:
    """
    Fetch river data from the SWALIM API (chart data).
    :param config: Configuration object containing settings.
    :param station_name: Name of the river station to fetch data for.
    :return: List of raw river level data for the specified station (equivalent to the export button on the SWALIM website).
    """
    # FIXME: URL for the SWALIM API to fetch river data is different from the one used in the SWALIM website for the latest data.
    url = config.load_river_data_config()["swalim_api_url"].replace("/levels", "/graph")

    # get the station ID from the station name
    station = get_river_station_metadata(config, station_name)
    station_id = station.id
    logger.debug(f"Fetching river data for station: {station_name} (ID: {station_id})")

    # Fetch river data from the SWALIM API
    # This request returns a JSON with the river data for the given station.
    # NOTE: POST requests to this URL with payload:
    # {
    #     'station_id': station_id,
    #     'start_timestamp': 0,
    #     'end_timestamp': 0
    # }
    # Example of response:
    # {
    #     "gaugeReadingList": [
    #         {
    #             'gaugeReadingId': '142628',
    #             'dateOfReading': '1735709795000',
    #             'readingValue': '2.08',
    #             'riverId': '2',
    #             'gaugeReaderId': '7',
    #             'stationId': '2',
    #             'readingType': 'River Level Reading',
    #             'longtermMean': None,
    #             'historicalMax': None,
    #             'historicalMin': None,
    #             'dateOfReadingStr': '01-01-2025',
    #             'isHistoric': 'false',
    #             'isValidated': 'true'
    #         },
    #     ],
    #     "indicator": {
    #         "indicatorId": "7",
    #         "riverId": "2",
    #         "stationId": "2",
    #         "moderateRiskLevelVal": "4.50",
    #         "highRiskLevelVal": "5.00",
    #         "bankFullVal": "6.00",
    #         "indicator_color": "",
    #         "indicatorColor": ""
    #     },
    #     "otherDetails": {
    #         "riverName": "Jubba River",
    #         "stationName": "Dollow"
    #     },
    #     "previous_year": {
    #         "gaugeReadingList": {
    #             "01-01-2024": {
    #                 "gaugeReadingId": "140391",
    #                 "dateOfReading": "1704090336000",
    #                 "readingValue": "2.18",
    #                 "riverId": "2",
    #                 "gaugeReaderId": "7",
    #                 "stationId": "2",
    #                 "readingType": "River Level Reading",
    #                 "longtermMean": null,
    #                 "historicalMax": null,
    #                 "historicalMin": null,
    #                 "dateOfReadingStr": "01-01-2024",
    #                 "isHistoric": "false",
    #                 "isValidated": "true"
    #             }
    #         }
    #     }
    # }
    try:
        response = requests.post(
            url,
            data={
                "station_id": station_id,
                "start_timestamp": 0,
                "end_timestamp": 0
            },
            headers={
                "Accept": "*/*",
                "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
                "Referer": "https://frrims.faoswalim.org/rivers/levels",
            },
            verify=False  # Disable SSL verification
        )
        response.raise_for_status()

        # Parse the response
        data = response.json()
        if not data:
            logger.warning(f"No data found for station: {station_name}")
            return pd.DataFrame(
                columns=[
                    "date",
                    "bankfull",
                    "highfloodrisk",
                    "moderatefloodrisk",
                    "longtermmean",
                    "previousreadingvalue",
                    "readingvalue"
                ]
            )
        
        # # DEBUG: store raw json data for debugging
        # swalim_dir = config.load_data_csv_config()["swalim_raw_data_dir"]
        # if not swalim_dir.endswith('/'):
        #     swalim_dir += '/'
        # with open(f"{swalim_dir}{station_name.lower().replace(' ', '_')}_river_levels_as_at_" \
        #           f"{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.json", "w") as f:
        #     import json
        #     json.dump(data, f, indent=4)
        
        if "gaugeReadingList" not in data and "previous_year" not in data and "gaugeReadingList" not in data["previous_year"]:
            # If the expected keys are not present, print an error message and raise an exception
            logger.error(f"Unexpected data format for station: {station_name}")
            raise ValueError(f"Unexpected data format for station: {station_name}")
        current_year_data_by_date = {entry["dateOfReadingStr"]: entry for entry in data["gaugeReadingList"]}
        previous_year_data_by_date = data["previous_year"]["gaugeReadingList"]

        # Extract the current year from the data
        current_year = next(iter(current_year_data_by_date.keys())).split("-")[2]

        # Combine data into the following format:
        # "date","bankfull","highfloodrisk","moderatefloodrisk","longtermmean","previousreadingvalue","readingvalue"
        river_levels = []

        # FIXME: handle leap years correctly
        # ASSUMPTION: previous year data has an entry for all dates
        for entry in previous_year_data_by_date.values():
            # Get the current year date corresponding to the previous year entry (adjust to current year)
            current_year_date = entry["dateOfReadingStr"].split("-")
            current_year_date[2] = current_year  # Replace the year with the current year
            current_year_date = "-".join(current_year_date)
            
            current_year_entry = current_year_data_by_date.get(current_year_date, {})

            try:
                # Parse DD-MM-YYYY date format
                date = pd.to_datetime(current_year_date, format="%d-%m-%Y")
            except ValueError:
                # getting invalid date for leap year (e.g. 29-02-2024)
                # how is this handled in the SWALIM website? --> date is duplicated (!)
                # Consider as leap year issue, skip
                continue
            bankfull = data.get("indicator", {}).get("bankFullVal", None)
            highfloodrisk = data.get("indicator", {}).get("highRiskLevelVal", None)
            moderatefloodrisk = data.get("indicator", {}).get("moderateRiskLevelVal", None)
            longtermmean = current_year_entry.get("longtermMean", None)
            previousreadingvalue = entry["readingValue"]
            readingvalue = current_year_entry.get("readingValue", None)
            river_levels.append((
                date,
                bankfull,
                highfloodrisk,
                moderatefloodrisk,
                longtermmean,
                previousreadingvalue,
                readingvalue
            ))

        return pd.DataFrame(
            river_levels,
            columns=[
                "date",
                "bankfull",
                "highfloodrisk",
                "moderatefloodrisk",
                "longtermmean",
                "previousreadingvalue",
                "readingvalue"
            ]
        )
    except requests.exceptions.HTTPError as http_err:
        logger.error(f"HTTP error occurred: {http_err}")
        logger.error("Couldn't fetch the river data from the API")
        raise RuntimeError(f"HTTP error occurred: {http_err}") from http_err


# Load data from CSV file
# data can be downloaded from the SWALIM website and saved to a CSV file
# See https://frrims.faoswalim.org/rivers/levels
# NOTE: POST requests to this URL with payload:
# {
#     'station_id': station_id,
#     'start_timestamp': 0,
#     'end_timestamp': 0
# }
#
# OTHERWISE, data can be downloaded programmatically via fetch_river_data_from_api
def load_river_data_from_csvs(config: Config, location_name: str, snrfa_file_path: Optional[str], swalim_file_path: Optional[str]):
    """
    Load river data from a CSV file into the database.
    :param location_name: Name of the river location to fetch data for (label).
    :param snrfa_file_path: Path to the SNRFA CSV file. Will have priority over SWALIM file if both are provided.
    :param swalim_file_path: Path to the SWALIM CSV file.
    :param config: Configuration object containing settings.
    """
    if not snrfa_file_path and not swalim_file_path:
        logger.error("Must provide either snrfa_file_path or swalim_file_path")
        raise ValueError("Either snrfa_file_path or swalim_file_path must be provided.")
    
    snrfa_df = __load_snrfa_river_data(snrfa_file_path, location_name) if snrfa_file_path else StationDataFrameSchema.empty()
    swalim_df = __load_swalim_river_data(swalim_file_path, location_name) if swalim_file_path else StationDataFrameSchema.empty()

    logger.debug(f"Loaded SNRFA data for {location_name}: {len(snrfa_df)} records")
    logger.debug(f"Loaded SWALIM data for {location_name}: {len(swalim_df)} records")
    
    # Check if both DataFrames are empty
    if snrfa_df.empty and swalim_df.empty:
        logger.error(f"No data found for location: {location_name}")
        raise ValueError(f"No valid data found for location: {location_name}")
    
    # Data reconciliation: Combine the two DataFrames
    # Use snrfa_df data if available, otherwise use swalim_df data
    # Do reconciliation based on date and location
    # NOTE: using also location to be more generic, only one value is expected
    df = pd.concat([snrfa_df, swalim_df], ignore_index=True)
    df = df.drop_duplicates(subset=["date", "location"], keep="last")  # Keep the last entry for each date and location
    df = df.sort_values(by=["date", "location"]).reset_index(drop=True)

    # Give metrics before and after reconciliation
    logger.debug(f"Total records after reconciliation for {location_name}: {len(df)}")
    logger.debug(f"Total dates in SNRFA data: {snrfa_df['date'].nunique()}")
    logger.debug(f"Total dates in SWALIM data: {swalim_df['date'].nunique()}")
    logger.debug(f"Missing dates in SNRFA data: {snrfa_df['date'].nunique() - df['date'].nunique()}")
    logger.debug(f"Missing dates in SWALIM data: {swalim_df['date'].nunique() - df['date'].nunique()}")
    logger.debug(f"Date range in SNRFA data: {snrfa_df['date'].dt.date.min()} to {snrfa_df['date'].dt.date.max()}")
    logger.debug(f"Date range in SWALIM data: {swalim_df['date'].dt.date.min()} to {swalim_df['date'].dt.date.max()}")
    logger.debug(f"Date range after reconciliation: {df['date'].dt.date.min()} to {df['date'].dt.date.max()}")
    # Data availability in current year, past year, year before that
    current_year = pd.Timestamp.now().year
    df["year"] = df["date"].dt.year
    current_year_data = df[df["year"] == current_year]
    past_year_data = df[df["year"] == current_year - 1]
    year_before_data = df[df["year"] == current_year - 2]
    logger.info(f"Data available for {current_year}: {len(current_year_data)} records")
    logger.info(f"Data available for {current_year - 1}: {len(past_year_data)} records")
    logger.info(f"Data available for {current_year - 2}: {len(year_before_data)} records")
    
    # Check if there are any new river levels to insert
    if df.empty:
        logger.warning(f"No new river levels found for {location_name}.")
        return

    # Convert DataFrame to list of HistoricalRiverLevel objects
    def convert_row_to_river_level(row):
        return HistoricalRiverLevel(
            location_name=row["location"],
            date=row["date"],
            level_m=row["level__m"]
        )

    river_levels = [convert_row_to_river_level(row) for row in df.to_dict(orient="records")]

    # Insert into database
    insert_river_data(river_levels, config)


def get_latest_swalim_river_csv(config: Config, location_name: str) -> str:
    """
    Get the location of the latest SWALIM river levels CSV file for a specific location.
    :param config: Configuration object containing settings.
    :param location_name: Name of the river location to fetch data for.
    :return: file path of the latest SWALIM river levels CSV file.
    """
    river_data_config = config.load_data_csv_config()
    swalim_raw_data_dir = river_data_config["swalim_raw_data_dir"]
    if not swalim_raw_data_dir.endswith('/'):
        swalim_raw_data_dir += '/'
    
    # find the latest CSV file in the SWALIM raw data directory
    import os
    import glob
    latest_file = None
    for file in glob.glob(swalim_raw_data_dir + f"{location_name.lower().replace(' ', '_')}_river_levels_as_at_*.csv"):
        if os.path.isfile(file) and (latest_file is None or os.path.getmtime(file) > os.path.getmtime(latest_file)):
            latest_file = file

    if latest_file is None:
        raise FileNotFoundError(f"No SWALIM river levels CSV file found for {location_name} in {swalim_raw_data_dir}")

    return latest_file


def get_latest_snrfa_river_csv(config: Config, location_name: str) -> str:
    """
    Get the location of the latest SNRFA river levels CSV file for a specific location.
    :param config: Configuration object containing settings.
    :param location_name: Name of the river location to fetch data for.
    :return: file path of the latest SNRFA river levels CSV file.
    """
    river_data_config = config.load_data_csv_config()
    snrfa_raw_data_dir = river_data_config["snrfa_raw_data_dir"]
    if not snrfa_raw_data_dir.endswith('/'):
        snrfa_raw_data_dir += '/'
    
    # find the latest CSV file in the SNRFA raw data directory
    import os
    import glob
    latest_file = None
    for file in glob.glob(snrfa_raw_data_dir + f"snrfa_level_data-{location_name.lower().replace(' ', '_')}-*.csv"):
        if os.path.isfile(file) and (latest_file is None or os.path.getmtime(file) > os.path.getmtime(latest_file)):
            latest_file = file

    if latest_file is None:
        raise FileNotFoundError(f"No SNRFA river levels CSV file found for {location_name} in {snrfa_raw_data_dir}")

    return latest_file
