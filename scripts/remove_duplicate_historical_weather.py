#!/usr/bin/env python3
"""
Remove duplicate historical weather records from the database.

This script identifies and removes duplicate entries in the historical_weather table
based on (location_name, date) combination. It keeps the most recent record (highest ID)
and removes older duplicates.

This should be run BEFORE adding the unique constraint to the historical_weather table.

Usage:
    python scripts/remove_duplicate_historical_weather.py [--dry-run]
"""
import argparse
import sys
from pathlib import Path

# Add src to path for imports
src_path = Path(__file__).parent.parent / "src"
sys.path.insert(0, str(src_path))

from flood_forecaster.data_ingestion.openmeteo.historical_weather import (
    remove_duplicates_historical_weather_from_db,
)
from flood_forecaster.utils.configuration import Config
from flood_forecaster.utils.logging_config import get_logger

logger = get_logger(__name__)


def main():
    """Main entry point for the duplicate removal script."""
    parser = argparse.ArgumentParser(
        description="Remove duplicate historical weather records from the database"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Only show duplicates without removing them",
    )
    parser.add_argument(
        "--config",
        type=str,
        default="config/config.ini",
        help="Path to configuration file (default: config/config.ini)",
    )
    args = parser.parse_args()

    # Load configuration
    config = Config(args.config)

    if args.dry_run:
        logger.info("=" * 60)
        logger.info("DRY RUN MODE - No changes will be made to the database")
        logger.info("=" * 60)
    else:
        logger.warning("=" * 60)
        logger.warning("LIVE MODE - Duplicates will be DELETED from the database")
        logger.warning("=" * 60)
        response = input("Are you sure you want to continue? (yes/no): ")
        if response.lower() != "yes":
            logger.info("Aborted by user")
            return

    # Run the duplicate removal
    remove_duplicates_historical_weather_from_db(config, dry_run=args.dry_run)

    if args.dry_run:
        logger.info("\n" + "=" * 60)
        logger.info("Dry run complete. Run without --dry-run to remove duplicates.")
        logger.info("=" * 60)
    else:
        logger.info("\n" + "=" * 60)
        logger.info("Duplicate removal complete!")
        logger.info("=" * 60)
        logger.info("\nNext steps:")
        logger.info("1. Deploy the latest code version (uses UPSERT)")
        logger.info("2. Add the unique constraint:")
        logger.info("   psql -h <host> -U postgres -d postgres -f sql/add_historical_weather_unique_constraint.sql")


if __name__ == "__main__":
    main()
