#!/usr/bin/env python
"""
Force refresh of forecast weather data.
This script will:
1. Delete all existing forecast data
2. Fetch fresh forecast data from Open-Meteo API
3. Verify the data was written correctly
"""

import sys

import openmeteo_requests
import requests_cache
from requests.adapters import HTTPAdapter, Retry
from sqlalchemy import select, func

from flood_forecaster.data_ingestion.openmeteo.forecast_weather import fetch_forecast
from flood_forecaster.data_model.weather import ForecastWeather
from flood_forecaster.utils.configuration import Config
from flood_forecaster.utils.database_helper import DatabaseConnection


def retry_session():
    """Create a session with retry logic - NO CACHE for force refresh."""
    # Don't use cache for force refresh - we want fresh data!
    cache_session = requests_cache.CachedSession(".cache", expire_after=0)
    retry_strategy = Retry(
        total=5,
        backoff_factor=0.2,
        status_forcelist=[429, 500, 502, 503, 504],
    )
    adapter = HTTPAdapter(max_retries=retry_strategy)
    cache_session.mount("http://", adapter)
    cache_session.mount("https://", adapter)
    return cache_session


def main():
    """Force refresh forecast data."""
    print("=" * 80)
    print("FORCE REFRESH FORECAST WEATHER DATA")
    print("=" * 80)
    print()

    config = Config("config/config.ini")
    db = DatabaseConnection(config)

    # Step 1: Check current state
    print("Step 1: Checking current state...")
    with db.engine.connect() as conn:
        count_stmt = select(func.count()).select_from(ForecastWeather.__table__)
        current_count = conn.execute(count_stmt).scalar()

        max_date_stmt = select(func.max(ForecastWeather.date)).select_from(ForecastWeather.__table__)
        max_date = conn.execute(max_date_stmt).scalar()

        print(f"  Current records: {current_count}")
        print(f"  Latest date: {max_date}")
    print()

    # Step 2: Clear the cache
    print("Step 2: Clearing stale cache...")
    import os
    from pathlib import Path
    cache_files = [".cache", ".cache.sqlite", ".cache.sqlite-shm", ".cache.sqlite-wal"]
    for cache_file in cache_files:
        cache_path = Path(cache_file)
        if cache_path.exists():
            try:
                os.remove(cache_path)
                print(f"  Deleted cache file: {cache_file}")
            except Exception as e:
                print(f"  Warning: Could not delete {cache_file}: {e}")
    print()

    # Step 3: Clear existing forecast data
    print("Step 3: Clearing existing forecast data...")
    response = input("  Are you sure you want to delete all forecast data? (yes/no): ")
    if response.lower() != 'yes':
        print("  Aborted.")
        return

    from sqlalchemy import delete
    with db.engine.connect() as conn:
        with conn.begin():
            delete_stmt = delete(ForecastWeather.__table__)
            result = conn.execute(delete_stmt)
            print(f"  Deleted {result.rowcount} records")
    print()

    # Step 3: Fetch fresh data
    print("Step 3: Fetching fresh forecast data from Open-Meteo API...")
    try:
        session = retry_session()
        openmeteo = openmeteo_requests.Client(session=session)

        forecast_df = fetch_forecast(config, openmeteo)

        print(f"  Fetched {len(forecast_df)} records")
        if len(forecast_df) > 0:
            print(f"  Date range: {forecast_df['date'].min()} to {forecast_df['date'].max()}")
            print(f"  Locations: {forecast_df['location_name'].unique().tolist()}")
    except Exception as e:
        print(f"  ERROR during fetch: {e}")
        import traceback
        traceback.print_exc()
        return
    print()

    # Step 4: Verify data was written
    print("Step 4: Verifying data was written to database...")
    with db.engine.connect() as conn:
        count_stmt = select(func.count()).select_from(ForecastWeather.__table__)
        new_count = conn.execute(count_stmt).scalar()

        max_date_stmt = select(func.max(ForecastWeather.date)).select_from(ForecastWeather.__table__)
        new_max_date = conn.execute(max_date_stmt).scalar()

        locations_stmt = select(
            func.count(func.distinct(ForecastWeather.location_name))
        ).select_from(ForecastWeather.__table__)
        location_count = conn.execute(locations_stmt).scalar()

        print(f"  Records in database: {new_count}")
        print(f"  Latest date: {new_max_date}")
        print(f"  Unique locations: {location_count}")

        if new_count > 0:
            print("  ✅ SUCCESS: Data was written to database")
        else:
            print("  ❌ FAILURE: No data in database after fetch!")
    print()

    print("=" * 80)
    print("REFRESH COMPLETE")
    print("=" * 80)


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"ERROR: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)
