#!/usr/bin/env python3
"""
Remove duplicate river level records from the database (DATA-005).

Collapses duplicate entries in flood_forecaster.historical_river_level on
(location_name, date). Retention rule, in order:

  1. prefer a row whose level_m is not NULL over one that is NULL;
  2. then keep the highest id, i.e. the most recently ingested row.

The highest-id rule is not arbitrary. All nine value-conflicting pairs in the
2026-09-22 production snapshot were arbitrated against public.station_river_data,
and the most recently ingested value was correct in every case, three of them
correcting a whole-metre transcription error.

Run this BEFORE adding the unique constraint:
    python scripts/maintenance/remove_duplicate_historical_river_level.py --dry-run
    python scripts/maintenance/remove_duplicate_historical_river_level.py
    psql -h <host> -U postgres -d postgres \
        -f sql/add_historical_river_level_unique_constraint.sql

Usage:
    python scripts/maintenance/remove_duplicate_historical_river_level.py [--dry-run] [--yes]
"""
import argparse
import sys
from pathlib import Path

# Add src to path for imports.
# parents[2] is the repository root: scripts/maintenance/<this file>.
src_path = Path(__file__).parents[2] / "src"
sys.path.insert(0, str(src_path))

from flood_forecaster.data_ingestion.swalim.river_level_api import (
    remove_duplicates_historical_river_level_from_db,
)
from flood_forecaster.utils.configuration import Config
from flood_forecaster.utils.logging_config import get_logger

logger = get_logger(__name__)


def main():
    """Main entry point for the duplicate removal script."""
    parser = argparse.ArgumentParser(
        description="Remove duplicate river level records from the database"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Only show duplicates without removing them",
    )
    parser.add_argument(
        "--yes",
        action="store_true",
        help="Skip the interactive confirmation (for non-interactive runs)",
    )
    parser.add_argument(
        "--config",
        type=str,
        default="config/config.ini",
        help="Path to configuration file (default: config/config.ini)",
    )
    args = parser.parse_args()

    config = Config(args.config)

    if args.dry_run:
        logger.info("=" * 60)
        logger.info("DRY RUN MODE - No changes will be made to the database")
        logger.info("=" * 60)
    else:
        logger.warning("=" * 60)
        logger.warning("LIVE MODE - Duplicates will be DELETED from the database")
        logger.warning("=" * 60)
        logger.warning("Retention: non-NULL level wins, then highest id (most recent).")
        if not args.yes:
            response = input("Are you sure you want to continue? (yes/no): ")
            if response.lower() != "yes":
                logger.info("Aborted by user")
                return 1

    affected = remove_duplicates_historical_river_level_from_db(config, dry_run=args.dry_run)

    if args.dry_run:
        logger.info("\n" + "=" * 60)
        logger.info(f"Dry run complete. {affected} row(s) would be deleted.")
        logger.info("Run without --dry-run to remove duplicates.")
        logger.info("=" * 60)
    else:
        logger.info("\n" + "=" * 60)
        logger.info(f"Duplicate removal complete. {affected} row(s) deleted.")
        logger.info("=" * 60)
        logger.info("\nNext steps:")
        logger.info("1. Deploy the latest code version (uses UPSERT)")
        logger.info("2. Add the unique constraint:")
        logger.info(
            "   psql -h <host> -U postgres -d postgres "
            "-f sql/add_historical_river_level_unique_constraint.sql"
        )

    return 0


if __name__ == "__main__":
    sys.exit(main())
