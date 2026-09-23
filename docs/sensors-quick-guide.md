# Field sensors: quick guide

## What are they?

Shaqodoon has IoT field devices that write timestamped readings to `public.sensor_readings`. The flood forecaster can
read **rainfall** values from this table and compare or combine them with Open-Meteo weather data. It does not write
back to the sensor table.

This is separate from the SWALIM river gauges used for river-level inputs.

## Where are they?

| Site    | Device label | Recorded equipment              | Nearest forecast location           |
|---------|--------------|---------------------------------|-------------------------------------|
| Baidoa  | `BAIDOA_MOH` | Weather and water-level sensors | `bay__baydhaba` (17.4 km)           |
| Afgooye | `MOHADM_AFG` | Weather station                 | `lower_shabelle__afgooye` (16.3 km) |
| Elbarde | `MOH_EBW1`   | Water-level sensor              | `bakool__ceel_barde` (36.6 km)      |

Locations come from `data/static/sensor-stations.csv`. The nearest forecast location is calculated from GPS coordinates
with a default 50 km limit.

## Is sensor data active in forecasts?

**No, not in the current scheduled production setup.**

- Sensor rainfall is disabled by default in `config/config.ini`.
- None of the three mapped locations is used by the five scheduled production stations.
- Water-level readings from these IoT devices are not integrated; production river levels come from SWALIM.

## How would rainfall integration work?

When enabled for a forecast that uses a mapped location:

1. Read rows whose meaning contains `Rainfall`.
2. Clean invalid values and total valid readings by UTC day.
3. Match the sensor to the nearest forecast location.
4. Prefer the prepared sensor rainfall over Open-Meteo for matching location/date rows.

Current missing-day handling can repeat a previous sensor total or use zero, so it must be reviewed before production
enablement.

Fixes are tracked as SENS-001–006 in the [improvement backlog](improvement-backlog.md).

## How can I inspect it?

```bash
flood-cli database-model validate-sensor-readings

flood-cli database-model compare-sensor-weather \
  --location Baidoa \
  --date-from 2026-09-01 \
  --date-to 2026-09-21
```

These commands read sensor data; they do not modify it.

For schema details, cleaning rules, configuration, SQL checks, limitations, and onboarding steps, see
the [technical sensor guide](sensor-readings-integration.md).
