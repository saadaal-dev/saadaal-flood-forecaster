#!/usr/bin/env python
"""
Catchup script to identify and fill missing river level predictions.

This script:
1. Reads the predicted_river_level table
2. Identifies missing predictions for each location from the last prediction date until today
3. Runs inference for each missing date to fill the gaps (using flood-cli commands)
4. Updates risk assessments after catching up (using flood-cli risk-assessment)

Similar to batch_infer_and_risk_assess.sh but smarter - only processes the specific
missing dates for each location instead of all dates from 2024-01-01.

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


def get_all_locations(session: Session) -> list[str]:
    """Get all unique locations that have predictions."""
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


def get_missing_dates(session: Session, location: str, end_date: date = None) -> list[date]:
    """
    Identify missing prediction dates for a location.
    Returns list of dates from last prediction until end_date (default: today).
    """
    if end_date is None:
        end_date = date.today()

    last_date = get_last_prediction_date(session, location)

    if last_date is None:
        print(f"  ⚠️  No predictions found for {location}. Consider running from a specific start date.")
        return []

    missing_dates = []
    current = last_date + timedelta(days=1)

    while current <= end_date:
        missing_dates.append(current)
        current += timedelta(days=1)

    return missing_dates


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


def main():
    """Main catchup process."""
    print("=" * 80)
    print("CATCHUP MISSING PREDICTIONS")
    print("=" * 80)
    print(f"Current time: {datetime.now()}")
    print(f"Catching up predictions until: {date.today()}")
    print()

    # Configuration
    config_path = Path(__file__).parent.parent / "config" / "config.ini"
    if not config_path.exists():
        print(f"❌ Configuration file not found at {config_path}")
        sys.exit(1)

    config = Config(str(config_path))
    db = DatabaseConnection(config)

    # Track statistics
    total_missing = 0
    total_processed = 0
    total_failed = 0
    location_stats = {}

    print("Step 1: Analyzing missing predictions by location")
    print("-" * 80)

    with Session(db.engine) as session:
        locations = get_all_locations(session)

        if not locations:
            print("❌ No locations found in predicted_river_level table.")
            print("   Please run the initial prediction pipeline first.")
            sys.exit(1)

        print(f"Found {len(locations)} locations: {', '.join(locations)}")
        print()

        # Analyze each location
        for location in locations:
            last_date = get_last_prediction_date(session, location)
            missing_dates = get_missing_dates(session, location)

            location_stats[location] = {
                'last_date': last_date,
                'missing_count': len(missing_dates),
                'missing_dates': missing_dates
            }

            total_missing += len(missing_dates)

            print(f"📍 {location}")
            print(f"   Last prediction: {last_date}")
            print(f"   Missing days: {len(missing_dates)}")
            if missing_dates:
                print(f"   Date range: {missing_dates[0]} to {missing_dates[-1]}")
            print()

    if total_missing == 0:
        print("✅ No missing predictions found! All locations are up to date.")
        print("=" * 80)
        return

    print(f"📊 Summary: {total_missing} missing predictions across {len(locations)} locations")
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
    print("Step 2: Running inference for missing dates")
    print("-" * 80)

    # Process each location
    for location in locations:
        stats = location_stats[location]
        missing_dates = stats['missing_dates']

        if not missing_dates:
            print(f"✓ {location}: Up to date")
            continue

        print(f"📍 {location}: Processing {len(missing_dates)} missing dates...")

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
    print("Step 3: Updating risk assessments")
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
    print()

    if total_failed > 0:
        print("⚠️  Some predictions failed. Check the errors above.")
        print("   You may need to:")
        print("   - Verify historical weather data is available for those dates")
        print("   - Check model files exist for all locations")
        print("   - Run data ingestion: flood-cli data-ingestion fetch-openmeteo historical")
        sys.exit(1)
    else:
        print("✅ All missing predictions have been filled successfully!")

    print("=" * 80)


if __name__ == "__main__":
    main()
