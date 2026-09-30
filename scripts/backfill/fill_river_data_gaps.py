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

WHAT GETS WRITTEN

Without --overwrite the script is insert-only. It looks for dates in the window
that hold no usable reading and inserts the ones the source can supply. A date
that already has a reading is left alone even if the source now disagrees with
it, because upstream corrections are not always improvements and silently
rewriting stored history is not a safe default.

With --overwrite it also rewrites readings that disagree with the source:

  missing     no row for that date            -> INSERT
  placeholder a row exists with level_m NULL  -> UPDATE that row
  changed     a row exists with a different
              level_m                         -> UPDATE that row
  unchanged   stored value matches the source -> left alone

"Different" means the two values differ by more than LEVEL_TOLERANCE_M, so
floating-point representation noise does not count as a change.

Note the placeholder case. A NULL-level row holds no usable reading, so both modes
repair it by filling that row in place; neither creates a second row for the date.
DATA-005 enforces one row per (location_name, date), so a duplicate insert is
rejected by the database rather than silently accepted as it was before. Against a
database where duplicate rows still exist for a date, --overwrite converges all of
them onto the source value.

--overwrite obeys the dry run: combine it with no --apply to see exactly which
readings would change, printed as "old -> new" per date.

USAGE
    # what is missing for Jowhar, up to today
    python scripts/backfill/fill_river_data_gaps.py --station Jowhar

    # repair the Jowhar outage for real
    python scripts/backfill/fill_river_data_gaps.py --station Jowhar \
        --from 2026-05-12 --apply

    # every station, bounded window, no prompt
    python scripts/backfill/fill_river_data_gaps.py --from 2026-01-01 --apply --yes

    # compare what the fallback source could offer
    python scripts/backfill/fill_river_data_gaps.py --station Jowhar --source public-schema

    # backfill since May 2026 AND replace readings that disagree with the
    # source; inspect first, then apply
    python scripts/backfill/fill_river_data_gaps.py --from 2026-05-01 --overwrite
    python scripts/backfill/fill_river_data_gaps.py --from 2026-05-01 --overwrite --apply

Requires POSTGRES_PASSWORD in the environment (see config/config.ini).

Take a database snapshot before using --overwrite: it is the only mode that can
destroy a stored reading, and the previous value is not recorded anywhere.

After filling gaps, recompute the affected predictions:
    python scripts/backfill/catchup_missing_predictions.py
"""

import argparse
import sys
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Dict, List, NamedTuple, Optional, Set, Tuple

from sqlalchemy import text

# Add the src directory to the path.
# parents[2] is the repository root: scripts/backfill/<this file>.
sys.path.insert(0, str(Path(__file__).parents[2] / "src"))

from flood_forecaster.utils.configuration import Config
from flood_forecaster.utils.database_helper import DatabaseConnection

SOURCE_CHART_API = "chart-api"
SOURCE_PUBLIC = "public-schema"

# Two readings closer than this are treated as the same value under --overwrite.
# level_m is DOUBLE PRECISION and the sources publish centimetre precision, so a
# millimetre threshold keeps real corrections while ignoring float noise (e.g. a
# stored 0.44999999999999996 against a fetched 0.45).
LEVEL_TOLERANCE_M = 0.001


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
        "--overwrite", action="store_true",
        help=(
            "Also replace stored readings that disagree with the source, and "
            "repair NULL-level rows in place instead of inserting alongside "
            "them. Destructive: the previous value is not kept. Without this "
            "flag the script only fills dates that have no usable reading."
        ),
    )
    parser.add_argument(
        "--apply", action="store_true",
        help="Actually write the rows. Without this nothing is written.",
    )
    parser.add_argument(
        "--yes", action="store_true",
        help="Skip the confirmation prompt when using --apply.",
    )
    parser.add_argument(
        "--config", type=Path, default=None,
        help="Path to config.ini. Default: <repo root>/config/config.ini",
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
    """
    (first_date, last_date, covered_days) currently stored for a location.

    Counts DISTINCT dates, not rows. Coverage measured as COUNT(*) over-reports
    wherever duplicates exist and can make a station look complete when it is not
    (DATA-005).
    """
    row = conn.execute(text("""
        SELECT MIN(date), MAX(date), COUNT(DISTINCT date)
        FROM flood_forecaster.historical_river_level
        WHERE location_name = :location
    """), {"location": location}).fetchone()
    if row and row[0]:
        return row[0], row[1], row[2]
    return None, None, 0


def get_existing_levels(conn, location: str, start: date, end: date) -> Dict[date, Optional[float]]:
    """
    Every date in [start, end] that has at least one row, mapped to its stored
    reading. The value is None when rows exist for the date but all of them have
    a NULL level_m.

    The GROUP BY is retained even though DATA-005 now enforces one row per
    (location_name, date): it makes the query correct against a database where the
    constraint has not yet been applied, and MAX() ignores NULLs, so a date holding
    both a NULL placeholder and a real reading reports the real one.

    A NULL-level row counts as "present but unusable" rather than "absent": the
    loader drops NULL levels before building features, so such a row occupies the
    date without being usable. identify_gaps() therefore treats it as a gap, and
    insert_rows() repairs it by filling the placeholder in place.
    """
    rows = conn.execute(text("""
        SELECT date, MAX(level_m) AS level
        FROM flood_forecaster.historical_river_level
        WHERE location_name = :location
          AND date BETWEEN :start AND :end
        GROUP BY date
    """), {"location": location, "start": start, "end": end})
    return {row[0]: (float(row[1]) if row[1] is not None else None) for row in rows}


def usable_dates(existing: Dict[date, Optional[float]]) -> Set[date]:
    """Dates from get_existing_levels() that hold a reading the loader can use."""
    return {day for day, level in existing.items() if level is not None}


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
    Fill dates that hold no usable reading: no row at all, or a NULL placeholder.

    Returns the number of rows the database actually accepted, taken from
    rowcount. The previous implementation incremented a counter per attempt, so
    conflicts were reported as successful inserts.

    DATA-005 added uq_historical_river_level_location_date on
    (location_name, date), which changes what this statement has to do. Before the
    constraint, a date carrying a NULL placeholder was repaired by inserting a
    *second* row for the same date, and the bare `ON CONFLICT DO NOTHING` could
    never fire because there was no index to detect a conflict against. With the
    constraint in place that second insert would be rejected, so a plain
    DO NOTHING would silently leave every placeholder date unrepaired — and NULL
    levels are not rare.

    So the conflict action fills the placeholder in place, guarded by
    `WHERE historical_river_level.level_m IS NULL`. That keeps the insert-only
    contract intact: a date that already holds a real reading is still left
    untouched even when the source disagrees, because rewriting stored history is
    --overwrite's job, not gap repair's. Filling a NULL is not rewriting history;
    by this script's own definition that date holds no reading.
    """
    if not rows:
        return 0
    statement = text("""
        INSERT INTO flood_forecaster.historical_river_level (location_name, date, level_m)
        VALUES (:location, :date, :level)
        ON CONFLICT (location_name, date) DO UPDATE
            SET level_m = EXCLUDED.level_m
            WHERE historical_river_level.level_m IS NULL
    """)
    inserted = 0
    for day, level in rows:
        result = conn.execute(statement, {"location": location, "date": day, "level": level})
        inserted += result.rowcount if result.rowcount and result.rowcount > 0 else 0
    return inserted


def update_rows(conn, location: str, rows: List[Tuple[date, Optional[float], float]]) -> int:
    """
    Overwrite the stored reading for dates that already have a row.

    Takes (date, old_level, new_level) triples; old_level is carried for
    reporting only and is not used in the statement.

    The `level_m IS DISTINCT FROM :level` guard makes the statement idempotent,
    so re-running writes nothing and the returned rowcount is the number of rows
    actually changed rather than examined. IS DISTINCT FROM rather than `<>`
    because `NULL <> 0.5` evaluates to NULL, not true, which would skip exactly
    the placeholder rows this mode exists to repair.

    The WHERE clause is deliberately not restricted to a single row. DATA-005 now
    enforces one row per (location_name, date), but against a database where the
    constraint has not yet been applied every duplicate row for that date
    converges on the source value.
    """
    if not rows:
        return 0
    statement = text("""
        UPDATE flood_forecaster.historical_river_level
        SET level_m = :level
        WHERE location_name = :location
          AND date = :date
          AND level_m IS DISTINCT FROM :level
    """)
    updated = 0
    for day, _old, level in rows:
        result = conn.execute(statement, {"location": location, "date": day, "level": level})
        updated += result.rowcount if result.rowcount and result.rowcount > 0 else 0
    return updated


def classify_changes(
    existing: Dict[date, Optional[float]],
    available: Dict[date, float],
) -> Tuple[List[Tuple[date, float]], List[Tuple[date, Optional[float], float]]]:
    """
    Split what the source offers into inserts and updates. Only used under
    --overwrite; without that flag every gap is an insert and stored readings are
    never compared.

    Returns (to_insert, to_update):

      to_insert  [(date, level)]                 no row exists for the date
      to_update  [(date, old_level, new_level)]  a row exists and either holds
                                                 NULL or a value differing by
                                                 more than LEVEL_TOLERANCE_M

    Dates whose stored value already matches the source appear in neither list.
    """
    to_insert: List[Tuple[date, float]] = []
    to_update: List[Tuple[date, Optional[float], float]] = []

    for day, new_level in sorted(available.items()):
        if day not in existing:
            to_insert.append((day, new_level))
            continue
        old_level = existing[day]
        if old_level is None:
            # Placeholder row: repair it in place rather than inserting beside it.
            to_update.append((day, None, new_level))
        elif abs(old_level - new_level) > LEVEL_TOLERANCE_M:
            to_update.append((day, old_level, new_level))

    return to_insert, to_update


def describe_changes(
    changes: List[Tuple[date, Optional[float], float]], max_listed: int
) -> List[str]:
    """One "date: old -> new" line per change, truncated to max_listed."""
    lines = []
    for day, old, new in changes[:max_listed]:
        shown_old = "NULL" if old is None else f"{old:g}"
        lines.append(f"{day.isoformat()}: {shown_old} -> {new:g}")
    if len(changes) > max_listed:
        lines.append(f"... and {len(changes) - max_listed} more")
    return lines


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
    Work out what one station needs and what the chosen source can supply.
    Prints its own progress. Returns a summary dict:

        gaps              number of days with no usable reading in the window
        inserts           [(date, level)] to INSERT
        updates           [(date, old, new)] to UPDATE; always empty unless
                          --overwrite was passed
        missing_in_source gap days the source could not supply
        skipped           reason string, or None

    Under --overwrite the source is queried even when there are no gaps, because
    a window can be fully populated and still hold readings that disagree with
    the source.
    """
    blank = {"gaps": 0, "inserts": [], "updates": [], "missing_in_source": 0, "skipped": None}
    print(f"\n📍 {station}  (SWALIM id {swalim_id})")

    start, end, problem = resolve_window(conn, station, args.date_from, args.date_to)
    if problem:
        print(f"   ⏭️  skipped: {problem}")
        return {**blank, "skipped": problem}

    existing = get_existing_levels(conn, station, start, end)
    usable = usable_dates(existing)
    gaps = identify_gaps(usable, start, end)
    placeholders = len(existing) - len(usable)

    print(f"   window {start} .. {end}  ({(end - start).days + 1} days)")
    print(f"   usable readings stored: {len(usable)}")
    if placeholders:
        print(f"   rows with a NULL level: {placeholders}")

    if gaps:
        print(f"   ⚠️  missing: {len(gaps)} day(s)")
        print(f"      {describe_gaps(gaps, args.max_listed)}")
    elif not args.overwrite:
        print("   ✅ no gaps")
        return blank
    else:
        print("   no gaps; checking stored readings against the source")

    try:
        if args.source == SOURCE_PUBLIC:
            available = fetch_from_public_schema(conn, swalim_id, start, end)
        else:
            available = fetch_from_chart_api(config, station, start, end)
    except Exception as exc:  # noqa: BLE001 - report and carry on with other stations
        print(f"   ❌ source error: {type(exc).__name__}: {exc}")
        return {**blank, "gaps": len(gaps), "missing_in_source": len(gaps),
                "skipped": f"source error: {exc}"}

    if args.overwrite:
        inserts, updates = classify_changes(existing, available)
    else:
        # Insert-only: every gap the source can cover, stored readings untouched.
        inserts = [(d, available[d]) for d in gaps if d in available]
        updates = []

    covered_gaps = len([d for d in gaps if d in available])
    missing_in_source = len(gaps) - covered_gaps
    print(f"   source offers {len(available)} reading(s) in window; "
          f"{covered_gaps} match a gap, {missing_in_source} unavailable")

    if args.overwrite:
        print(f"   → {len(inserts)} to insert, {len(updates)} to overwrite")
        for line in describe_changes(updates, args.max_listed):
            print(f"      {line}")

    return {"gaps": len(gaps), "inserts": inserts, "updates": updates,
            "missing_in_source": missing_in_source, "skipped": None}


class Plan(NamedTuple):
    """Everything the analysis pass decided, before anything is written."""

    inserts: Dict[str, List[Tuple[date, float]]]
    updates: Dict[str, List[Tuple[date, Optional[float], float]]]
    total_gaps: int
    unavailable: Dict[str, int]

    @property
    def insert_count(self) -> int:
        return sum(len(v) for v in self.inserts.values())

    @property
    def update_count(self) -> int:
        return sum(len(v) for v in self.updates.values())

    def is_empty(self) -> bool:
        return not self.inserts and not self.updates


def print_header(args) -> None:
    print("=" * 78)
    print("FILL GAPS IN HISTORICAL RIVER LEVEL DATA")
    print("=" * 78)
    print(f"Source : {args.source}")
    print(f"Window : {args.date_from or '(earliest stored)'} .. {args.date_to or 'today'}")
    print(f"Mode   : {'APPLY - rows will be written' if args.apply else 'DRY RUN - nothing will be written'}")
    print(f"Writes : {'INSERT gaps + OVERWRITE disagreeing readings' if args.overwrite else 'INSERT gaps only'}")
    if args.overwrite:
        print("         ⚠️  --overwrite replaces stored readings; the previous values are not kept.")
    print()


def build_plan(conn, config: Config, targets: List[str], mapping: Dict[str, int], args) -> Plan:
    """Analyse every target station and collect what would be written."""
    inserts: Dict[str, List[Tuple[date, float]]] = {}
    updates: Dict[str, List[Tuple[date, Optional[float], float]]] = {}
    total_gaps = 0
    unavailable: Dict[str, int] = {}

    for station in targets:
        outcome = analyse_station(conn, config, station, mapping[station], args)
        total_gaps += outcome["gaps"]
        if outcome["missing_in_source"]:
            unavailable[station] = outcome["missing_in_source"]
        if outcome["inserts"]:
            inserts[station] = outcome["inserts"]
        if outcome["updates"]:
            updates[station] = outcome["updates"]

    return Plan(inserts, updates, total_gaps, unavailable)


def print_plan_summary(plan: Plan, args) -> None:
    print()
    print("=" * 78)
    print(f"Gaps found          : {plan.total_gaps}")
    print(f"To insert           : {plan.insert_count}")
    if args.overwrite:
        print(f"To overwrite        : {plan.update_count}")
    if plan.unavailable:
        detail = ', '.join(f'{k}: {v}' for k, v in sorted(plan.unavailable.items()))
        print(f"Not in source       : {sum(plan.unavailable.values())} ({detail})")
    print("=" * 78)


def explain_empty_plan(plan: Plan, args) -> None:
    """Say why there is nothing to do, which is not always obvious."""
    print("\nNothing to write.")
    if plan.total_gaps and args.source == SOURCE_CHART_API:
        print("Gaps exist but the API had no reading for those dates.")
        print(f"Try --source {SOURCE_PUBLIC} to see whether the fallback table has them.")
    elif not args.overwrite:
        print("Stored readings were not compared against the source. "
              "Pass --overwrite to check for disagreements.")


def confirm_write(plan: Plan) -> bool:
    print(f"\n⚠️  About to insert {plan.insert_count} row(s) into "
          f"flood_forecaster.historical_river_level.")
    if plan.update_count:
        print(f"⚠️  And OVERWRITE {plan.update_count} existing reading(s). "
              f"The previous values will not be recoverable from this table.")
    return input("Proceed? (yes/no): ").strip().lower() == "yes"


def write_plan(db: DatabaseConnection, plan: Plan) -> Tuple[int, int]:
    """
    Apply the plan in a single transaction: either the whole repair lands or none
    of it does. Returns (rows_inserted, rows_overwritten) as reported by the
    database, not as requested.
    """
    print("\nWriting...")
    inserted_total = 0
    updated_total = 0

    with db.engine.begin() as conn:
        for station in sorted(set(plan.inserts) | set(plan.updates)):
            rows = plan.inserts.get(station, [])
            changes = plan.updates.get(station, [])

            inserted = insert_rows(conn, station, rows)
            inserted_total += inserted
            skipped = len(rows) - inserted
            parts = [f"inserted {inserted}" + (f" ({skipped} already present)" if skipped else "")]

            updated = update_rows(conn, station, changes)
            updated_total += updated
            if changes:
                # A shortfall means the stored value already equalled the source
                # between the analysis read and this write: nothing to do.
                unchanged = len(changes) - updated
                parts.append(f"overwrote {updated}"
                             + (f" ({unchanged} already current)" if unchanged else ""))

            print(f"   {station}: {', '.join(parts)}")

    return inserted_total, updated_total


def print_next_steps(inserted: int, updated: int) -> None:
    print()
    print("=" * 78)
    print(f"✅ Inserted {inserted} row(s), overwrote {updated} row(s).")
    print("=" * 78)
    print("\nNext steps:")
    print("  1. Re-run this script without --apply to confirm the gaps are closed.")
    print("  2. python scripts/backfill/catchup_missing_predictions.py   # recompute predictions")
    if updated:
        print("     Overwritten readings change model inputs, so predictions built from")
        print("     them are now stale: recomputing is required, not optional.")


def main(argv: Optional[List[str]] = None) -> int:
    args = parse_args(argv)

    config_path = args.config or (Path(__file__).parents[2] / "config" / "config.ini")
    if not config_path.exists():
        print(f"❌ Configuration file not found at {config_path}")
        return 1

    config = Config(str(config_path))
    db = DatabaseConnection(config)
    print_header(args)

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

        plan = build_plan(conn, config, targets, mapping, args)
        print_plan_summary(plan, args)

        if plan.is_empty():
            explain_empty_plan(plan, args)
            return 0

        if not args.apply:
            print("\nDry run. Re-run with --apply to write the changes above.")
            return 0

        if not args.yes and not confirm_write(plan):
            print("Cancelled.")
            return 0

    inserted_total, updated_total = write_plan(db, plan)
    print_next_steps(inserted_total, updated_total)
    return 0


if __name__ == "__main__":
    sys.exit(main())
