FROM python:3.12

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# Install system dependencies
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    build-essential \
    ca-certificates \
    cron \
    curl \
    git \
    && rm -rf /var/lib/apt/lists/*

# Install uv
ADD https://astral.sh/uv/install.sh /uv-installer.sh
RUN sh /uv-installer.sh && rm /uv-installer.sh
ENV PATH="/root/.local/bin/:$PATH"

# Set work directory
ARG BASE_PATH="/root/Amadeus"
WORKDIR $BASE_PATH
COPY . saadaal-flood-forecaster

# Set repository root and logs path
ENV REPOSITORY_ROOT_PATH="$BASE_PATH/saadaal-flood-forecaster"
ENV LOGS_PATH="$REPOSITORY_ROOT_PATH/logs"
ENV LOG_FILE_PATH="$LOGS_PATH/logs_amadeus_saadaal_flood_forecaster.log"
RUN mkdir -p $LOGS_PATH

WORKDIR $REPOSITORY_ROOT_PATH

# Create virtual environment
ENV VENV_PATH="$REPOSITORY_ROOT_PATH/.venv"
RUN uv venv --python 3.12 $VENV_PATH
ENV PATH="$VENV_PATH/bin:$PATH" \
    VIRTUAL_ENV="$VENV_PATH"

# Install Python dependencies from the lock file
RUN uv sync \
        --locked \
        --no-dev \
        --no-editable

# Ensure the script is executable
RUN chmod +x "$REPOSITORY_ROOT_PATH"/scripts/amadeus_saadaal_flood_forecaster.sh

# Copy cron job definition, replace placeholders  and set proper permissions
ARG CRON_FILE_PATH="/etc/cron.d/amadeus_saadaal_flood_forecaster_cron"
COPY ./amadeus_saadaal_flood_forecaster_cron $CRON_FILE_PATH
RUN sed -i "s|{{REPOSITORY_ROOT_PATH}}|$REPOSITORY_ROOT_PATH|g" $CRON_FILE_PATH && \
    sed -i "s|{{VENV_PATH}}|$VENV_PATH|g" $CRON_FILE_PATH && \
    sed -i "s|{{LOG_FILE_PATH}}|$LOG_FILE_PATH|g" $CRON_FILE_PATH && \
    chmod 0644 $CRON_FILE_PATH

# Add entrypoint
COPY docker-entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh
ENTRYPOINT ["/entrypoint.sh"]
