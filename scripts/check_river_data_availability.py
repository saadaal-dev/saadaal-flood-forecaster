#!/usr/bin/env python
"""
Check available historical river level data in the database.
Use this to determine the valid date range for catchup_missing_predictions.py
"""

import sys
from datetime import date
from pathlib import Path

from sqlalchemy import select, func, text

# Add the src directory to the path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from flood_forecaster.utils.configuration import Config
from flood_forecaster.utils.database_helper import DatabaseConnection
from flood_forecaster.data_model.river_level import HistoricalRiverLevel


def main():
    """Check available river level data."""
    print("=" * 80)
    print("HISTORICAL RIVER LEVEL DATA AVAILABILITY")
    print("=" * 80)
    print()

    # Configuration
    config_path = Path(__file__).parent.parent / "config" / "config.ini"
    if not config_path.exists():
        print(f"❌ Configuration file not found at {config_path}")
        sys.exit(1)

    config = Config(str(config_path))
    db = DatabaseConnection(config)

    with db.engine.connect() as conn:
        # Get overall statistics
        print("📊 Overall Statistics")
        print("-" * 80)

        total_count = conn.execute(
            select(func.count()).select_from(HistoricalRiverLevel.__table__)
        ).scalar()
        print(f"Total records: {total_count:,}")

        if total_count == 0:
            print()
            print("⚠️  No river level data found in database!")
            print("   You cannot run catchup_missing_predictions.py without river data.")
            print("   The ML models require historical river levels as input.")
            print()
            sys.exit(1)

        min_date = conn.execute(
            select(func.min(HistoricalRiverLevel.date)).select_from(HistoricalRiverLevel.__table__)
        ).scalar()
        max_date = conn.execute(
            select(func.max(HistoricalRiverLevel.date)).select_from(HistoricalRiverLevel.__table__)
        ).scalar()

        print(f"Overall date range: {min_date} to {max_date}")
        print()

        # Get per-location statistics
        print("📍 Data Availability by Location")
        print("-" * 80)
        print(f"{'Location':<30} {'First Date':<15} {'Last Date':<15} {'Records':<10} {'Days':<10}")
        print("-" * 80)

        query = text("""
                     SELECT location_name,
                            MIN(date)               as first_date,
                            MAX(date)               as last_date,
                            COUNT(*)                as record_count,
                            (MAX(date) - MIN(date)) as date_range
                     FROM flood_forecaster.historical_river_level
                     GROUP BY location_name
                     ORDER BY location_name
                     """)

        results = conn.execute(query)
        location_data = []

        for row in results:
            location = row[0]
            first_date = row[1]
            last_date = row[2]
            count = row[3]
            days = row[4] if row[4] is not None else 0

            location_data.append({
                'location': location,
                'first_date': first_date,
                'last_date': last_date,
                'count': count,
                'days': days
            })

            print(f"{location:<30} {first_date!s:<15} {last_date!s:<15} {count:<10,} {days:<10}")

        print()

        # Check for data gaps
        print("🔍 Checking for data gaps...")
        print("-" * 80)

        has_gaps = False
        for loc in location_data:
            location = loc['location']
            first_date = loc['first_date']
            last_date = loc['last_date']
            count = loc['count']
            expected_days = (last_date - first_date).days + 1

            if count < expected_days:
                gap_days = expected_days - count
                if not has_gaps:
                    print("⚠️  DATA GAPS DETECTED:")
                    has_gaps = True
                print(f"   {location}: {gap_days} missing days between {first_date} and {last_date}")
                print(f"      Expected {expected_days} records, found {count}")

        if has_gaps:
            print()
            print("❌ CRITICAL: River data has gaps! Catchup will FAIL for gap periods.")
            print("   The ML model requires continuous daily data.")
            print("   You can only catch up for dates with complete data.")
            print()
        else:
            print("✅ No gaps detected - river data is continuous")
            print()

        print("=" * 80)
        print("RECOMMENDATIONS FOR CATCHUP SCRIPT")
        print("=" * 80)
        print()

        # Find the safe date range (where ALL locations have data)
        if location_data:
            latest_start = max(loc['first_date'] for loc in location_data)
            earliest_end = min(loc['last_date'] for loc in location_data)

            if has_gaps:
                print("⚠️  Due to data gaps, recommendations are LIMITED:")
                print()
                print("   Option 1: Catch up ONLY recent dates (where data is complete)")
                print(f"      Start from: {earliest_end} (last available data)")
                print(f"      This will only catch up from yesterday/today forward")
                print()
                print("   Option 2: Skip gap periods (NOT RECOMMENDED - will have prediction gaps)")
                print(f"      Can try: {latest_start} but will fail during gap periods")
                print()
            else:
                print("✅ Safe Date Range (all locations have data):")
                print(f"   Start from: {latest_start} or later")
                print(f"   Up to: {earliest_end} (or today if more recent)")
                print()

            # Check for locations with limited data
            today = date.today()
            recent_threshold = 30  # days

            limited_data_locations = [
                loc for loc in location_data
                if loc['days'] < recent_threshold
            ]

            if limited_data_locations:
                print("⚠️  Locations with limited data (< 30 days):")
                for loc in limited_data_locations:
                    print(f"   - {loc['location']}: {loc['days']} days of data")
                print()

            # Check for outdated data
            outdated_locations = [
                loc for loc in location_data
                if (today - loc['last_date']).days > 7
            ]

            if outdated_locations:
                print("⚠️  Locations with outdated data (last update > 7 days ago):")
                for loc in outdated_locations:
                    days_old = (today - loc['last_date']).days
                    print(f"   - {loc['location']}: Last update {days_old} days ago ({loc['last_date']})")
                print()
                print("   Consider running: flood-cli data-ingestion fetch-river-data")
                print()

        print("💡 Usage Example:")
        print()
        print("   python scripts/catchup_missing_predictions.py")
        print(f"   # When prompted, enter start date: {latest_start}")
        print()
        print("=" * 80)


if __name__ == "__main__":
    main()
