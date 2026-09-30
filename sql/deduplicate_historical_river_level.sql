-- =========================================
-- Cleanup: collapse duplicate river levels  (DATA-005)
-- =========================================
-- psql-only equivalent of scripts/maintenance/remove_duplicate_historical_river_level.py.
--
-- WHY A SQL VERSION EXISTS
--
-- The new ingestion code uses ON CONFLICT (location_name, date), which PostgreSQL
-- can only satisfy when a matching unique index exists. Deploying that code before
-- the constraint is applied makes every river ingestion fail with:
--
--   there is no unique or exclusion constraint matching the ON CONFLICT specification
--
-- So the constraint has to be in place *before* the code ships. But the Python
-- cleanup script ships *with* that code, which would leave no way to clear the
-- duplicates first. This file breaks that cycle: it needs nothing but psql, so the
-- database can be prepared ahead of the deployment.
--
-- Applying the constraint early is safe for the currently deployed code: its
-- insert path checks for an existing row before inserting, and the gap-fill script
-- uses a bare ON CONFLICT DO NOTHING, which needs no index. Verified against a copy
-- of the 2026-09-22 snapshot.
--
-- RETENTION RULE
--
-- One row survives per (location_name, date):
--   1. a row whose level_m is NOT NULL beats one that is NULL;
--   2. then the highest id wins, i.e. the most recently ingested.
--
-- The highest-id rule was verified, not assumed. All nine value-conflicting pairs in
-- the 2026-09-22 production snapshot were arbitrated against public.station_river_data
-- and the more recently ingested value was correct in every case, three of them
-- correcting a whole-metre transcription error. Note the discarded outlier sat on
-- different sides of id order across those nine, so a plain MIN(id)/MAX(id) choice
-- without that arbitration would have been a guess.
--
-- USAGE
--   -- 1. take a snapshot first; this deletes rows and the previous values are not kept
--   ./db-snapshot/01-dump.sh
--
--   -- 2. preview (prints counts and every value-changing pair, writes nothing)
--   psql -h <host> -U postgres -d postgres \
--       -v ON_ERROR_STOP=1 -v apply=0 -f sql/deduplicate_historical_river_level.sql
--
--   -- 3. apply
--   psql -h <host> -U postgres -d postgres \
--       -v ON_ERROR_STOP=1 -v apply=1 -f sql/deduplicate_historical_river_level.sql
--
--   -- 4. then add the constraint
--   psql -h <host> -U postgres -d postgres \
--       -v ON_ERROR_STOP=1 -f sql/add_historical_river_level_unique_constraint.sql
--
-- Defaults to preview when -v apply is not supplied, so a missing flag cannot delete
-- anything. Idempotent: re-running after a successful apply reports nothing to do.

\if :{?apply}
\else
    \set apply 0
\endif

SET search_path TO flood_forecaster, public;

BEGIN;

-- Bridge the psql client variable into a server setting the DO block can read.
-- psql variables are interpolated into SQL text and are not visible to PL/pgSQL.
SET LOCAL data005.apply = :'apply';

DO
$$
    DECLARE
        excess_rows     INTEGER;
        affected_pairs  INTEGER;
        conflict_pairs  INTEGER;
        should_apply    BOOLEAN := current_setting('data005.apply', true) = '1';
        r               RECORD;
    BEGIN
        CREATE TEMP TABLE data005_doomed ON COMMIT DROP AS
        SELECT id, location_name, date, level_m
        FROM (SELECT id, location_name, date, level_m,
                     ROW_NUMBER() OVER (
                         PARTITION BY location_name, date
                         ORDER BY (level_m IS NOT NULL) DESC, id DESC
                     ) AS rn
              FROM flood_forecaster.historical_river_level) ranked
        WHERE rn > 1;

        SELECT COUNT(*), COUNT(DISTINCT (location_name, date))
        INTO excess_rows, affected_pairs
        FROM data005_doomed;

        IF excess_rows = 0 THEN
            RAISE NOTICE 'No duplicate (station, date) river levels found. Nothing to do.';
            RETURN;
        END IF;

        RAISE NOTICE 'Found % excess row(s) across % duplicate (station, date) pair(s).',
            excess_rows, affected_pairs;

        -- Only these pairs actually change a stored reading; the rest are exact copies.
        SELECT COUNT(*) INTO conflict_pairs
        FROM (SELECT location_name, date
              FROM flood_forecaster.historical_river_level
              GROUP BY location_name, date
              HAVING COUNT(*) > 1 AND COUNT(DISTINCT level_m) > 1) c;

        IF conflict_pairs = 0 THEN
            RAISE NOTICE 'All duplicate pairs agree on level_m; no reading changes value.';
        ELSE
            RAISE NOTICE '% pair(s) hold conflicting values; keeping the most recently ingested:',
                conflict_pairs;
            FOR r IN
                SELECT h.location_name, h.date,
                       MIN(h.level_m) AS lowest,
                       MAX(h.level_m) AS highest,
                       (SELECT k.level_m
                          FROM flood_forecaster.historical_river_level k
                         WHERE k.location_name = h.location_name AND k.date = h.date
                           AND k.id NOT IN (SELECT id FROM data005_doomed)
                         LIMIT 1) AS kept
                FROM flood_forecaster.historical_river_level h
                GROUP BY h.location_name, h.date
                HAVING COUNT(*) > 1 AND COUNT(DISTINCT h.level_m) > 1
                ORDER BY h.location_name, h.date
            LOOP
                RAISE NOTICE ' - % %: keeping % (range %..%)',
                    r.location_name, r.date, r.kept, r.lowest, r.highest;
            END LOOP;
        END IF;

        IF NOT should_apply THEN
            RAISE NOTICE 'PREVIEW: % row(s) would be deleted. Re-run with -v apply=1 to delete.',
                excess_rows;
            RETURN;
        END IF;

        DELETE FROM flood_forecaster.historical_river_level
        WHERE id IN (SELECT id FROM data005_doomed);

        RAISE NOTICE 'Deleted % duplicate row(s).', excess_rows;
    END
$$;

COMMIT;

-- Verification: both numbers must match, and excess must be 0.
SELECT COUNT(*)                                   AS total_rows,
       COUNT(DISTINCT (location_name, date))      AS distinct_station_days,
       COUNT(*) - COUNT(DISTINCT (location_name, date)) AS excess_rows
FROM flood_forecaster.historical_river_level;
