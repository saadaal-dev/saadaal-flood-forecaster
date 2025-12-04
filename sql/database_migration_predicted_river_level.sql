-- =========================================
-- Migration Script: Fix predicted_river_level table
-- =========================================
-- This script fixes two issues:
-- 1. Changes date column from TIMESTAMP to DATE (removes time component)
-- 2. Adds created_at and updated_at columns
-- 3. Adds unique constraint to prevent duplicates
--
-- WARNING: This will remove duplicate rows if they exist.
-- Run this on the production database.
-- =========================================

-- Set the search path to use the flood_forecaster schema
SET search_path TO flood_forecaster, public;

-- Step 1: Backup the existing data (optional but recommended)
-- CREATE TABLE flood_forecaster.predicted_river_level_backup AS SELECT * FROM flood_forecaster.predicted_river_level;

-- Step 2: Add new columns (created_at, updated_at) if they don't exist
DO
$$
    BEGIN
        IF NOT EXISTS (SELECT 1
                       FROM information_schema.columns
                       WHERE table_schema = 'flood_forecaster'
                         AND table_name = 'predicted_river_level'
                         AND column_name = 'created_at') THEN
            ALTER TABLE flood_forecaster.predicted_river_level
                ADD COLUMN created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP;
        END IF;

        IF NOT EXISTS (SELECT 1
                       FROM information_schema.columns
                       WHERE table_schema = 'flood_forecaster'
                         AND table_name = 'predicted_river_level'
                         AND column_name = 'updated_at') THEN
            ALTER TABLE flood_forecaster.predicted_river_level
                ADD COLUMN updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP;
        END IF;
    END
$$;

-- Step 3: Change date column from TIMESTAMP to DATE
-- This will truncate the time component from existing data
ALTER TABLE flood_forecaster.predicted_river_level
    ALTER COLUMN date TYPE DATE;

-- Step 4: Remove duplicate rows (keep the most recent one based on id)
-- This is necessary before adding the unique constraint
DELETE
FROM flood_forecaster.predicted_river_level a USING (SELECT MAX(id) as id, location_name, date, ml_model_name
                                                     FROM flood_forecaster.predicted_river_level
                                                     GROUP BY location_name, date, ml_model_name
                                                     HAVING COUNT(*) > 1) b
WHERE a.location_name = b.location_name
  AND a.date = b.date
  AND a.ml_model_name = b.ml_model_name
  AND a.id < b.id;

-- Step 5: Add unique constraint to prevent future duplicates
DO
$$
    BEGIN
        IF NOT EXISTS (SELECT 1
                       FROM pg_constraint
                       WHERE conname = 'uq_prediction_location_date_model') THEN
            ALTER TABLE flood_forecaster.predicted_river_level
                ADD CONSTRAINT uq_prediction_location_date_model
                    UNIQUE (location_name, date, ml_model_name);
        END IF;
    END
$$;

-- Step 6: Add NOT NULL constraints
ALTER TABLE flood_forecaster.predicted_river_level
    ALTER COLUMN location_name SET NOT NULL,
    ALTER COLUMN date SET NOT NULL,
    ALTER COLUMN ml_model_name SET NOT NULL;

-- Step 7: Add comments
COMMENT ON COLUMN flood_forecaster.predicted_river_level.created_at IS 'Timestamp when the prediction was first created';
COMMENT ON COLUMN flood_forecaster.predicted_river_level.updated_at IS 'Timestamp when the prediction was last updated';

-- Step 8: Create trigger to automatically update updated_at on row updates
CREATE OR REPLACE FUNCTION update_predicted_river_level_updated_at()
    RETURNS TRIGGER AS
$$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trigger_update_predicted_river_level_updated_at ON flood_forecaster.predicted_river_level;

CREATE TRIGGER trigger_update_predicted_river_level_updated_at
    BEFORE UPDATE
    ON flood_forecaster.predicted_river_level
    FOR EACH ROW
EXECUTE FUNCTION update_predicted_river_level_updated_at();

-- Step 9: Verify the changes
SELECT column_name,
       data_type,
       is_nullable,
       column_default
FROM information_schema.columns
WHERE table_schema = 'flood_forecaster'
  AND table_name = 'predicted_river_level'
ORDER BY ordinal_position;

-- Show count of records and date range
SELECT COUNT(*)                      as total_records,
       COUNT(DISTINCT location_name) as unique_locations,
       MIN(date)                     as earliest_date,
       MAX(date)                     as latest_date
FROM flood_forecaster.predicted_river_level;

-- Show any remaining duplicates (should be 0)
SELECT location_name, date, ml_model_name, COUNT(*)
FROM flood_forecaster.predicted_river_level
GROUP BY location_name, date, ml_model_name
HAVING COUNT(*) > 1;

COMMIT;

