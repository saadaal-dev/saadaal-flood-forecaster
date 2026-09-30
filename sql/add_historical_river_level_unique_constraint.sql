-- =========================================
-- Migration: Add Unique Constraint to historical_river_level  (DATA-005)
-- =========================================
-- Adds a unique constraint on (location_name, date) so one station cannot hold more
-- than one reading per calendar day.
--
-- Why this matters beyond tidiness:
--   * Any coverage check written as COUNT(*) over-reports when duplicates exist and
--     can conclude a station is complete when it is not.
--   * Without a constraint there is no ON CONFLICT target, so every write path has to
--     pre-check row by row. That read-modify-write cannot be made race-safe and
--     cannot update a corrected upstream value.
--   * The 2026-09-22 production snapshot held 962 excess rows across 962 duplicate
--     (location_name, date) pairs, 9 of which disagreed on level_m.
--
-- ORDER MATTERS: apply this BEFORE deploying the code.
--
-- The new ingestion code uses ON CONFLICT (location_name, date), which PostgreSQL
-- can only satisfy when a matching unique index exists. Deploying it first makes
-- every river ingestion fail with "there is no unique or exclusion constraint
-- matching the ON CONFLICT specification". Applying this migration early is safe for
-- the currently deployed code: its insert path checks for an existing row first, and
-- the gap-fill script uses a bare ON CONFLICT DO NOTHING, which needs no index.
--
-- Prerequisites:
--   1. Take a snapshot: ./db-snapshot/01-dump.sh
--   2. Remove existing duplicates. Use the psql-only cleanup, since the Python
--      script ships with the code that is not deployed yet:
--        psql ... -v ON_ERROR_STOP=1 -v apply=0 -f sql/deduplicate_historical_river_level.sql
--        psql ... -v ON_ERROR_STOP=1 -v apply=1 -f sql/deduplicate_historical_river_level.sql
--      Once the code is deployed, the equivalent is
--        python scripts/maintenance/remove_duplicate_historical_river_level.py [--dry-run]
--
-- Usage:
--   psql -h <host> -U postgres -d postgres -f sql/add_historical_river_level_unique_constraint.sql
--
-- Rollback:
--   ALTER TABLE flood_forecaster.historical_river_level
--       DROP CONSTRAINT uq_historical_river_level_location_date;

SET search_path TO flood_forecaster, public;

-- Step 1: Refuse to proceed while duplicates remain.
-- Counted as excess rows so the number matches what the cleanup script reports.
DO
$$
    DECLARE
        duplicate_pairs INTEGER;
        excess_rows     INTEGER;
    BEGIN
        SELECT COUNT(*), COALESCE(SUM(n - 1), 0)
        INTO duplicate_pairs, excess_rows
        FROM (SELECT location_name, date, COUNT(*) AS n
              FROM flood_forecaster.historical_river_level
              GROUP BY location_name, date
              HAVING COUNT(*) > 1) duplicates;

        IF duplicate_pairs > 0 THEN
            RAISE NOTICE 'WARNING: Found % duplicate (location_name, date) pair(s) in historical_river_level, % excess row(s)', duplicate_pairs, excess_rows;
            RAISE NOTICE 'Remove them first:';
            RAISE NOTICE '  python scripts/maintenance/remove_duplicate_historical_river_level.py --dry-run';
            RAISE NOTICE '  python scripts/maintenance/remove_duplicate_historical_river_level.py';
            RAISE EXCEPTION 'Cannot add unique constraint with existing duplicates';
        ELSE
            RAISE NOTICE 'No duplicates found. Safe to add unique constraint.';
        END IF;
    END
$$;

-- Step 2: Add the unique constraint.
-- Idempotent: skipped when a previous run already added it.
DO
$$
    BEGIN
        IF EXISTS (SELECT 1
                   FROM pg_constraint
                   WHERE conrelid = 'flood_forecaster.historical_river_level'::regclass
                     AND conname = 'uq_historical_river_level_location_date') THEN
            RAISE NOTICE 'Constraint uq_historical_river_level_location_date already exists; nothing to do.';
        ELSE
            ALTER TABLE flood_forecaster.historical_river_level
                ADD CONSTRAINT uq_historical_river_level_location_date UNIQUE (location_name, date);
            RAISE NOTICE 'Added unique constraint uq_historical_river_level_location_date';
        END IF;
    END
$$;

-- Step 3: Verify.
DO
$$
    DECLARE
        constraint_exists BOOLEAN;
    BEGIN
        SELECT EXISTS (SELECT 1
                       FROM pg_constraint
                       WHERE conrelid = 'flood_forecaster.historical_river_level'::regclass
                         AND conname = 'uq_historical_river_level_location_date')
        INTO constraint_exists;

        IF constraint_exists THEN
            RAISE NOTICE 'Verified: uq_historical_river_level_location_date is in place';
        ELSE
            RAISE WARNING 'Constraint was not added - check for errors above';
        END IF;
    END
$$;

-- Display constraint details
SELECT conname, contype, pg_get_constraintdef(oid) AS definition
FROM pg_constraint
WHERE conrelid = 'flood_forecaster.historical_river_level'::regclass
  AND conname = 'uq_historical_river_level_location_date';
