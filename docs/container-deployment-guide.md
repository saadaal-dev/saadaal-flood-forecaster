# Container Deployment Guide

## Step-by-Step Deployment Instructions

1. Navigate to the CapRover UI
2. Open the **Apps** tab
3. Select the target app (currently `app-test`)
4. Navigate to the **Deployment** tab
5. Scroll down to **Method 3: Deploy from Github/Bitbucket/Gitlab**
6.  Fill in the required fields:
   - **Repository**: `github.com/saadaal-dev/saadaal-flood-forecaster`
   - **Branch**: `main`
   - **Username and Password**: any (repository is public)
7. Click **Save & Restart**
8. Click **Force build** to trigger deployment
9. Check the **Logs** tab for cron initialization message and log output

**Note**: The cron job is scheduled to run daily at noon UTC. This schedule can be changed in the `amadeus_saadaal_flood_forecaster_cron` file when needed.
