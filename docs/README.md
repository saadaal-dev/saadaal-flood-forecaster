# Documentation

This index describes the current implementation. It was checked against the tracked source, SQL, configuration,
container, cron, and test files on 2026-09-22.

## Start here

- [High-level design](high-level-design.md) — system context, external systems, pipeline, database, and deployment
  diagrams.
- [Local setup and project overview](../README.md) — installation, tests, and basic deployment.
- [Contributing](../CONTRIBUTING.md) — contribution workflow.
- [Improvement backlog](improvement-backlog.md) — prioritized gaps, planned improvements, completion criteria, and
  status workflow.

## Component guides

| Component                 | Responsibility                                                            | Guide                                                                |
|---------------------------|---------------------------------------------------------------------------|----------------------------------------------------------------------|
| Configuration and CLI     | Runtime settings and supported operator/developer commands                | [Configuration and CLI](components/configuration-and-cli.md)         |
| Data ingestion            | Open-Meteo, SWALIM, CSV, and optional sensor rainfall inputs              | [Data ingestion](components/data-ingestion.md)                       |
| Database and data model   | PostgreSQL schemas, tables, views, indexes, and record lifecycle          | [Database and data model](components/database.md)                    |
| ML pipeline               | Feature preparation, training, evaluation, inference, and model artifacts | [ML pipeline](components/ml-pipeline.md)                             |
| Risk and alerts           | Threshold classification and Mailjet notification behavior                | [Risk assessment and alerts](components/risk-and-alerts.md)          |
| Scheduling and deployment | Bash orchestration, cron, Docker, and failure behavior                    | [Scheduling and deployment](components/scheduling-and-deployment.md) |
| Operations and quality    | Logging, Sentry, health checks, tests, and diagnostics                    | [Operations and testing](components/operations-and-testing.md)       |

## Detailed references

- [Database diagram](flood-forecaster-datamodel.md)
- [Scripts reference](scripts-reference.md)
- [Field sensors: quick guide](sensors-quick-guide.md)
- [Field sensor data integration](sensor-readings-integration.md) — detailed technical reference
- [Sentry integration](sentry-integration.md)
- [Container deployment](container-deployment-guide.md)
- [Server command quick reference](server-quick-reference.md)

## Documentation boundaries

- `config/config.ini`, `amadeus_saadaal_flood_forecaster_cron`, and the implementation are authoritative when behavior
  changes.
- The scheduled production path performs **inference**, not model training. Training and evaluation are developer
  workflows.
- `docker-compose.yml` starts a local PostgreSQL service only; the application image is built separately with
  `Dockerfile`.
- Files describing one-off incidents or historical fixes are not part of this current-state documentation set.
- Documentation filenames use lowercase kebab-case. Conventional repository-level names such as `README.md`,
  `CONTRIBUTING.md`, and `LICENSE` are exceptions.

When changing behavior, update the relevant component guide and any affected diagram in the same pull request.
