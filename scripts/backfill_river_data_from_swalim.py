#!/usr/bin/env python
"""
Backfill historical river level data by fetching from the SWALIM chart API.

Use this when fill_river_data_gaps.py cannot help (e.g. the public.station_river_data
table does not have the missing dates) and you need to pull data directly from the
SWALIM external API.

This script:
1. Shows which stations are missing data (and how many days)
2. For each selected station, calls:
     flood-cli data-ingestion fetch-river-data-from-chart-api <station>
   which downloads the full history as a CSV into data/raw/swalim/
3. Then calls:
     flood-cli data-ingestion fetch-river-data-from-csv <station> --swalim-file <csv>
   to load that CSV into flood_forecaster.historical_river_level

Known limitations of the SWALIM chart API:
  - readingValue can be null for dates that haven't been entered yet → those dates are
    silently dropped (NaN → dropna). Run check_river_data_availability.py afterwards to
    verify how many dates were actually filled.
  - Leap-year dates (29-02) in non-leap years are silently skipped.

Prerequisites:
  - flood-cli installed and available in PATH
  - POSTGRES_PASSWORD set in .env
  - Network access to https://frrims.faoswalim.org
"""

import subprocess
import sys
from pathlib import Path

# Add the src directory to the path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from sqlalchemy import text

from flood_forecaster.utils.configuration import Config
from flood_forecaster.utils.database_helper import DatabaseConnection
from flood_forecaster.data_ingestion.swalim.river_level_api import get_latest_swalim_river_csv


# ── helpers ──────────────────────────────────────────────────────────────────

def get_gap_summary(conn) -> dict[str, dict]:
    """Return per-station gap info: {station: {first, last, records, expected, gaps}}"""
    query = text("""
                 SELECT location_name,
                        MIN(date) AS first_date,
                        MAX(date) AS last_date,
                        COUNT(*)  AS records
                 FROM flood_forecaster.historical_river_level
                 GROUP BY location_name
                 ORDER BY location_name
                 """)
    rows = conn.execute(query).fetchall()

    summary = {}
    for row in rows:
        name, first, last, records = row
        expected = (last - first).days + 1
        summary[name] = {
            "first": first,
            "last": last,
            "records": records,
            "expected": expected,
            "gaps": expected - records,
        }
    return summary


def run(cmd: str) -> bool:
    """Run a shell command, stream output, return True on success."""
    print(f"\n  ▶ {cmd}")
    result = subprocess.run(cmd, shell=True)
    if result.returncode != 0:
        print(f"  ❌ Command failed (exit {result.returncode})")
        return False
    print(f"  ✅ Done")
    return True


# ── main ─────────────────────────────────────────────────────────────────────

def main():
    print("=" * 80)
    print("BACKFILL RIVER DATA FROM SWALIM CHART API")
    print("=" * 80)
    print()
    print("⚠️  Note: SWALIM may return null for dates not yet entered. Those dates")
    print("    will be silently dropped. Run check_river_data_availability.py")
    print("    afterwards to verify results.")
    print()

    config_path = Path(__file__).parent.parent / "config" / "config.ini"
    if not config_path.exists():
        print(f"❌ Config not found at {config_path}")
        sys.exit(1)

    config = Config(str(config_path))
    db = DatabaseConnection(config)

    # ── Step 1: Show gap summary ──────────────────────────────────────────────
    print("Step 1: Current data gaps")
    print("-" * 80)
    with db.engine.connect() as conn:
        gaps = get_gap_summary(conn)

    if not gaps:
        print("  No data found in historical_river_level at all.")
        print("  Consider running fetch-river-data-from-csv with SNRFA data first.")
        sys.exit(0)

    stations_with_gaps = []
    for name, info in gaps.items():
        if info["gaps"] > 0:
            print(f"  📍 {name}: {info['gaps']} missing days "
                  f"(range {info['first']} → {info['last']}, "
                  f"{info['records']}/{info['expected']} records)")
            stations_with_gaps.append(name)
        else:
            print(f"  ✅ {name}: no gaps detected")

    if not stations_with_gaps:
        print("\n✅ No gaps found. Nothing to do.")
        sys.exit(0)

    print()

    # ── Step 2: Select stations ───────────────────────────────────────────────
    print("Step 2: Select stations to backfill")
    print("-" * 80)
    for i, name in enumerate(stations_with_gaps, 1):
        print(f"  {i}. {name}")
    print()
    selection = input("  Enter numbers separated by commas, or 'all': ").strip()

    if selection.lower() == "all":
        selected = stations_with_gaps
    else:
        try:
            indices = [int(x.strip()) - 1 for x in selection.split(",")]
            selected = [stations_with_gaps[i] for i in indices]
        except (ValueError, IndexError):
            print("❌ Invalid selection.")
            sys.exit(1)

    print(f"\n  Selected: {', '.join(selected)}")
    confirm = input("\n  Proceed? This will call the SWALIM API and update the DB. (yes/no): ").strip()
    if confirm.lower() != "yes":
        print("Aborted.")
        sys.exit(0)

    # ── Step 3: Fetch + load per station ─────────────────────────────────────
    print()
    print("Step 3: Fetch from SWALIM chart API and load into DB")
    print("-" * 80)

    success, failed = [], []

    for station in selected:
        print(f"\n📍 {station}")

        # 3a. Download from SWALIM chart API → CSV
        ok = run(f'flood-cli data-ingestion fetch-river-data-from-chart-api "{station}"')
        if not ok:
            failed.append(station)
            continue

        # 3b. Locate the just-created CSV
        try:
            csv_path = get_latest_swalim_river_csv(config, station)
            print(f"  📄 CSV: {csv_path}")
        except FileNotFoundError as e:
            print(f"  ❌ Could not find CSV: {e}")
            failed.append(station)
            continue

        # 3c. Load CSV into DB
        ok = run(f'flood-cli data-ingestion fetch-river-data-from-csv "{station}" --swalim-file "{csv_path}"')
        if ok:
            success.append(station)
        else:
            failed.append(station)

    # ── Step 4: Summary ───────────────────────────────────────────────────────
    print()
    print("=" * 80)
    print("BACKFILL COMPLETE")
    print("=" * 80)
    print(f"  ✅ Succeeded: {len(success)} station(s): {', '.join(success) if success else '—'}")
    print(f"  ❌ Failed:    {len(failed)} station(s): {', '.join(failed) if failed else '—'}")
    print()
    print("Next steps:")
    print("  1. Verify:  python scripts/check_river_data_availability.py")
    print("  2. Catchup: python scripts/catchup_missing_predictions.py")
    print("=" * 80)


if __name__ == "__main__":
    main()
