-- =========================================
-- Migration: Add Unique Constraint to historical_weather
-- =========================================
-- This migration adds a unique constraint on (location_name, date) to prevent duplicate weather records
-- This should be safe to run since the code now uses UPSERT logic (ON CONFLICT DO UPDATE)
--
-- Prerequisites:
-- 1. The application code must use UPSERT (already implemented in common.py)
-- 2. Any existing duplicates should be cleaned up first
--
-- Usage:
--   psql -h <host> -U postgres -d postgres -f sql/add_historical_weather_unique_constraint.sql

SET search_path TO flood_forecaster, public;

-- Step 1: Check for existing duplicates (informational query)
-- Run this separately first to see if you have duplicates
DO
$$
    DECLARE
        duplicate_count INTEGER;
    BEGIN
        SELECT COUNT(*)
        INTO duplicate_count
        FROM (SELECT location_name, date
              FROM flood_forecaster.historical_weather
              GROUP BY location_name, date
              HAVING COUNT(*) > 1) duplicates;

        IF duplicate_count > 0 THEN
            RAISE NOTICE 'WARNING: Found % duplicate (location_name, date) combinations in historical_weather', duplicate_count;
            RAISE NOTICE 'You should run the deduplication script first:';
            RAISE NOTICE 'python scripts/remove_duplicate_historical_weather.py';
            RAISE EXCEPTION 'Cannot add unique constraint with existing duplicates';
        ELSE
            RAISE NOTICE 'No duplicates found. Safe to add unique constraint.';
        END IF;
    END
$$;

-- Step 2: Add the unique constraint
-- This will only execute if the above check passes (no duplicates)
ALTER TABLE flood_forecaster.historical_weather
    ADD CONSTRAINT uq_historical_weather_location_date UNIQUE (location_name, date);

-- Step 3: Verify the constraint was added and print confirmation
DO
$$
    DECLARE
        constraint_exists BOOLEAN;
    BEGIN
        SELECT EXISTS (SELECT 1
                       FROM pg_constraint
                       WHERE conrelid = 'flood_forecaster.historical_weather'::regclass
                         AND conname = 'uq_historical_weather_location_date')
        INTO constraint_exists;

        IF constraint_exists THEN
            RAISE NOTICE 'Successfully added unique constraint uq_historical_weather_location_date';
        ELSE
            RAISE WARNING 'Constraint was not added - check for errors above';
        END IF;
    END
$$;

-- Display constraint details
SELECT conname, contype, pg_get_constraintdef(oid) as definition
FROM pg_constraint
WHERE conrelid = 'flood_forecaster.historical_weather'::regclass
  AND conname = 'uq_historical_weather_location_date';


