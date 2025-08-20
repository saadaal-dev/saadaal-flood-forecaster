classDiagram
direction BT
class forecast_weather {
varchar(100) location_name
timestamp date
double precision temperature_2m_max
double precision temperature_2m_min
double precision precipitation_sum
double precision rain_sum
double precision precipitation_hours
double precision precipitation_probability_max
double precision wind_speed_10m_max
integer id
}
class historical_river_level {
varchar(100) location_name
date date
double precision level_m
integer id
}
class historical_weather {
varchar(100) location_name
timestamp date
double precision temperature_2m_max
double precision temperature_2m_min
double precision precipitation_sum
double precision rain_sum
double precision precipitation_hours
integer id
}
class predicted_river_level {
varchar(100) location_name
timestamp date
double precision level_m
varchar(50) station_number
varchar(100) ml_model_name
integer forecast_days /* Number of days into the future the forecast is for */
varchar(50) risk_level
integer id
}
class river_station_metadata {
varchar(50) station_number
varchar(100) station_name
varchar(100) river_name
varchar(100) region
varchar(50) status
date first_date
double precision latitude
double precision longitude
double precision moderate_flood_risk_m
double precision high_flood_risk_m
double precision bankfull_m
double precision maximum_depth_m
double precision maximum_width_m
double precision maximum_flow_m
double precision elevation
integer swalim_internal_id
}

