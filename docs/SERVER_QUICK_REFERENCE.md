# Quick Reference - Server Commands

## Access Server

```bash
ssh user@68.183.13.232
docker exec -it <container-id> bash
cd /root/Amadeus/saadaal-flood-forecaster
source .venv/bin/activate
```

## Diagnostic Commands

### Clear stale API cache ⚠️ IMPORTANT

```bash
python scripts/clear_cache.py
# or manually:
rm -f .cache .cache.sqlite .cache.sqlite-shm .cache.sqlite-wal
```

### Check forecast data status

```bash
python scripts/diagnose_forecast_data.py
```

### Monitor live logs

```bash
tail -f logs/logs_amadeus_saadaal_flood_forecaster.log
```

### Force refresh forecast data

```bash
python scripts/force_refresh_forecast.py
```

## Manual Database Queries

### Connect to database

```bash
psql -h 68.183.13.232 -U <username> -d postgres
```

### Check forecast data

```sql
-- Summary by location
SELECT location_name,
       MIN(date) as min_date,
       MAX(date) as max_date,
       COUNT(*)  as row_count
FROM flood_forecaster.forecast_weather
GROUP BY location_name
ORDER BY MAX(date) DESC;

-- Check critical locations
SELECT location_name, MAX(date) as last_date
FROM flood_forecaster.forecast_weather
WHERE location_name IN (
                        'hiran__belet_weyne',
                        'ethiopia__tullu_dimtu',
                        'ethiopia__shabelle_gode',
                        'ethiopia__fafen_haren',
                        'ethiopia__debre_selam_arsi',
                        'ethiopia__fafen_gebredarre'
    )
GROUP BY location_name;

-- Check future data
SELECT COUNT(*) as future_records
FROM flood_forecaster.forecast_weather
WHERE date > CURRENT_DATE;

-- Recent inserts
SELECT location_name, date, TO_CHAR(date, 'YYYY-MM-DD HH24:MI:SS') as formatted_date
FROM flood_forecaster.forecast_weather
WHERE date >= CURRENT_DATE - INTERVAL '7 days'
ORDER BY date DESC
    LIMIT 50;
```

## CLI Commands

### Manual data ingestion

```bash
# Fetch forecast weather
flood-cli data-ingestion fetch-openmeteo forecast

# Fetch historical weather
flood-cli data-ingestion fetch-openmeteo historical

# Fetch river data
flood-cli data-ingestion fetch-river-data
```

### Run inference

```bash
# For specific station
flood-cli ml infer -f 7 -m Prophet_001 -o database "Belet Weyne"

# Run all stations (via script)
bash scripts/batch_infer_and_risk_assess.sh
```

### Risk assessment

```bash
flood-cli risk-assessment
```

## Useful Log Patterns

### Search for errors

```bash
grep -i "error\|exception" logs/logs_amadeus_saadaal_flood_forecaster.log | tail -20
```

### Search for specific date

```bash
grep "2025-12-03" logs/logs_amadeus_saadaal_flood_forecaster.log
```

### Search for upsert operations

```bash
grep "Upserted.*ForecastWeather" logs/logs_amadeus_saadaal_flood_forecaster.log | tail -10
```

### Search for missing data errors

```bash
grep "Missing weather forecast data" logs/logs_amadeus_saadaal_flood_forecaster.log | tail -20
```

### View DEBUG messages (after deployment)

```bash
grep "DEBUG:" logs/logs_amadeus_saadaal_flood_forecaster.log | tail -50
```

## Container Management

### Find container

```bash
docker ps | grep saadaal
```

### View container logs

```bash
docker logs <container-id> --tail 100 --follow
```

### Restart container

```bash
docker restart <container-id>
```

### Check cron jobs

```bash
crontab -l
cat amadeus_saadaal_flood_forecaster_cron
```

## File Locations

- **Config:** `config/config.ini`
- **Logs:** `logs/logs_amadeus_saadaal_flood_forecaster.log`
- **Models:** `models/`
- **Scripts:** `scripts/`
- **Cron:** `amadeus_saadaal_flood_forecaster_cron`

## Environment

### Check Python version

```bash
python --version
```

### Check installed packages

```bash
pip list | grep -i "flood\|prophet\|openmeteo"
```

### Check environment variables

```bash
echo $REPOSITORY_ROOT_PATH
echo $VENV_PATH
```

## Emergency Recovery

### If container is stuck

```bash
docker restart <container-id>
```

### If database connection fails

```bash
# Check database is running
docker ps | grep postgres

# Test connection
psql -h 68.183.13.232 -U <username> -d postgres -c "SELECT 1;"
```

### If forecast data completely missing

```bash
python scripts/force_refresh_forecast.py
```

### If models are missing

```bash
ls -lh models/
# Should see: Preprocessor_001-f7-Prophet_001-*.json files
```

