###############################################################################
# Stage 1: Builder — install dependencies in an isolated stage
###############################################################################
FROM python:3.12-slim AS builder

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# Install build-time system dependencies only
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    build-essential \
    ca-certificates \
    curl \
    git \
    && rm -rf /var/lib/apt/lists/*

# Install uv from official image (avoids network download issues)
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /usr/local/bin/

# Set work directory
ARG BASE_PATH="/root/Amadeus"
WORKDIR $BASE_PATH
COPY . saadaal-flood-forecaster

WORKDIR $BASE_PATH/saadaal-flood-forecaster

# Create virtual environment and install dependencies
ENV VENV_PATH="$BASE_PATH/saadaal-flood-forecaster/.venv"
RUN uv venv --python 3.12 $VENV_PATH
ENV PATH="$VENV_PATH/bin:$PATH" \
    VIRTUAL_ENV="$VENV_PATH"

RUN uv sync \
        --locked \
        --no-dev \
        --no-editable

###############################################################################
# Stage 2: Runtime — slim image with only what's needed to run
###############################################################################
FROM python:3.12-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# Install only runtime system dependencies (cron needed for scheduling)
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    ca-certificates \
    cron \
    libpq5 \
    && rm -rf /var/lib/apt/lists/*

# Set work directory
ARG BASE_PATH="/root/Amadeus"
WORKDIR $BASE_PATH

# Copy the application and venv from builder
COPY --from=builder $BASE_PATH/saadaal-flood-forecaster $BASE_PATH/saadaal-flood-forecaster

# Set repository root and logs path
ENV REPOSITORY_ROOT_PATH="$BASE_PATH/saadaal-flood-forecaster"
ENV LOGS_PATH="$REPOSITORY_ROOT_PATH/logs"
ENV LOG_FILE_PATH="$LOGS_PATH/logs_amadeus_saadaal_flood_forecaster.log"
RUN mkdir -p $LOGS_PATH

WORKDIR $REPOSITORY_ROOT_PATH

# Activate virtual environment
ENV VENV_PATH="$REPOSITORY_ROOT_PATH/.venv"
ENV PATH="$VENV_PATH/bin:$PATH" \
    VIRTUAL_ENV="$VENV_PATH"

# Ensure scripts are executable
RUN chmod +x "$REPOSITORY_ROOT_PATH"/scripts/amadeus_saadaal_flood_forecaster.sh && \
    chmod +x "$REPOSITORY_ROOT_PATH"/scripts/amadeus_saadaal_flood_forecaster_resilient.sh

# Copy cron job definition, replace placeholders and set proper permissions
ARG CRON_FILE_PATH="/etc/cron.d/amadeus_saadaal_flood_forecaster_cron"
COPY ./amadeus_saadaal_flood_forecaster_cron $CRON_FILE_PATH
RUN sed -i "s|{{REPOSITORY_ROOT_PATH}}|$REPOSITORY_ROOT_PATH|g" $CRON_FILE_PATH && \
    sed -i "s|{{VENV_PATH}}|$VENV_PATH|g" $CRON_FILE_PATH && \
    sed -i "s|{{LOG_FILE_PATH}}|$LOG_FILE_PATH|g" $CRON_FILE_PATH && \
    chmod 0644 $CRON_FILE_PATH

# Add entrypoint
COPY docker-entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

# Healthcheck: verify cron daemon is running
HEALTHCHECK --interval=5m --timeout=3s --start-period=10s --retries=2 \
    CMD pgrep cron > /dev/null || exit 1

ENTRYPOINT ["/entrypoint.sh"]
