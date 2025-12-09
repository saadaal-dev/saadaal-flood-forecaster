# Sentry Integration Guide

This document explains how Sentry has been integrated into the Saadaal Flood Forecaster application for centralized
logging and error tracking.

## Overview

Sentry has been integrated to:

- Centralize all application logs in one place (Sentry dashboard)
- Track errors and exceptions with full stack traces
- Monitor application performance
- Get real-time alerts when issues occur
- Track breadcrumbs (trail of events leading to errors)

## Setup Instructions

### Step 1: Get Your Sentry DSN

1. Log in to your Sentry account at https://sentry.io
2. Create a new project (or use an existing one)
    - Project type: Python
    - Alert frequency: Set according to your needs
3. Copy your DSN (Data Source Name) - it looks like:
   ```
   https://abc123@o123456.ingest.sentry.io/7890123
   ```

### Step 2: Configure Environment Variables

Add the following environment variables to your deployment:

```bash
# Required: Your Sentry DSN
export SENTRY_DSN="https://your-dsn-here@sentry.io/project-id"

# Optional: Environment name (defaults to 'production')
export SENTRY_ENVIRONMENT="production"

# Optional: Release version for tracking
export SENTRY_RELEASE="0.1.2"

# Optional: Log level (defaults to 'INFO')
export LOG_LEVEL="INFO"
```

### Step 3: Update CapRover Configuration

In your CapRover dashboard:

1. Go to your app settings
2. Navigate to "App Configs" → "Environment Variables"
3. Add the environment variables:
    - `SENTRY_DSN`: Your Sentry DSN
    - `SENTRY_ENVIRONMENT`: `production` (or `staging`, `development`)
    - `LOG_LEVEL`: `INFO` (or `DEBUG` for more verbose logging)

### Step 4: Rebuild and Deploy

```bash
# Install dependencies with the new sentry-sdk package
uv sync --locked

# Rebuild your Docker image (CapRover will do this automatically on push)
```

## How It Works

### Automatic Logging

All log messages at ERROR level and above are automatically sent to Sentry:

```python
import logging

logger = logging.getLogger(__name__)

# This will appear in Sentry
logger.error("Something went wrong!")
logger.critical("Critical failure!")

# These appear as breadcrumbs in Sentry
logger.info("Processing started")
logger.warning("Something looks suspicious")
```

### Manual Exception Tracking

You can manually capture exceptions with additional context:

```python
from flood_forecaster.utils.logging_config import capture_exception

try:
    # Your code here
    process_data()
except Exception as e:
    capture_exception(e,
                      station="Belet Weyne",
                      date="2025-12-06",
                      custom_info="Additional context"
                      )
```

### Manual Message Tracking

Send custom messages to Sentry:

```python
from flood_forecaster.utils.logging_config import capture_message

capture_message(
    "Flood alert triggered for Belet Weyne",
    level="warning",
    risk_level="high",
    water_level=5.2
)
```

### Breadcrumbs

Add breadcrumbs to track the sequence of events:

```python
from flood_forecaster.utils.logging_config import add_breadcrumb

add_breadcrumb(
    message="Started data processing",
    category="data_ingestion",
    level="info",
    station="Belet Weyne",
    records_count=100
)
```

## Logging Levels

- **DEBUG**: Detailed information for debugging (not sent to Sentry by default)
- **INFO**: General informational messages (stored as breadcrumbs in Sentry)
- **WARNING**: Warning messages (stored as breadcrumbs in Sentry)
- **ERROR**: Error events (sent as events to Sentry)
- **CRITICAL**: Critical failures (sent as events to Sentry)

## What Gets Sent to Sentry

### Events (Errors)

- All `logger.error()` and `logger.critical()` calls
- Uncaught exceptions
- Manual `capture_exception()` calls
- Manual `capture_message()` calls at error/fatal level

### Breadcrumbs (Context)

- `logger.info()` calls
- `logger.warning()` calls
- Manual `add_breadcrumb()` calls
- Database queries
- HTTP requests

### Context Information

- Environment (production/staging/development)
- Release version
- Server details (OS, Python version)
- User information (if configured)
- Custom tags and extra data

## Performance Monitoring

The integration includes performance monitoring:

- 10% of transactions are sampled for performance data
- Track slow database queries
- Monitor API response times
- Identify bottlenecks

## Testing the Integration

### Test 1: Check if Sentry is Initialized

After deploying, check your logs for:

```
Sentry initialized successfully for environment: production
```

If you see a warning about missing DSN, Sentry is not configured.

### Test 2: Trigger a Test Error

Add this to a command and run it:

```python
from flood_forecaster.utils.logging_config import capture_message

capture_message("Test message from flood forecaster", level="info")
```

Check your Sentry dashboard to see if the message appears.

### Test 3: Check Real Errors

Run your normal workflow and check Sentry for any errors that occur naturally.

## Viewing Logs in Sentry

1. Go to https://sentry.io and log in
2. Select your project
3. Navigate to:
    - **Issues**: See all errors and exceptions
    - **Performance**: Monitor transaction performance
    - **Releases**: Track issues by release version
    - **Alerts**: Configure email/Slack notifications

## Best Practices

1. **Use Appropriate Log Levels**
    - Use `logger.debug()` for verbose debugging (development only)
    - Use `logger.info()` for general information
    - Use `logger.warning()` for potential issues
    - Use `logger.error()` for actual errors
    - Use `logger.critical()` for critical failures

2. **Add Context**
    - Include relevant data in log messages
    - Use extra parameters to add structured data
    - Add breadcrumbs before operations

3. **Don't Log Sensitive Data**
    - Avoid logging passwords, API keys, personal information
    - Configure `send_default_pii=False` (already set)

4. **Monitor Quota Usage**
    - Sentry has event limits based on your plan
    - Adjust sample rates if needed
    - Filter out noisy errors

## Troubleshooting

### No Logs Appearing in Sentry

1. Check if `SENTRY_DSN` is set correctly
2. Check your Sentry project settings
3. Verify network connectivity from the container
4. Check if the DSN is active and not disabled

### Too Many Events

1. Increase the `event_level` to `CRITICAL` in `logging_config.py`
2. Reduce `traces_sample_rate` for performance monitoring
3. Add filters to ignore specific errors

### Logs Only in File, Not Sentry

1. Ensure `setup_logging()` is called at startup
2. Check if the log level is high enough (ERROR or above)
3. Verify Sentry SDK is installed: `pip list | grep sentry`

## Migration Notes

- **Before**: Logs were written to files in the container, requiring SSH access to view
- **After**: Logs are automatically sent to Sentry, viewable from anywhere
- **File logs**: Still available in the container at `$LOG_FILE_PATH` for backup

## Additional Resources

- [Sentry Python SDK Documentation](https://docs.sentry.io/platforms/python/)
- [Sentry Logging Integration](https://docs.sentry.io/platforms/python/integrations/logging/)
- [Sentry Best Practices](https://docs.sentry.io/product/best-practices/)

## Support

If you encounter issues:

1. Check the Sentry dashboard for configuration errors
2. Review container logs for initialization messages
3. Verify environment variables are set correctly
4. Test with a simple `capture_message()` call

