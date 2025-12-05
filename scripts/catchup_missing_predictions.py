#!/usr/bin/env python
"""
Catchup script to identify and fill missing river level predictions.

This script:
1. Loads all configured stations from metadata (not just those with existing predictions)
2. Prompts you to specify a start date (no hardcoded dates!)
3. Reads the predicted_river_level table to find last prediction per location
4. Identifies missing predictions for each location from start date (or last prediction) until today
5. Runs inference for each missing date to fill the gaps (using flood-cli commands)
6. Updates risk assessments after catching up (using flood-cli risk-assessment)

Similar to batch_infer_and_risk_assess.sh but smarter:
- Prompts for start date instead of hardcoding
- Only processes missing dates (skips dates that already have predictions)
- Works for locations with no existing predictions in the database

Use this when the automated pipeline has failed in the past and you need to backfill missing data.

DEPLOYMENT:
- Can run inside Docker container (recommended for production)
- Can run outside container if you have network access to the database
- Requires POSTGRES_PASSWORD environment variable
- Requires flood-cli installed and accessible
"""

import subprocess
import sys
from datetime import datetime, timedelta, date
from pathlib import Path

from sqlalchemy import select, func, distinct
from sqlalchemy.orm import Session

# Add the src directory to the path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from flood_forecaster.utils.configuration import Config
from flood_forecaster.utils.database_helper import DatabaseConnection
from flood_forecaster.data_model.river_level import PredictedRiverLevel
from flood_forecaster.data_model.river_station import get_river_stations_static


def get_all_configured_stations(config: Config) -> list[str]:
    """Get all stations configured in the system from static metadata."""
    river_stations = get_river_stations_static(config)
    return [station.name for station in river_stations]


def get_all_locations_with_predictions(session: Session) -> list[str]:
    """Get all unique locations that have predictions in the database."""
    stmt = select(distinct(PredictedRiverLevel.location_name)).order_by(PredictedRiverLevel.location_name)
    result = session.execute(stmt)
    locations = [row[0] for row in result]
    return locations


def get_last_prediction_date(session: Session, location: str) -> date | None:
    """Get the most recent prediction date for a location."""
    stmt = (
        select(func.max(func.date(PredictedRiverLevel.date)))
        .where(PredictedRiverLevel.location_name == location)
        .where(PredictedRiverLevel.level_m.isnot(None))
    )
    result = session.execute(stmt).scalar()
    return result


def get_missing_dates(session: Session, location: str, start_date: date, end_date: date = None) -> list[date]:
    """
    Identify ALL missing prediction dates for a location, including holes/gaps in existing data.
    Returns list of all missing dates from start_date to end_date (default: today).

    This checks what dates actually exist in the database and finds ALL gaps,
    not just dates after the last prediction.
    """
    if end_date is None:
        end_date = date.today()

    # Get all existing prediction dates for this location in the date range
    stmt = (
        select(func.date(PredictedRiverLevel.date))
        .where(PredictedRiverLevel.location_name == location)
        .where(PredictedRiverLevel.date >= start_date)
        .where(PredictedRiverLevel.date <= end_date)
        .where(PredictedRiverLevel.level_m.isnot(None))
        .distinct()
    )
    result = session.execute(stmt)
    existing_dates = {row[0] for row in result}

    # Generate all dates in the range
    all_dates = []
    current = start_date
    while current <= end_date:
        all_dates.append(current)
        current += timedelta(days=1)

    # Find missing dates (dates that should exist but don't)
    missing_dates = [d for d in all_dates if d not in existing_dates]

    return missing_dates


def check_station_supported(location: str, forecast_days: int = 7, model_type: str = "Prophet_001") -> tuple[
    bool, str | None]:
    """
    Check if a station is supported by running a test inference.
    Returns (is_supported, error_message).
    """
    try:
        # Try a single inference with a recent date to check if station is supported
        test_date = date.today() - timedelta(days=1)
        date_str = test_date.strftime("%Y-%m-%d")
        cmd = [
            "flood-cli", "ml", "infer",
            "-f", str(forecast_days),
            "-m", model_type,
            "-o", "database",
            "-d", date_str,
            location
        ]

        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            check=False
        )

        if result.returncode == 0:
            return True, None
        else:
            error_msg = result.stderr.strip() if result.stderr else 'Command failed'
            # Check if it's a "station not supported" error
            if "not supported" in error_msg.lower():
                return False, error_msg
            # For other errors, we still consider it "supported" but with issues
            return True, error_msg
    except Exception as e:
        return True, str(e)


def run_inference_for_date(location: str, inference_date: date,
                           forecast_days: int = 7, model_type: str = "Prophet_001") -> bool:
    """
    Run inference for a specific location and date using flood-cli command.
    Uses the same approach as batch_infer_and_risk_assess.sh script.
    Returns True if successful, False otherwise.
    """
    try:
        # Format the command exactly like batch_infer_and_risk_assess.sh does
        date_str = inference_date.strftime("%Y-%m-%d")
        cmd = [
            "flood-cli", "ml", "infer",
            "-f", str(forecast_days),
            "-m", model_type,
            "-o", "database",
            "-d", date_str,
            location
        ]

        # Run the command
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            check=False
        )

        if result.returncode == 0:
            return True
        else:
            print(f"❌ Error: {result.stderr.strip() if result.stderr else 'Command failed'}")
            return False
    except Exception as e:
        print(f"❌ Error: {e}")
        return False


def parse_date_input(date_str: str) -> date | None:
    """Parse a date string in YYYY-MM-DD format."""
    try:
        return datetime.strptime(date_str.strip(), "%Y-%m-%d").date()
    except ValueError:
        return None


def prompt_for_stations(all_stations: list[str]) -> list[str]:
    """
    Prompt user to select which stations to process.
    Returns list of selected station names.
    """
    print("📍 Select stations to process:")
    print()
    print("   Available stations:")
    for i, station in enumerate(all_stations, 1):
        print(f"     {i}. {station}")
    print()
    print("   Options:")
    print("     - Enter numbers separated by commas (e.g., 1,3,5)")
    print("     - Enter 'all' to process all stations")
    print("     - Enter station names separated by commas")
    print()

    while True:
        selection = input("   Your selection: ").strip()

        if not selection:
            print("   ⚠️  Please enter a selection")
            continue

        # Check for 'all'
        if selection.lower() == 'all':
            print(f"   Selected: All {len(all_stations)} stations")
            return all_stations

        selected_stations = []

        # Try parsing as numbers
        if any(char.isdigit() for char in selection):
            try:
                indices = [int(x.strip()) for x in selection.split(',')]
                for idx in indices:
                    if 1 <= idx <= len(all_stations):
                        selected_stations.append(all_stations[idx - 1])
                    else:
                        print(f"   ⚠️  Invalid number: {idx} (must be 1-{len(all_stations)})")
                        selected_stations = []
                        break

                if selected_stations:
                    print(f"   Selected: {', '.join(selected_stations)}")
                    return selected_stations
                else:
                    continue
            except ValueError:
                pass  # Try parsing as station names

        # Try parsing as station names
        station_names = [s.strip() for s in selection.split(',')]
        for name in station_names:
            # Case-insensitive matching
            matched = False
            for station in all_stations:
                if station.lower() == name.lower():
                    selected_stations.append(station)
                    matched = True
                    break

            if not matched:
                print(f"   ⚠️  Unknown station: '{name}'")
                print(f"   Available: {', '.join(all_stations)}")
                selected_stations = []
                break

        if selected_stations:
            print(f"   Selected: {', '.join(selected_stations)}")
            return selected_stations


def main():
    """Main catchup process."""
    print("=" * 80)
    print("CATCHUP MISSING PREDICTIONS")
    print("=" * 80)
    print(f"Current time: {datetime.now()}")
    print()

    # Configuration
    config_path = Path(__file__).parent.parent / "config" / "config.ini"
    if not config_path.exists():
        print(f"❌ Configuration file not found at {config_path}")
        sys.exit(1)

    config = Config(str(config_path))
    db = DatabaseConnection(config)

    # Get all configured stations from metadata
    try:
        all_configured_stations = get_all_configured_stations(config)
        print(f"📍 Found {len(all_configured_stations)} configured stations:")
        print(f"   {', '.join(all_configured_stations)}")
        print()
    except Exception as e:
        print(f"❌ Failed to load station metadata: {e}")
        sys.exit(1)

    # Prompt for station selection
    selected_stations = prompt_for_stations(all_configured_stations)
    print()

    # Prompt for start date
    print("🗓️  From which date should we check for missing predictions?")
    print(f"   (Format: YYYY-MM-DD, e.g., 2024-01-01)")
    print(f"   Press Enter to use default: 2024-01-01")
    start_date_input = input("   Start date: ").strip()

    if start_date_input == "":
        start_date = date(2024, 1, 1)
        print(f"   Using default: {start_date}")
    else:
        start_date = parse_date_input(start_date_input)
        if start_date is None:
            print(f"❌ Invalid date format. Please use YYYY-MM-DD")
            sys.exit(1)
        print(f"   Using: {start_date}")

    end_date = date.today()
    print(f"   End date: {end_date} (today)")
    print()

    # Track statistics
    total_missing = 0
    total_processed = 0
    total_failed = 0
    location_stats = {}

    print("Step 1: Analyzing missing predictions by location")
    print("-" * 80)

    with Session(db.engine) as session:
        # Analyze each selected station
        for location in selected_stations:
            last_date = get_last_prediction_date(session, location)
            missing_dates = get_missing_dates(session, location, start_date, end_date)

            location_stats[location] = {
                'last_date': last_date,
                'missing_count': len(missing_dates),
                'missing_dates': missing_dates
            }

            total_missing += len(missing_dates)

            print(f"📍 {location}")
            if last_date is None:
                print(f"   Last prediction: None (no predictions in DB)")
                print(f"   Will create predictions from: {start_date}")
            else:
                print(f"   Last prediction: {last_date}")

            print(f"   Missing days: {len(missing_dates)}")

            if missing_dates:
                # Check if missing dates are continuous or have gaps
                if len(missing_dates) == 1:
                    print(f"   Missing date: {missing_dates[0]}")
                else:
                    # Detect if there are gaps (non-continuous missing dates)
                    gaps = []
                    gap_start = missing_dates[0]
                    gap_end = missing_dates[0]

                    for i in range(1, len(missing_dates)):
                        if missing_dates[i] == gap_end + timedelta(days=1):
                            # Continuous gap
                            gap_end = missing_dates[i]
                        else:
                            # Gap break, save current gap
                            gaps.append((gap_start, gap_end))
                            gap_start = missing_dates[i]
                            gap_end = missing_dates[i]

                    # Save last gap
                    gaps.append((gap_start, gap_end))

                    if len(gaps) == 1:
                        # All missing dates are continuous
                        print(f"   Date range: {missing_dates[0]} to {missing_dates[-1]}")
                    else:
                        # Multiple gaps detected
                        print(f"   ⚠️  {len(gaps)} gap(s) detected:")
                        for gap_start, gap_end in gaps:
                            if gap_start == gap_end:
                                print(f"      - {gap_start}")
                            else:
                                days = (gap_end - gap_start).days + 1
                                print(f"      - {gap_start} to {gap_end} ({days} days)")
            print()

    if total_missing == 0:
        print("✅ No missing predictions found! All locations are up to date.")
        print("=" * 80)
        return

    print(f"📊 Summary: {total_missing} missing predictions across {len(selected_stations)} location(s)")
    print()

    # Ask for confirmation
    print("⚠️  This will run inference for all missing dates.")
    print("   Depending on the number of missing dates, this may take a while.")
    print()
    response = input("Do you want to proceed? (yes/no): ").strip().lower()

    if response != "yes":
        print("❌ Catchup cancelled by user.")
        sys.exit(0)

    print()
    print("Step 2: Fetching latest data (historical weather, forecast, river levels)")
    print("-" * 80)

    # Run data ingestion just like batch_infer_and_risk_assess.sh does
    print("Running data ingestion...")
    data_ingestion_commands = [
        ["flood-cli", "data-ingestion", "fetch-openmeteo", "historical"],
        ["flood-cli", "data-ingestion", "fetch-openmeteo", "forecast"],
        ["flood-cli", "data-ingestion", "fetch-river-data"]
    ]

    data_ingestion_failed = False
    for cmd in data_ingestion_commands:
        print(f"  Running: {' '.join(cmd)}")
        result = subprocess.run(cmd, capture_output=True, text=True, check=False)
        if result.returncode != 0:
            print(f"  ⚠️  Warning: {' '.join(cmd[2:])} failed")
            print(f"     {result.stderr.strip() if result.stderr else 'Command failed'}")
            data_ingestion_failed = True
        else:
            print(f"  ✅ {' '.join(cmd[2:])} completed")

    if data_ingestion_failed:
        print()
        print("⚠️  Some data ingestion steps failed. Predictions may fail if required data is missing.")
        print("   Do you want to continue anyway? (yes/no): ", end="")
        response = input().strip().lower()
        if response != "yes":
            print("❌ Catchup cancelled by user.")
            sys.exit(1)

    print()
    print("Step 3: Running inference for missing dates")
    print("-" * 80)

    # Track unsupported stations
    unsupported_stations = []

    # Process each selected location
    for location in selected_stations:
        stats = location_stats[location]
        missing_dates = stats['missing_dates']

        if not missing_dates:
            print(f"✓ {location}: Up to date")
            continue

        # Check if station is supported before processing all dates
        print(f"📍 {location}: Checking if station is supported...", end=" ")
        is_supported, error_msg = check_station_supported(location)

        if not is_supported:
            print(f"⚠️  SKIPPED")
            print(f"   Reason: {error_msg}")
            print(f"   {len(missing_dates)} dates will not be processed for this station")
            unsupported_stations.append(location)
            # Don't count these as failures since the station isn't supported
            print()
            continue
        else:
            print(f"✅ Supported")

        print(f"   Processing {len(missing_dates)} missing dates...")

        success_count = 0
        fail_count = 0

        for inference_date in missing_dates:
            print(f"  Processing {inference_date}...", end=" ")
            success = run_inference_for_date(location, inference_date)

            if success:
                print("✅")
                success_count += 1
                total_processed += 1
            else:
                print("❌")
                fail_count += 1
                total_failed += 1

        print(f"  Location summary: {success_count} successful, {fail_count} failed")
        print()

    print("=" * 80)
    print("Step 4: Updating risk assessments")
    print("-" * 80)

    try:
        # Use flood-cli command like batch_infer_and_risk_assess.sh does
        result = subprocess.run(
            ["flood-cli", "risk-assessment"],
            capture_output=True,
            text=True,
            check=False
        )

        if result.returncode == 0:
            print("✅ Risk assessments updated successfully")
        else:
            print(
                f"❌ Failed to update risk assessments: {result.stderr.strip() if result.stderr else 'Command failed'}")
            print("   You may need to run 'flood-cli risk-assessment' manually")
    except Exception as e:
        print(f"❌ Failed to update risk assessments: {e}")
        print("   You may need to run 'flood-cli risk-assessment' manually")

    print()
    print("=" * 80)
    print("CATCHUP COMPLETE")
    print("=" * 80)
    print(f"Total missing predictions found: {total_missing}")
    print(f"Successfully processed: {total_processed}")
    print(f"Failed: {total_failed}")
    if unsupported_stations:
        print(f"Unsupported stations (skipped): {len(unsupported_stations)}")
        print(f"   {', '.join(unsupported_stations)}")
    print()

    if unsupported_stations:
        print("ℹ️  Some stations were skipped because they are not supported by the ML model:")
        for station in unsupported_stations:
            print(f"   - {station}")
        print()
        print("   To support these stations, you need to:")
        print("   - Train ML models for these locations")
        print("   - Ensure model files exist in the models/ directory")
        print()

    if total_failed > 0:
        print("⚠️  Some predictions failed. Check the errors above.")
        print("   You may need to:")
        print("   - Verify historical weather data is available for those dates")
        print("   - Check model files exist for all locations")
        print("   - Run data ingestion: flood-cli data-ingestion fetch-openmeteo historical")
        sys.exit(1)
    else:
        if unsupported_stations:
            print("✅ All supported stations have been processed successfully!")
            print("   (Some stations were skipped - see above)")
        else:
            print("✅ All missing predictions have been filled successfully!")

    print("=" * 80)


if __name__ == "__main__":
    main()
