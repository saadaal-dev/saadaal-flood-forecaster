-- =========================================
-- Views for Common Queries
-- =========================================

-- Set the search path to use the flood_forecaster schema
SET search_path TO flood_forecaster, public;

-- View: Latest predictions with station metadata
CREATE OR REPLACE VIEW latest_predictions AS
SELECT p.id,
       p.location_name,
       p.date,
       p.level_m,
       p.station_number,
       p.ml_model_name,
       p.forecast_days,
       p.risk_level,
       s.station_name,
       s.river_name,
       s.region,
       s.moderate_flood_risk_m,
       s.high_flood_risk_m,
       s.latitude,
       s.longitude
FROM predicted_river_level p
         LEFT JOIN river_station_metadata s ON p.station_number = s.station_number
WHERE p.date > CURRENT_DATE;

-- View: Risk assessment summary
CREATE OR REPLACE VIEW risk_summary AS
SELECT location_name,
       station_number,
       COUNT(*)                                            as total_predictions,
       COUNT(CASE WHEN risk_level = 'HIGH' THEN 1 END)     as high_risk_count,
       COUNT(CASE WHEN risk_level = 'MODERATE' THEN 1 END) as moderate_risk_count,
       COUNT(CASE WHEN risk_level = 'LOW' THEN 1 END)      as low_risk_count,
       MAX(date)                                           as latest_prediction_date,
       AVG(level_m)                                        as avg_predicted_level
FROM predicted_river_level
WHERE date > CURRENT_DATE
GROUP BY location_name, station_number;
