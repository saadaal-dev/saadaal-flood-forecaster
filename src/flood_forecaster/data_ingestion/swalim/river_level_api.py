from typing import Generator, List, Optional

import pandas as pd
import requests
from bs4 import BeautifulSoup
from sqlalchemy.orm import Session
import pandera.pandas as pa

from src.flood_forecaster import DatabaseConnection
from src.flood_forecaster.data_model.river_level import HistoricalRiverLevel, StationDataFrameSchema
from src.flood_forecaster.data_model.river_station import get_river_station_names, get_river_station_metadata
from src.flood_forecaster.utils.configuration import Config


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
        print(f"HTTP error occurred: {http_err}")
        print("Couldn't fetch the latest river data")

    except requests.exceptions.RequestException as err:
        print(f"Error occurred: {err}")
        print("Couldn't fetch the latest river data")

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
    return new_level_data


def __filter_river_data_exists(river_levels: List[HistoricalRiverLevel], session: Session) -> Generator[HistoricalRiverLevel, None, None]:
    """
    Check if the river levels already exist in the database.
    :param river_levels: List of HistoricalRiverLevel objects to check.
    :param session: SQLAlchemy session to use for the database query.
    :return: Generator yielding HistoricalRiverLevel objects that do not exist in the database.
    """
    for level in river_levels:
        existing_entry = session.query(HistoricalRiverLevel.date, HistoricalRiverLevel.level_m).filter(
            HistoricalRiverLevel.location_name == level.location_name,
            HistoricalRiverLevel.date == level.date
        ).first()
        if existing_entry:
            print(f"River level for {level.location_name} on {level.date} already exists in the database. Skipping insertion.")
            if existing_entry.level_m != level.level_m:
                print(f"WARNING: Existing level {existing_entry.level_m} does not match new level {level.level_m}.")
        else:
            yield level


# Insert river data into database
def insert_river_data(river_levels: List[HistoricalRiverLevel], config: Config, avoid_duplicates: bool = True) -> int:
    database_connection = DatabaseConnection(config)

    with database_connection.engine.connect() as conn:
        with Session(bind=conn) as session:
            if avoid_duplicates:
                _river_levels = list(__filter_river_data_exists(river_levels, session))
            else:
                # keep all river levels, even if they already exist in the database
                _river_levels = river_levels

            print(f"Inserting {len(_river_levels)} river levels into the database...")
            session.add_all(_river_levels)
            session.commit()
    
    return len(_river_levels)


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
    print(f"Fetching river data for station: {station_name} (ID: {station_id})")

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
            print(f"No data found for station: {station_name}")
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
        # with open(f"{swalim_dir}{station_name.lower().replace(' ', '_')}_river_levels_as_at_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.json", "w") as f:
        #     import json
        #     json.dump(data, f, indent=4)
        
        if "gaugeReadingList" not in data and "previous_year" not in data and "gaugeReadingList" not in data["previous_year"]:
            # If the expected keys are not present, print an error message and raise an exception
            print(f"Unexpected data format for station: {station_name}")
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
        print(f"HTTP error occurred: {http_err}")
        print("Couldn't fetch the river data from the API")
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
        raise ValueError("Either snrfa_file_path or swalim_file_path must be provided.")
    
    snrfa_df = __load_snrfa_river_data(snrfa_file_path, location_name) if snrfa_file_path else pa.typing.DataFrame[StationDataFrameSchema]()
    swalim_df = __load_swalim_river_data(swalim_file_path, location_name) if swalim_file_path else pa.typing.DataFrame[StationDataFrameSchema]()

    print(f"Loaded SNRFA data for {location_name}: {len(snrfa_df)} records")
    print(f"Loaded SWALIM data for {location_name}: {len(swalim_df)} records")
    
    # Check if both DataFrames are empty
    if snrfa_df.empty and swalim_df.empty:
        print(f"No data found for location: {location_name}")
        raise ValueError(f"No valid data found for location: {location_name}")
    
    # Data reconciliation: Combine the two DataFrames
    # Use snrfa_df data if available, otherwise use swalim_df data
    # Do reconciliation based on date and location
    # NOTE: using also location to be more generic, only one value is expected
    df = pd.concat([snrfa_df, swalim_df], ignore_index=True)
    df = df.drop_duplicates(subset=["date", "location"], keep="last")  # Keep the last entry for each date and location
    df = df.sort_values(by=["date", "location"]).reset_index(drop=True)

    # Give metrics before and after reconciliation
    print(f"Total records after reconciliation for {location_name}: {len(df)}")
    print(f"Total dates in SNRFA data: {snrfa_df['date'].nunique()}")
    print(f"Total dates in SWALIM data: {swalim_df['date'].nunique()}")
    print(f"Missing dates in SNRFA data: {snrfa_df['date'].nunique() - df['date'].nunique()}")
    print(f"Missing dates in SWALIM data: {swalim_df['date'].nunique() - df['date'].nunique()}")
    print(f"Date range in SNRFA data: {snrfa_df['date'].dt.date.min()} to {snrfa_df['date'].dt.date.max()}")
    print(f"Date range in SWALIM data: {swalim_df['date'].dt.date.min()} to {swalim_df['date'].dt.date.max()}")
    print(f"Date range after reconciliation: {df['date'].dt.date.min()} to {df['date'].dt.date.max()}")
    # Data availability in current year, past year, year before that
    current_year = pd.Timestamp.now().year
    df["year"] = df["date"].dt.year
    current_year_data = df[df["year"] == current_year]
    past_year_data = df[df["year"] == current_year - 1]
    year_before_data = df[df["year"] == current_year - 2]
    print(f"Data available for {current_year}: {len(current_year_data)} records")
    print(f"Data available for {current_year - 1}: {len(past_year_data)} records")
    print(f"Data available for {current_year - 2}: {len(year_before_data)} records")
    
    # Check if there are any new river levels to insert
    if df.empty:
        print(f"No new river levels found for {location_name}.")
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
