#!/usr/bin/env python
"""
Fill gaps in flood_forecaster.historical_river_level.

Two sources are supported:

  chart-api     (default) SWALIM's /rivers/graph JSON endpoint, addressed per
                station by id. Returns the current year plus the previous year
                in one call, so it can repair long gaps. Immune to the HTML
                row-position problem described in backlog item DATA-004.

  public-schema public.station_river_data, mapped through
                river_station_metadata.swalim_internal_id. This table is
                written by a host cron outside this project's control and is
                less complete than the API, so it is a fallback rather than a
                primary source. See RISK-005.

Safe by default: the script reports what it would do and writes nothing unless
you pass --apply.

USAGE
    # what is missing for Jowhar, up to today
    python scripts/fill_river_data_gaps.py --station Jowhar

    # repair the Jowhar outage for real
    python scripts/fill_river_data_gaps.py --station Jowhar \
        --from 2026-05-12 --apply

    # every station, bounded window, no prompt
    python scripts/fill_river_data_gaps.py --from 2026-01-01 --apply --yes

    # compare what the fallback source could offer
    python scripts/fill_river_data_gaps.py --station Jowhar --source public-schema

Requires POSTGRES_PASSWORD in the environment (see config/config.ini).

After filling gaps, recompute the affected predictions:
    python scripts/catchup_missing_predictions.py
"""

import argparse
import sys
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple

from sqlalchemy import text

# Add the src directory to the path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from flood_forecaster.utils.configuration import Config
from flood_forecaster.utils.database_helper import DatabaseConnection

SOURCE_CHART_API = "chart-api"
SOURCE_PUBLIC = "public-schema"


# --------------------------------------------------------------------------- #
# arguments
# --------------------------------------------------------------------------- #
def _parse_date(value: str) -> date:
    try:
        return datetime.strptime(value, "%Y-%m-%d").date()
    except ValueError:
        raise argparse.ArgumentTypeError(f"expected YYYY-MM-DD, got {value!r}")


def parse_args(argv: Optional[List[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Fill gaps in flood_forecaster.historical_river_level.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="Dry run by default. Pass --apply to write.",
    )
    parser.add_argument(
        "--station", action="append", dest="stations", metavar="NAME",
        help="Station to process; repeatable. Default: every mapped station.",
    )
    parser.add_argument(
        "--from", dest="date_from", type=_parse_date, metavar="YYYY-MM-DD",
        help="Start of the window. Default: the station's earliest existing row.",
    )
    parser.add_argument(
        "--to", dest="date_to", type=_parse_date, metavar="YYYY-MM-DD",
        help="End of the window. Default: today, so trailing gaps are visible.",
    )
    parser.add_argument(
        "--source", choices=[SOURCE_CHART_API, SOURCE_PUBLIC], default=SOURCE_CHART_API,
        help=f"Where to read readings from. Default: {SOURCE_CHART_API}.",
    )
    parser.add_argument(
        "--apply", action="store_true",
        help="Actually insert the rows. Without this nothing is written.",
    )
    parser.add_argument(
        "--yes", action="store_true",
        help="Skip the confirmation prompt when using --apply.",
    )
    parser.add_argument(
        "--config", type=Path, default=None,
        help="Path to config.ini. Default: ../config/config.ini",
    )
    parser.add_argument(
        "--max-listed", type=int, default=12, metavar="N",
        help="How many individual dates to list per station. Default: 12.",
    )

    args = parser.parse_args(argv)
    if args.date_from and args.date_to and args.date_from > args.date_to:
        parser.error(f"--from ({args.date_from}) is after --to ({args.date_to})")
    return args


# --------------------------------------------------------------------------- #
# database reads
# --------------------------------------------------------------------------- #
def get_station_mapping(conn) -> Dict[str, int]:
    """station_name -> swalim_internal_id, for stations that have one."""
    rows = conn.execute(text("""
        SELECT station_name, swalim_internal_id
        FROM flood_forecaster.river_station_metadata
        WHERE swalim_internal_id IS NOT NULL
        ORDER BY station_name
    """))
    return {row[0]: row[1] for row in rows}


def get_existing_range(conn, location: str) -> Tuple[Optional[date], Optional[date], int]:
    """(first_date, last_date, row_count) currently stored for a location."""
    row = conn.execute(text("""
        SELECT MIN(date), MAX(date), COUNT(*)
        FROM flood_forecaster.historical_river_level
        WHERE location_name = :location
    """), {"location": location}).fetchone()
    if row and row[0]:
        return row[0], row[1], row[2]
    return None, None, 0


def get_existing_dates(conn, location: str, start: date, end: date) -> Set[date]:
    """
    Dates already holding a usable reading in [start, end].

    A row whose level_m IS NULL is deliberately treated as absent: the loader
    drops NULL levels before building features, so such a row occupies the date
    without being usable. Counting it as present would leave the gap unfixed.
    """
    rows = conn.execute(text("""
        SELECT date
        FROM flood_forecaster.historical_river_level
        WHERE location_name = :location
          AND date BETWEEN :start AND :end
          AND level_m IS NOT NULL
    """), {"location": location, "start": start, "end": end})
    return {row[0] for row in rows}


def resolve_window(
    conn, location: str, arg_from: Optional[date], arg_to: Optional[date]
) -> Tuple[Optional[date], Optional[date], Optional[str]]:
    """
    Decide the window to inspect for a station.

    --to defaults to TODAY rather than to the newest stored row. The previous
    behaviour bounded the search by MAX(date), which made a trailing gap
    structurally invisible: a station that stopped reporting looked continuous.
    That is exactly how the Jowhar outage went unnoticed.
    """
    first, last, _ = get_existing_range(conn, location)
    end = arg_to or date.today()

    if arg_from is not None:
        start = arg_from
    elif first is not None:
        start = first
    else:
        return None, None, "no existing rows; pass --from to choose a start date"

    if start > end:
        return None, None, f"window is empty ({start} > {end})"
    return start, end, None


def identify_gaps(existing: Set[date], start: date, end: date) -> List[date]:
    missing, current = [], start
    while current <= end:
        if current not in existing:
            missing.append(current)
        current += timedelta(days=1)
    return missing


# --------------------------------------------------------------------------- #
# sources
# --------------------------------------------------------------------------- #
def fetch_from_public_schema(conn, swalim_id: int, start: date, end: date) -> Dict[date, float]:
    """
    Readings from public.station_river_data for one SWALIM id.

    Note: the previous implementation ordered by a column named "date", which
    does not exist on this table (it is "reading_date"). Every call raised, the
    error was swallowed by a bare except, and the function always returned an
    empty list - so the script could never fill anything.
    """
    rows = conn.execute(text("""
        SELECT reading_date, reading
        FROM public.station_river_data
        WHERE station_id = :station_id
          AND reading_date BETWEEN :start AND :end
          AND reading IS NOT NULL
        ORDER BY reading_date
    """), {"station_id": swalim_id, "start": start, "end": end})
    return {row[0]: float(row[1]) for row in rows}


def fetch_from_chart_api(config: Config, station: str, start: date, end: date) -> Dict[date, float]:
    """
    Readings from SWALIM's /rivers/graph endpoint, restricted to [start, end].

    The response carries the current year in 'readingvalue' and the same
    calendar day one year earlier in 'previousreadingvalue', so a single call
    can cover roughly two years. Both are used, matching the reconciliation the
    CSV loader already performs.
    """
    import pandas as pd
    from flood_forecaster.data_ingestion.swalim.river_level_api import (
        fetch_river_data_from_chart_api,
    )

    df = fetch_river_data_from_chart_api(config, station)
    if df is None or df.empty:
        return {}

    readings: Dict[date, float] = {}

    def absorb(frame, value_col, year_offset: int) -> None:
        if value_col not in frame.columns:
            return
        subset = frame[["date", value_col]].copy()
        subset[value_col] = pd.to_numeric(subset[value_col], errors="coerce")
        subset = subset.dropna(subset=["date", value_col])
        for row in subset.itertuples(index=False):
            day = row.date
            day = day.date() if hasattr(day, "date") else day
            if year_offset:
                try:
                    day = day.replace(year=day.year + year_offset)
                except ValueError:
                    continue  # 29 Feb with no counterpart in the shifted year
            if start <= day <= end:
                readings[day] = float(getattr(row, value_col))

    # Current year takes precedence over the previous-year echo.
    absorb(df, "previousreadingvalue", -1)
    absorb(df, "readingvalue", 0)
    return readings


# --------------------------------------------------------------------------- #
# database write
# --------------------------------------------------------------------------- #
def insert_rows(conn, location: str, rows: List[Tuple[date, float]]) -> int:
    """
    Insert readings, skipping dates already present.

    Returns the number of rows the database actually accepted, taken from
    rowcount. The previous implementation incremented a counter per attempt, so
    conflicts were reported as successful inserts.
    """
    if not rows:
        return 0
    statement = text("""
        INSERT INTO flood_forecaster.historical_river_level (location_name, date, level_m)
        VALUES (:location, :date, :level)
        ON CONFLICT DO NOTHING
    """)
    inserted = 0
    for day, level in rows:
        result = conn.execute(statement, {"location": location, "date": day, "level": level})
        inserted += result.rowcount if result.rowcount and result.rowcount > 0 else 0
    return inserted


# --------------------------------------------------------------------------- #
# main
# --------------------------------------------------------------------------- #
def resolve_targets(
    mapping: Dict[str, int], requested: Optional[List[str]]
) -> Tuple[List[str], Optional[str]]:
    """Validate the requested station names against the mapping."""
    if not requested:
        return sorted(mapping), None
    unknown = [s for s in requested if s not in mapping]
    if unknown:
        return [], (
            f"Unknown station(s): {', '.join(unknown)}\n"
            f"   Available: {', '.join(sorted(mapping))}"
        )
    return list(requested), None


def describe_gaps(gaps: List[date], max_listed: int) -> str:
    if len(gaps) <= max_listed:
        return ', '.join(d.isoformat() for d in gaps)
    head = ', '.join(d.isoformat() for d in gaps[:3])
    tail = ', '.join(d.isoformat() for d in gaps[-3:])
    return f"{head} ... {tail}"


def analyse_station(conn, config: Config, station: str, swalim_id: int, args) -> dict:
    """
    Work out what is missing for one station and what the chosen source can
    supply. Prints its own progress. Returns a summary dict:

        gaps              number of missing days in the window
        fillable          [(date, level)] ready to insert
        missing_in_source days with no reading available
        skipped           reason string, or None
    """
    blank = {"gaps": 0, "fillable": [], "missing_in_source": 0, "skipped": None}
    print(f"\n📍 {station}  (SWALIM id {swalim_id})")

    start, end, problem = resolve_window(conn, station, args.date_from, args.date_to)
    if problem:
        print(f"   ⏭️  skipped: {problem}")
        return {**blank, "skipped": problem}

    existing = get_existing_dates(conn, station, start, end)
    gaps = identify_gaps(existing, start, end)
    print(f"   window {start} .. {end}  ({(end - start).days + 1} days)")
    print(f"   usable readings stored: {len(existing)}")

    if not gaps:
        print("   ✅ no gaps")
        return blank

    print(f"   ⚠️  missing: {len(gaps)} day(s)")
    print(f"      {describe_gaps(gaps, args.max_listed)}")

    try:
        if args.source == SOURCE_PUBLIC:
            available = fetch_from_public_schema(conn, swalim_id, start, end)
        else:
            available = fetch_from_chart_api(config, station, start, end)
    except Exception as exc:  # noqa: BLE001 - report and carry on with other stations
        print(f"   ❌ source error: {type(exc).__name__}: {exc}")
        return {**blank, "gaps": len(gaps), "missing_in_source": len(gaps),
                "skipped": f"source error: {exc}"}

    fillable = [(d, available[d]) for d in gaps if d in available]
    missing_in_source = len(gaps) - len(fillable)
    print(f"   source offers {len(available)} reading(s) in window; "
          f"{len(fillable)} match a gap, {missing_in_source} unavailable")

    return {"gaps": len(gaps), "fillable": fillable,
            "missing_in_source": missing_in_source, "skipped": None}


def main(argv: Optional[List[str]] = None) -> int:
    args = parse_args(argv)

    config_path = args.config or (Path(__file__).parent.parent / "config" / "config.ini")
    if not config_path.exists():
        print(f"❌ Configuration file not found at {config_path}")
        return 1

    config = Config(str(config_path))
    db = DatabaseConnection(config)

    print("=" * 78)
    print("FILL GAPS IN HISTORICAL RIVER LEVEL DATA")
    print("=" * 78)
    print(f"Source : {args.source}")
    print(f"Window : {args.date_from or '(earliest stored)'} .. {args.date_to or 'today'}")
    print(f"Mode   : {'APPLY - rows will be written' if args.apply else 'DRY RUN - nothing will be written'}")
    print()

    with db.engine.connect() as conn:
        mapping = get_station_mapping(conn)
        if not mapping:
            print("❌ No station mapping found in flood_forecaster.river_station_metadata.")
            print("   Check that swalim_internal_id is populated.")
            return 1

        targets, error = resolve_targets(mapping, args.stations)
        if error:
            print(f"❌ {error}")
            return 1

        print(f"Stations: {', '.join(targets)}")
        print("-" * 78)

        plan: Dict[str, List[Tuple[date, float]]] = {}
        total_gaps = 0
        total_available = 0
        unavailable: Dict[str, int] = {}

        for station in targets:
            outcome = analyse_station(conn, config, station, mapping[station], args)
            total_gaps += outcome["gaps"]
            total_available += len(outcome["fillable"])
            if outcome["missing_in_source"]:
                unavailable[station] = outcome["missing_in_source"]
            if outcome["fillable"]:
                plan[station] = outcome["fillable"]

        print()
        print("=" * 78)
        print(f"Gaps found         : {total_gaps}")
        print(f"Fillable from source: {total_available}")
        if unavailable:
            print(f"Not in source      : {sum(unavailable.values())} "
                  f"({', '.join(f'{k}: {v}' for k, v in sorted(unavailable.items()))})")
        print("=" * 78)

        if not plan:
            print("\nNothing to insert.")
            if total_gaps and args.source == SOURCE_CHART_API:
                print("Gaps exist but the API had no reading for those dates.")
                print(f"Try --source {SOURCE_PUBLIC} to see whether the fallback table has them.")
            return 0

        if not args.apply:
            print("\nDry run. Re-run with --apply to insert the rows above.")
            return 0

        if not args.yes:
            print(f"\n⚠️  About to insert {total_available} row(s) into "
                  f"flood_forecaster.historical_river_level.")
            if input("Proceed? (yes/no): ").strip().lower() != "yes":
                print("Cancelled.")
                return 0

    # Single transaction: either the whole backfill lands or none of it does.
    print("\nInserting...")
    inserted_total = 0
    with db.engine.begin() as conn:
        for station, rows in plan.items():
            inserted = insert_rows(conn, station, rows)
            inserted_total += inserted
            skipped = len(rows) - inserted
            suffix = f" ({skipped} already present)" if skipped else ""
            print(f"   {station}: inserted {inserted}{suffix}")

    print()
    print("=" * 78)
    print(f"✅ Inserted {inserted_total} row(s).")
    print("=" * 78)
    print("\nNext steps:")
    print("  1. Re-run this script without --apply to confirm the gaps are closed.")
    print("  2. python scripts/catchup_missing_predictions.py   # recompute predictions")
    return 0


if __name__ == "__main__":
    sys.exit(main())
