#!/usr/bin/env python
"""
Fill gaps in historical_river_level table using data from public.station_river_data.

This script:
1. Reads station mapping from river_station_metadata (station_name -> swalim_internal_id)
2. Identifies gaps in historical_river_level per location
3. Fetches missing data from public.station_river_data using the swalim_internal_id
4. Inserts the missing data into historical_river_level

Use this to backfill historical river data gaps that prevent catchup predictions.
"""

import sys
from datetime import date, timedelta
from pathlib import Path
from typing import Dict, List, Tuple

from sqlalchemy import text

# Add the src directory to the path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from flood_forecaster.utils.configuration import Config
from flood_forecaster.utils.database_helper import DatabaseConnection


def get_station_mapping(conn) -> Dict[str, int]:
    """
    Get mapping of station names to SWALIM internal IDs.
    Returns: {station_name: swalim_internal_id}
    """
    query = text("""
                 SELECT station_name, swalim_internal_id
                 FROM flood_forecaster.river_station_metadata
                 WHERE swalim_internal_id IS NOT NULL
                 ORDER BY station_name
                 """)

    result = conn.execute(query)
    mapping = {}

    for row in result:
        station_name = row[0]
        swalim_id = row[1]
        mapping[station_name] = swalim_id

    return mapping


def get_existing_data_range(conn, location: str) -> Tuple[date | None, date | None, int]:
    """
    Get the date range and count of existing data for a location.
    Returns: (first_date, last_date, record_count)
    """
    query = text("""
                 SELECT MIN(date) as first_date,
                        MAX(date) as last_date,
                        COUNT(*)  as record_count
                 FROM flood_forecaster.historical_river_level
                 WHERE location_name = :location
                 """)

    result = conn.execute(query, {"location": location}).fetchone()

    if result and result[0]:
        return result[0], result[1], result[2]
    else:
        return None, None, 0


def identify_gaps(conn, location: str, first_date: date, last_date: date) -> List[date]:
    """
    Identify missing dates in the date range for a location.
    Returns list of missing dates.
    """
    # Get all existing dates for this location
    query = text("""
                 SELECT date
                 FROM flood_forecaster.historical_river_level
                 WHERE location_name = :location
                   AND date >= :first_date
                   AND date <= :last_date
                 ORDER BY date
                 """)

    result = conn.execute(query, {
        "location": location,
        "first_date": first_date,
        "last_date": last_date
    })

    existing_dates = {row[0] for row in result}

    # Generate all dates in the range
    all_dates = []
    current = first_date
    while current <= last_date:
        all_dates.append(current)
        current += timedelta(days=1)

    # Find missing dates
    missing_dates = [d for d in all_dates if d not in existing_dates]

    return missing_dates


def fetch_data_from_public_schema(conn, swalim_id: int, missing_dates: List[date]) -> List[Tuple[date, float]]:
    """
    Fetch river data from public.station_river_data for the given SWALIM ID and dates.
    Returns: [(date, reading), ...]
    """
    if not missing_dates:
        return []

    min_date = min(missing_dates)
    max_date = max(missing_dates)

    # Query the public schema table
    query = text("""
                 SELECT reading_date, reading
                 FROM public.station_river_data
                 WHERE station_id = :station_id
                   AND reading_date >= :min_date
                   AND reading_date <= :max_date
                   AND reading IS NOT NULL
                 ORDER BY date
                 """)

    try:
        result = conn.execute(query, {
            "station_id": swalim_id,
            "min_date": min_date,
            "max_date": max_date
        })

        data = [(row[0], row[1]) for row in result]
        return data
    except Exception as e:
        print(f"    ⚠️  Error querying public.station_river_data: {e}")
        return []


def insert_missing_data(conn, location: str, data: List[Tuple[date, float]]) -> int:
    """
    Insert missing data into historical_river_level.
    Returns number of records inserted.
    """
    if not data:
        return 0

    # Build insert query
    insert_query = text("""
                        INSERT INTO flood_forecaster.historical_river_level (location_name, date, level_m)
                        VALUES (:location, :date, :level) ON CONFLICT DO NOTHING
                        """)

    inserted = 0
    for date_val, level_val in data:
        try:
            conn.execute(insert_query, {
                "location": location,
                "date": date_val,
                "level": level_val
            })
            inserted += 1
        except Exception as e:
            print(f"    ⚠️  Failed to insert {date_val}: {e}")

    conn.commit()
    return inserted


def main():
    """Main gap filling process."""
    print("=" * 80)
    print("FILL GAPS IN HISTORICAL RIVER LEVEL DATA")
    print("=" * 80)
    print()
    print("This script fills data gaps using public.station_river_data")
    print()

    # Configuration
    config_path = Path(__file__).parent.parent / "config" / "config.ini"
    if not config_path.exists():
        print(f"❌ Configuration file not found at {config_path}")
        sys.exit(1)

    config = Config(str(config_path))
    db = DatabaseConnection(config)

    total_gaps = 0
    total_filled = 0
    total_missing_in_source = 0

    with db.engine.connect() as conn:
        # Step 1: Get station mapping
        print("Step 1: Loading station mapping")
        print("-" * 80)

        station_mapping = get_station_mapping(conn)

        if not station_mapping:
            print("❌ No station mapping found in river_station_metadata")
            print("   Check that swalim_internal_id is populated")
            sys.exit(1)

        print(f"Found {len(station_mapping)} stations with SWALIM IDs:")
        for station_name, swalim_id in station_mapping.items():
            print(f"  - {station_name}: SWALIM ID {swalim_id}")
        print()

        # Step 2: Analyze gaps for each station
        print("Step 2: Analyzing data gaps")
        print("-" * 80)

        station_gaps = {}

        for station_name in station_mapping.keys():
            first_date, last_date, count = get_existing_data_range(conn, station_name)

            if first_date is None:
                print(f"📍 {station_name}")
                print(f"   No data exists - skipping (use full data import instead)")
                print()
                continue

            # Calculate expected records
            expected_records = (last_date - first_date).days + 1
            gap_count = expected_records - count

            print(f"📍 {station_name}")
            print(f"   Date range: {first_date} to {last_date}")
            print(f"   Existing records: {count}")
            print(f"   Expected records: {expected_records}")

            if gap_count > 0:
                print(f"   ⚠️  Gaps detected: {gap_count} missing days")

                # Identify specific missing dates
                missing_dates = identify_gaps(conn, station_name, first_date, last_date)
                station_gaps[station_name] = missing_dates
                total_gaps += len(missing_dates)

                print(f"   Missing dates: {len(missing_dates)}")
                if len(missing_dates) <= 10:
                    for d in missing_dates:
                        print(f"      - {d}")
                else:
                    print(f"      First: {missing_dates[0]}")
                    print(f"      Last: {missing_dates[-1]}")
            else:
                print(f"   ✅ No gaps - data is continuous")

            print()

        if total_gaps == 0:
            print("✅ No gaps found! All stations have continuous data.")
            print("=" * 80)
            return

        print(f"📊 Total gaps found: {total_gaps} missing days across {len(station_gaps)} stations")
        print()

        # Step 3: Confirm before filling
        print("⚠️  This will fetch data from public.station_river_data and fill the gaps.")
        print()
        response = input("Do you want to proceed? (yes/no): ").strip().lower()

        if response != "yes":
            print("❌ Gap filling cancelled by user.")
            sys.exit(0)

        print()
        print("Step 3: Filling gaps from public.station_river_data")
        print("-" * 80)

        # Step 4: Fill gaps for each station
        for station_name, missing_dates in station_gaps.items():
            swalim_id = station_mapping[station_name]

            print(f"📍 {station_name} (SWALIM ID: {swalim_id})")
            print(f"   Fetching data for {len(missing_dates)} missing dates...")

            # Fetch data from public schema
            source_data = fetch_data_from_public_schema(conn, swalim_id, missing_dates)

            if not source_data:
                print(f"   ⚠️  No data found in public.station_river_data")
                total_missing_in_source += len(missing_dates)
                print()
                continue

            print(f"   Found {len(source_data)} records in source table")

            # Filter to only dates that were missing
            missing_dates_set = set(missing_dates)
            filtered_data = [(d, v) for d, v in source_data if d in missing_dates_set]

            print(f"   Inserting {len(filtered_data)} records...")

            # Insert data
            inserted = insert_missing_data(conn, station_name, filtered_data)
            total_filled += inserted

            if inserted > 0:
                print(f"   ✅ Successfully inserted {inserted} records")

            # Check if any dates still missing
            still_missing = len(missing_dates) - inserted
            if still_missing > 0:
                print(f"   ⚠️  {still_missing} dates still missing (no data in source)")
                total_missing_in_source += still_missing

            print()

        print("=" * 80)
        print("GAP FILLING COMPLETE")
        print("=" * 80)
        print(f"Total gaps found: {total_gaps}")
        print(f"Successfully filled: {total_filled}")
        print(f"Still missing (no source data): {total_missing_in_source}")
        print()

        if total_filled > 0:
            print("✅ Gaps have been filled! Run check_river_data_availability.py to verify.")
            print()
            print("Next steps:")
            print("  1. Verify gaps are filled: python scripts/check_river_data_availability.py")
            print("  2. Run catchup: python scripts/catchup_missing_predictions.py")
        else:
            print("⚠️  No data was filled. The source table may not have the data needed.")

        print("=" * 80)


if __name__ == "__main__":
    main()
