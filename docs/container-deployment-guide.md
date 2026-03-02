# Container Deployment Guide

## Local Development (Docker Compose)

The quickest way to run the full stack locally:

```bash
# 1. Copy and fill in your environment variables
cp .env.example .env
# Edit .env — set DB_HOST=db for local mode

# 2. Start PostgreSQL + the forecaster
docker compose --profile local up -d

# 3. Check logs
docker compose logs -f flood-forecaster

# 4. Stop everything
docker compose down
```

### Production Mode

On the production VM, run **without** the `local` profile. This starts only the app container and connects to the existing native PostgreSQL:

```bash
# .env must have POSTGRES_PASSWORD set (no default in production)
# DB_HOST defaults to the Docker host (existing PostgreSQL)
docker compose up -d
```

The PostgreSQL database is automatically bootstrapped with the schema, indexes, and views from the `sql/` directory on first run (local profile only).

---

## Manual Deployment (CapRover UI)

If you need to deploy manually (e.g., a hotfix):

1. Navigate to the CapRover UI
2. Open the **Apps** tab
3. Select the target app
4. Navigate to the **Deployment** tab
5. Scroll down to **Method 3: Deploy from Github/Bitbucket/Gitlab**
6.  Fill in the required fields:
   - **Repository**: `github.com/saadaal-dev/saadaal-flood-forecaster`
   - **Branch**: `main`
   - **Username and Password**: any (repository is public)
7. Click **Save & Restart**
8. Click **Force build** to trigger deployment
9. Check the **Logs** tab for cron initialization message and log output

---

## Notes

- The cron job is scheduled to run daily at noon UTC. This schedule can be changed in the `amadeus_saadaal_flood_forecaster_cron` file.
- The Docker image uses a multi-stage build (`python:3.12-slim`) to keep the runtime image small.
- A `HEALTHCHECK` is included — CapRover will automatically detect if the cron daemon stops.
