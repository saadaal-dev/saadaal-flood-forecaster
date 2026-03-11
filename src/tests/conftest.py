"""
Top-level pytest configuration.

Auto-skips tests marked @pytest.mark.integration_db when PostgreSQL is not
reachable on localhost:5432, so that developers without a running DB (or CI
runners that don't spin up the compose stack) get a clean SKIP rather than a
hard connection error.

To bring up the local test DB:
    docker compose up -d
    export POSTGRES_PASSWORD=testpassword   # must match docker-compose.yml default
"""

import socket

import pytest


def _postgres_reachable(host: str = "localhost", port: int = 5432, timeout: float = 1.0) -> bool:
    try:
        conn = socket.create_connection((host, port), timeout=timeout)
        conn.close()
        return True
    except OSError:
        return False


def pytest_collection_modifyitems(config, items):
    if not _postgres_reachable():
        skip_db = pytest.mark.skip(
            reason=(
                "PostgreSQL not reachable on localhost:5432. "
                "Start the test DB with: docker compose up -d  "
                "(and set POSTGRES_PASSWORD to match docker-compose.yml)"
            )
        )
        for item in items:
            if item.get_closest_marker("integration_db"):
                item.add_marker(skip_db)
