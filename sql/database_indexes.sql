-- =========================================
-- Flood Forecaster Database Indexes
-- =========================================
-- This script creates performance indexes for the Saadaal Flood Forecaster project
-- Run this script AFTER running database_bootstrap.sql to optimize query performance

-- Set the search path to use the flood_forecaster schema
SET search_path TO flood_forecaster, public;

-- =========================================
-- Indexes for historical_river_level
-- =========================================
CREATE INDEX IF NOT EXISTS idx_historical_river_location ON historical_river_level (location_name);
CREATE INDEX IF NOT EXISTS idx_historical_river_date ON historical_river_level (date);

-- =========================================
-- Indexes for predicted_river_level
-- =========================================
CREATE INDEX IF NOT EXISTS idx_predicted_river_location ON predicted_river_level (location_name);
CREATE INDEX IF NOT EXISTS idx_predicted_river_date ON predicted_river_level (date);
CREATE INDEX IF NOT EXISTS idx_predicted_river_station ON predicted_river_level (station_number);
CREATE INDEX IF NOT EXISTS idx_predicted_river_model ON predicted_river_level (ml_model_name);
CREATE INDEX IF NOT EXISTS idx_predicted_river_risk ON predicted_river_level (risk_level);
CREATE INDEX IF NOT EXISTS idx_predicted_river_forecast_days ON predicted_river_level (forecast_days);

-- =========================================
-- Indexes for historical_weather
-- =========================================
CREATE INDEX IF NOT EXISTS idx_historical_weather_location ON historical_weather (location_name);
CREATE INDEX IF NOT EXISTS idx_historical_weather_date ON historical_weather (date);

-- =========================================
-- Indexes for forecast_weather
-- =========================================
CREATE INDEX IF NOT EXISTS idx_forecast_weather_location ON forecast_weather (location_name);
CREATE INDEX IF NOT EXISTS idx_forecast_weather_date ON forecast_weather (date);

-- =========================================
-- Indexes for river_station_metadata
-- =========================================
CREATE INDEX IF NOT EXISTS idx_station_metadata_name ON river_station_metadata (station_name);
CREATE INDEX IF NOT EXISTS idx_station_metadata_river ON river_station_metadata (river_name);
CREATE INDEX IF NOT EXISTS idx_station_metadata_region ON river_station_metadata (region);
CREATE INDEX IF NOT EXISTS idx_station_metadata_status ON river_station_metadata (status);

-- =========================================
-- Composite Indexes for Common Queries
-- =========================================
-- Index for date range queries on predictions
CREATE INDEX IF NOT EXISTS idx_predicted_river_date_station ON predicted_river_level (date, station_number);

-- Index for location-based historical data queries
CREATE INDEX IF NOT EXISTS idx_historical_river_location_date ON historical_river_level (location_name, date);

-- Index for weather-location-date queries
CREATE INDEX IF NOT EXISTS idx_historical_weather_location_date ON historical_weather (location_name, date);
CREATE INDEX IF NOT EXISTS idx_forecast_weather_location_date ON forecast_weather (location_name, date);

-- =========================================
-- Indexes Creation Complete
-- =========================================
SELECT 'Database indexes created successfully!' AS status;
