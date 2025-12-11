-- =========================================
-- Flood Forecaster Database Bootstrap
-- =========================================
-- This script creates the complete database schema for the Saadaal Flood Forecaster project
-- Run this script on a fresh PostgreSQL database to set up all required tables
-- After running this, execute database_indexes.sql for performance optimization

-- Create the flood_forecaster schema
CREATE SCHEMA IF NOT EXISTS flood_forecaster;

-- Set the search path to use the new schema by default
SET search_path TO flood_forecaster, public;

-- =========================================
-- Table: historical_river_level
-- =========================================
-- Stores historical river level measurements
CREATE TABLE IF NOT EXISTS historical_river_level
(
    id            SERIAL PRIMARY KEY,
    location_name VARCHAR(100),
    date          DATE,
    level_m       DOUBLE PRECISION
);

-- =========================================
-- Table: predicted_river_level
-- =========================================
-- Stores ML model predictions for future river levels
CREATE TABLE IF NOT EXISTS predicted_river_level
(
    id             SERIAL PRIMARY KEY,
    location_name VARCHAR(100) NOT NULL,
    date          DATE         NOT NULL,
    level_m        DOUBLE PRECISION,
    station_number VARCHAR(50),
    ml_model_name VARCHAR(100) NOT NULL,
    forecast_days  INTEGER,
    risk_level    VARCHAR(50),
    created_at    TIMESTAMP    NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at    TIMESTAMP    NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uq_prediction_location_date_model UNIQUE (location_name, date, ml_model_name)
);

-- Add comment to explain forecast_days column
COMMENT ON COLUMN predicted_river_level.forecast_days IS 'Number of days into the future the forecast is for';
COMMENT ON COLUMN predicted_river_level.risk_level IS 'Risk level of the forecasted river level, e.g., ''Low'', ''Medium'', ''High''';
COMMENT ON COLUMN predicted_river_level.created_at IS 'Timestamp when the prediction was first created';
COMMENT ON COLUMN predicted_river_level.updated_at IS 'Timestamp when the prediction was last updated';

-- =========================================
-- Table: historical_weather
-- =========================================
-- Stores historical weather data for model training
CREATE TABLE IF NOT EXISTS historical_weather
(
    id                  SERIAL PRIMARY KEY,
    location_name       VARCHAR(100),
    date                TIMESTAMP,
    temperature_2m_max  DOUBLE PRECISION,
    temperature_2m_min  DOUBLE PRECISION,
    precipitation_sum   DOUBLE PRECISION,
    rain_sum            DOUBLE PRECISION,
    precipitation_hours DOUBLE PRECISION
);

ALTER TABLE flood_forecaster.historical_weather
    ADD CONSTRAINT uq_historical_weather_location_date UNIQUE (location_name, date);

-- =========================================
-- Table: forecast_weather
-- =========================================
-- Stores weather forecast data for river level predictions
CREATE TABLE IF NOT EXISTS forecast_weather
(
    id                            SERIAL PRIMARY KEY,
    location_name                 VARCHAR(100),
    date                          TIMESTAMP,
    temperature_2m_max            DOUBLE PRECISION,
    temperature_2m_min            DOUBLE PRECISION,
    precipitation_sum             DOUBLE PRECISION,
    rain_sum                      DOUBLE PRECISION,
    precipitation_hours           DOUBLE PRECISION,
    precipitation_probability_max DOUBLE PRECISION,
    wind_speed_10m_max            DOUBLE PRECISION
);

ALTER TABLE flood_forecaster.forecast_weather
    ADD CONSTRAINT uq_forecast_location_date UNIQUE (location_name, date);

-- =========================================
-- Table: river_station_metadata
-- =========================================
-- Stores metadata about river monitoring stations
CREATE TABLE IF NOT EXISTS river_station_metadata
(
    station_number        VARCHAR(50),
    station_name          VARCHAR(100)
        CONSTRAINT station_name_unique UNIQUE,
    river_name            VARCHAR(100),
    region                VARCHAR(100),
    status                VARCHAR(50),
    first_date            DATE,
    latitude              DOUBLE PRECISION,
    longitude             DOUBLE PRECISION,
    moderate_flood_risk_m DOUBLE PRECISION,
    high_flood_risk_m     DOUBLE PRECISION,
    bankfull_m            DOUBLE PRECISION,
    maximum_depth_m       DOUBLE PRECISION,
    maximum_width_m       DOUBLE PRECISION,
    maximum_flow_m        DOUBLE PRECISION,
    elevation             DOUBLE PRECISION,
    swalim_internal_id    INTEGER
);

-- =========================================
-- Grant Permissions
-- =========================================
-- Grant permissions to postgres user (adjust as needed for your setup)
GRANT ALL PRIVILEGES ON SCHEMA flood_forecaster TO postgres;
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA flood_forecaster TO postgres;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA flood_forecaster TO postgres;

-- =========================================
-- Database Setup Complete
-- =========================================
COMMENT ON SCHEMA flood_forecaster IS 'Main schema for the Saadaal Flood Forecaster project';
