from datetime import date, timedelta
from typing import Generator, List, Tuple

from flood_forecaster.data_model.river_level import HistoricalRiverLevel, RiverStationMetadata, StationRiverData
from sqlalchemy import func
from sqlalchemy.orm import Session

from flood_forecaster import DatabaseConnection
from flood_forecaster.utils.configuration import Config
from flood_forecaster.utils.logging_config import get_logger

logger = get_logger(__name__)


def get_station_mapping(config: Config) -> List[RiverStationMetadata]:
    """
    Get mapping of station names to SWALIM internal IDs.
    Returns: List of RiverStationMetadata objects
    """
    database_connection = DatabaseConnection(config)

    with database_connection.engine.connect() as conn:
        with Session(bind=conn) as session:
            station_metadata = session.query(RiverStationMetadata).filter(
                RiverStationMetadata.swalim_internal_id != None
            ).order_by(RiverStationMetadata.station_name).all()

    return station_metadata


def get_existing_data_range(session: Session, location: str) -> Tuple[date | None, date | None, int]:
    """
    Get the date range and count of existing data for a location.
    Returns: (first_date, last_date, record_count)
    """
    result = session.query(
        func.min(HistoricalRiverLevel.date),
        func.max(HistoricalRiverLevel.date),
        func.count(func.distinct(HistoricalRiverLevel.date))
    ).filter(HistoricalRiverLevel.location_name == location).one()

    if result and result[0]:
        return result[0], result[1], result[2]
    else:
        return None, None, 0


def identify_gaps(session: Session, location: str, first_date: date, last_date: date) -> List[date]:
    """
    Identify missing dates in the date range for a location.
    Returns list of missing dates.
    """
    # Get all existing dates for this location
    existing_dates = session.query(HistoricalRiverLevel.date).filter(
        HistoricalRiverLevel.location_name == location,
        HistoricalRiverLevel.date >= first_date,
        HistoricalRiverLevel.date <= last_date
    ).order_by(HistoricalRiverLevel.date).all()

    existing_dates_set = {row[0] for row in existing_dates}

    # Generate all dates in the range
    all_dates = []
    current = first_date
    while current <= last_date:
        all_dates.append(current)
        current += timedelta(days=1)

    # Find missing dates
    missing_dates = [d for d in all_dates if d not in existing_dates_set]

    return missing_dates


def fetch_data_from_public_schema(session: Session, swalim_id: int, missing_dates: List[date]) -> List[Tuple[date, float]]:
    """
    Fetch river data from public.station_river_data for the given SWALIM ID and dates.
    Returns: [(date, reading), ...]
    """
    if not missing_dates:
        return []

    min_date = min(missing_dates)
    max_date = max(missing_dates)

    # Query the public schema table
    result = session.query(StationRiverData.reading_date, StationRiverData.reading).filter(
        StationRiverData.station_id == swalim_id,
        StationRiverData.reading_date >= min_date,
        StationRiverData.reading_date <= max_date,
        StationRiverData.reading != None
    ).order_by(StationRiverData.reading_date).all()

    data = [(row[0], row[1]) for row in result]
    return data


def insert_missing_data(
    session: Session,
    location: str,
    data: List[Tuple[date, float]],
    avoid_duplicates: bool = True,
) -> int:
    """
    Insert missing data into historical_river_level using ORM.
    Returns number of records inserted.
    """
    if not data:
        return 0

    if avoid_duplicates:
        filtered_data = list(__filter_river_data_exists(data, location, session))
    else:
        filtered_data = data

    if not filtered_data:
        return 0

    records = [
        HistoricalRiverLevel(location_name=location, date=date_val, level_m=level_val)
        for date_val, level_val in filtered_data
    ]

    try:
        logger.debug(f"Inserting {len(records)} river levels into historical_river_level...")
        session.add_all(records)
        session.commit()
        return len(records)
    except Exception as e:
        session.rollback()
        logger.error(f"    ⚠️  Failed to insert data for {location}: {e}")
        return 0


def __filter_river_data_exists(
    data: List[Tuple[date, float]],
    location: str,
    session: Session,
) -> Generator[Tuple[date, float], None, None]:
    """
    Check if the river levels already exist in historical_river_level.
    :param data: List of (date, reading) tuples to check.
    :param location: Station/location name in historical_river_level.
    :param session: SQLAlchemy session to use for the database query.
    :return: Generator yielding (date, reading) tuples that do not exist in the database.
    """
    for date_val, level_val in data:
        existing_entry = session.query(HistoricalRiverLevel.level_m).filter(
            HistoricalRiverLevel.location_name == location,
            HistoricalRiverLevel.date == date_val,
        ).first()
        if existing_entry:
            logger.debug(
                f"River level for {location} on {date_val} already exists in historical_river_level. Skipping insertion."
            )
            if existing_entry.level_m != level_val:
                logger.warning(
                    f"WARNING: Existing level {existing_entry.level_m} does not match new level {level_val}."
                )
        else:
            yield date_val, level_val


def fill_gaps_using_public_schema(config: Config) -> bool:
    """Main gap filling process."""
    logger.info("=" * 80)
    logger.info("FILL GAPS IN HISTORICAL RIVER LEVEL DATA")
    logger.info("=" * 80)
    logger.info("")
    logger.info("This fills data gaps using public.station_river_data")
    logger.info("")

    db = DatabaseConnection(config)

    total_gaps = 0
    total_filled = 0
    total_missing_in_source = 0

    # Step 1: Get station mapping
    logger.info("Step 1: Loading station mapping")
    logger.info("-" * 80)

    station_metadata = get_station_mapping(config)

    if not station_metadata:
        logger.error("❌ No station mapping found in river_station_metadata")
        logger.error("   Check that swalim_internal_id is populated")
        return False

    logger.info(f"Found {len(station_metadata)} stations with SWALIM IDs:")
    for station in station_metadata:
        logger.info(f"  - {station.station_name}: SWALIM ID {station.swalim_internal_id}")
    logger.info("")

    station_mapping = {
        station.station_name: station.swalim_internal_id
        for station in station_metadata
    }

    with db.engine.connect() as conn:
        with Session(bind=conn) as session:
            # Step 2: Analyze gaps for each station
            logger.info("Step 2: Analyzing data gaps")
            logger.info("-" * 80)

            station_gaps = {}

            for station_name in station_mapping.keys():
                first_date, last_date, count = get_existing_data_range(session, station_name)

                if first_date is None:
                    logger.info(f"📍 {station_name}")
                    logger.info("   No data exists - skipping (use full data import instead)")
                    logger.info("")
                    continue

                # Calculate expected records
                expected_records = (last_date - first_date).days + 1
                gap_count = expected_records - count

                logger.info(f"📍 {station_name}")
                logger.info(f"   Date range: {first_date} to {last_date}")
                logger.info(f"   Existing records: {count}")
                logger.info(f"   Expected records: {expected_records}")

                if gap_count > 0:
                    logger.info(f"   ⚠️  Gaps detected: {gap_count} missing days")

                    # Identify specific missing dates
                    missing_dates = identify_gaps(session, station_name, first_date, last_date)
                    station_gaps[station_name] = missing_dates
                    total_gaps += len(missing_dates)

                    logger.info(f"   Missing dates: {len(missing_dates)}")
                    if len(missing_dates) <= 10:
                        for d in missing_dates:
                            logger.info(f"      - {d}")
                    else:
                        logger.info(f"      First: {missing_dates[0]}")
                        logger.info(f"      Last: {missing_dates[-1]}")
                else:
                    logger.info("   ✅ No gaps - data is continuous")

                logger.info("")

            if total_gaps == 0:
                logger.info("✅ No gaps found! All stations have continuous data.")
                logger.info("=" * 80)
                return True

            logger.info(f"📊 Total gaps found: {total_gaps} missing days across {len(station_gaps)} stations")
            logger.info("")

            # Step 3: Confirm before filling
            logger.info("⚠️  This will fetch data from public.station_river_data and fill the gaps.")
            logger.info("")

            logger.info("")
            logger.info("Step 3: Filling gaps from public.station_river_data")
            logger.info("-" * 80)

            # Step 4: Fill gaps for each station
            for station_name, missing_dates in station_gaps.items():
                swalim_id = station_mapping[station_name]

                logger.info(f"📍 {station_name} (SWALIM ID: {swalim_id})")
                logger.info(f"   Fetching data for {len(missing_dates)} missing dates...")

                # Fetch data from public schema
                source_data = fetch_data_from_public_schema(session, swalim_id, missing_dates)

                if not source_data:
                    logger.error("   ⚠️  No data found in public.station_river_data")
                    total_missing_in_source += len(missing_dates)
                    logger.info("")
                    continue

                logger.info(f"   Found {len(source_data)} records in source table")

                # Filter to only dates that were missing
                missing_dates_set = set(missing_dates)
                filtered_data = [(d, v) for d, v in source_data if d in missing_dates_set]

                logger.info(f"   Inserting {len(filtered_data)} records...")

                # Insert data
                inserted = insert_missing_data(session, station_name, filtered_data)
                total_filled += inserted

                if inserted > 0:
                    logger.info(f"   ✅ Successfully inserted {inserted} records")

                # Check if any dates still missing
                still_missing = len(missing_dates) - inserted
                if still_missing > 0:
                    logger.error(f"   ⚠️  {still_missing} dates still missing (no data in source)")
                    total_missing_in_source += still_missing

                logger.info("")

            logger.info("=" * 80)
            logger.info("GAP FILLING COMPLETE")
            logger.info("=" * 80)
            logger.info(f"Total gaps found: {total_gaps}")
            logger.info(f"Successfully filled: {total_filled}")
            logger.info(f"Still missing (no source data): {total_missing_in_source}")
            logger.info("")

            if total_filled > 0:
                logger.info("✅ Gaps have been filled! Run check_river_data_availability.py to verify.")
                logger.info("")
                logger.info("Next steps:")
                logger.info("  1. Verify gaps are filled: python scripts/check_river_data_availability.py")
                logger.info("  2. Run catchup: python scripts/catchup_missing_predictions.py")
            else:
                logger.info("⚠️  No data was filled. The source table may not have the data needed.")
                return False

            logger.info("=" * 80)
            return True

