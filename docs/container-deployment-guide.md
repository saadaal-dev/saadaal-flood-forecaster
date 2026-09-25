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
8. Open the **App Configs** tab and set the **Environmental Variables** (see below), then **Save & Update**
9. Click **Force build** to trigger deployment
10. Check the **Logs** tab for cron initialization message and log output

## Environmental Variables

These live in the CapRover app config, not in the repository. They are per-app: a newly created app,
or a different app than the one previously serving production, starts with none of them set.

| Variable            | Required | Notes                                          |
|---------------------|----------|------------------------------------------------|
| `DB_HOST`           | Yes      | PostgreSQL hostname or IP. Every DB read/write fails without it. |
| `POSTGRES_PASSWORD` | Yes      | Password for the `[data.database] user` in `config/config.ini`. |
| `MAILJET_API_KEY`   | Yes      | Needed to send alert emails.                   |
| `MAILJET_API_SECRET`| Yes      | Needed to send alert emails.                   |
| `CONTACT_LIST_ID`   | Optional | Mailjet contact list for bulk alerts.          |
| `SENTRY_DSN`        | Optional | Enables Sentry error reporting.                |
| `SENTRY_ENVIRONMENT`| Optional | Defaults to `production`.                      |
| `SENTRY_RELEASE`    | Optional | Release tag reported to Sentry.                |
| `LOG_LEVEL`         | Optional | Defaults to `INFO`.                            |

Only variables on the allowlist in `docker-entrypoint.sh` are snapshotted to the `.env` file the cron
job reads, and only if they are actually set in the container. Confirm the snapshot in the **Logs**
tab right after a deploy:

```text
[entrypoint] Captured into .env: DB_HOST POSTGRES_PASSWORD MAILJET_API_KEY ...
```

If `DB_HOST` or `POSTGRES_PASSWORD` is missing, the entrypoint prints an explicit error block at
startup and the pipeline aborts with a configuration error instead of failing at noon with an opaque
`ValueError: DB_HOST environment variable not set.` traceback.

## Deploying from GitHub Actions

`.github/workflows/deploy-caprover.yml` (manual trigger) calls CapRover's "Trigger build via webhook"
URL, which is the same thing as pressing **Force build** above. It does not create apps and does not
set environment variables.

One-time setup:

1. In the CapRover app's **Deployment** tab, copy the **Trigger build via webhook** URL. The token in
   that URL is specific to one app — verify it belongs to the app you actually want to deploy.
2. Store it as the `CAPROVER_WEBHOOK_URL` secret in the repository's `production` environment
   (Settings → Environments → production → Environment secrets).
3. The app must already be configured with Method 3 above; the webhook only rebuilds what the app is
   configured to build.

**Note**: The cron job is scheduled to run daily at noon UTC. This schedule can be changed in the `amadeus_saadaal_flood_forecaster_cron` file when needed.
