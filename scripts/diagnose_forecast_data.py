#!/usr/bin/env python
"""
Diagnostic script to check forecast weather data in the database.
Run this on the server to understand why forecast data is missing.
"""

import sys
from datetime import datetime, timedelta

from sqlalchemy import select, func

from flood_forecaster.data_model.weather import ForecastWeather
from flood_forecaster.utils.configuration import Config
from flood_forecaster.utils.database_helper import DatabaseConnection


def main():
    """Run diagnostics on forecast weather data."""
    config = Config("config/config.ini")
    db = DatabaseConnection(config)

    print("=" * 80)
    print("FORECAST WEATHER DATA DIAGNOSTICS")
    print("=" * 80)
    print(f"Current time: {datetime.now()}")
    print()

    with db.engine.connect() as conn:
        # Get overall statistics
        total_count_stmt = select(func.count()).select_from(ForecastWeather.__table__)
        total_count = conn.execute(total_count_stmt).scalar()
        print(f"Total forecast weather records in database: {total_count}")
        print()

        # Get date range
        min_date_stmt = select(func.min(ForecastWeather.date)).select_from(ForecastWeather.__table__)
        max_date_stmt = select(func.max(ForecastWeather.date)).select_from(ForecastWeather.__table__)
        min_date = conn.execute(min_date_stmt).scalar()
        max_date = conn.execute(max_date_stmt).scalar()
        print(f"Date range in database: {min_date} to {max_date}")
        print()

        # Get location statistics
        locations_stmt = select(
            ForecastWeather.location_name,
            func.min(ForecastWeather.date).label('min_date'),
            func.max(ForecastWeather.date).label('max_date'),
            func.count().label('count')
        ).group_by(ForecastWeather.location_name).order_by(ForecastWeather.location_name)

        print("Data by location:")
        print("-" * 80)
        print(f"{'Location':<40} {'Min Date':<20} {'Max Date':<20} {'Count':<10}")
        print("-" * 80)

        for row in conn.execute(locations_stmt):
            print(f"{row.location_name:<40} {str(row.min_date):<20} {str(row.max_date):<20} {row.count:<10}")
        print()

        # Check for expected locations
        expected_locations = [
            'hiran__belet_weyne',
            'ethiopia__tullu_dimtu',
            'ethiopia__shabelle_gode',
            'ethiopia__fafen_haren',
            'ethiopia__debre_selam_arsi',
            'ethiopia__fafen_gebredarre'
        ]

        print("Status of critical locations:")
        print("-" * 80)
        for loc in expected_locations:
            loc_stmt = select(
                func.count(),
                func.max(ForecastWeather.date)
            ).where(ForecastWeather.location_name == loc)
            result = conn.execute(loc_stmt).one()
            count = result[0]
            last_date = result[1]
            status = "✅ OK" if count > 0 else "❌ MISSING"
            print(f"{status} {loc:<40} Count: {count:<6} Last: {last_date}")
        print()

        # Check recent data (last 7 days)
        today = datetime.now().date()
        week_ago = today - timedelta(days=7)
        recent_stmt = select(
            ForecastWeather.location_name,
            func.count().label('count')
        ).where(
            ForecastWeather.date >= week_ago
        ).group_by(ForecastWeather.location_name).order_by(ForecastWeather.location_name)

        print(f"Recent data (since {week_ago}):")
        print("-" * 80)
        recent_results = list(conn.execute(recent_stmt))
        if recent_results:
            for row in recent_results:
                print(f"  {row.location_name}: {row.count} records")
        else:
            print("  ❌ NO RECENT DATA FOUND!")
        print()

        # Check for data in the future
        future_stmt = select(
            func.count()
        ).where(
            ForecastWeather.date > today
        )
        future_count = conn.execute(future_stmt).scalar()
        print(f"Future forecast records (date > {today}): {future_count}")

        if future_count == 0:
            print("  ⚠️  WARNING: No future forecast data! System cannot make predictions.")
        print()

    print("=" * 80)
    print("DIAGNOSTICS COMPLETE")
    print("=" * 80)


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"ERROR: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)
