# Improvement backlog

This is the canonical list of known gaps, risks, incomplete features, and worthwhile technical improvements in Saadaal
Flood Forecaster. It was verified against the repository on 2026-09-23.

The backlog describes work that is **not yet complete**, with the exception of items explicitly marked `Done`, which are
retained so that their stable IDs keep old pull request and incident references understandable. Current behavior and
operator warnings remain in the relevant domain guides; priority, status, and completion criteria live here to avoid
maintaining two competing task lists.

## How to use this backlog

### Status

| Status        | Meaning                                                                  |
|---------------|--------------------------------------------------------------------------|
| `Open`        | Verified problem; no implementation is in progress                       |
| `In progress` | An issue or pull request is actively addressing it                       |
| `Blocked`     | Work cannot continue until the stated dependency or decision is resolved |
| `Done`        | Completion criteria were verified and affected documentation was updated |
| `Won't do`    | Explicitly accepted behavior; record the decision and rationale          |

### Priority

| Priority | Meaning                                                                       |
|----------|-------------------------------------------------------------------------------|
| `P0`     | Active security, safety, or data-integrity risk requiring immediate attention |
| `P1`     | High operational or correctness risk; schedule next                           |
| `P2`     | Important reliability, maintainability, or completeness improvement           |
| `P3`     | Useful enhancement or cleanup with a safe current workaround                  |

### One-item workflow

1. Select one `Open` item, confirm its evidence is still current, and create an issue or pull request referencing its
   stable ID.
2. Change its status to `In progress` and add the issue/PR link.
3. Implement the smallest complete fix, including tests and migrations when applicable.
4. Update the relevant domain documentation in the same PR. Keep operational facts and warnings there, but keep planning
   details here.
5. Verify every “Done when” checkbox, mark the item `Done`, and record the merge reference and date.
6. Do not delete completed IDs; stable IDs keep old PR and incident references understandable.

## Summary

| ID       | Priority | Area                 | Improvement                                                 | Status |
|----------|----------|----------------------|-------------------------------------------------------------|--------|
| SEC-001  | P0       | Security             | Enable TLS certificate verification                         | Open   |
| SEC-002  | P1       | Security             | Stop persisting the complete container environment          | Open   |
| DATA-001 | P1       | Data                 | Define and test timestamp/timezone semantics                | Open   |
| DATA-002 | P1       | Data                 | Replace implicit missing-data behavior with explicit policy | Open   |
| DATA-003 | P2       | Data                 | Verify historical Open-Meteo incremental boundaries         | Open   |
| DATA-004 | P1       | Data                 | Harden SWALIM parsing and calendar handling                 | Open   |
| DATA-005 | P2       | Data                 | Enforce historical river-level uniqueness                   | Open   |
| DATA-006 | P2       | Data                 | Consolidate river-station metadata ownership                | Open   |
| DATA-007 | P3       | Data                 | Normalize loader date-range APIs                            | Open   |
| CLI-001  | P2       | CLI                  | Implement or remove exposed no-op options and commands      | Open   |
| SENS-001 | P2       | Sensors              | Validate sensor coverage before enablement                  | Open   |
| SENS-002 | P1       | Sensors              | Make missing sensor rainfall fall back safely               | Open   |
| SENS-003 | P2       | Sensors              | Resolve zero, negative, cadence, and timezone semantics     | Open   |
| SENS-004 | P3       | Sensors              | Decide whether to support IoT water-level readings          | Open   |
| SENS-005 | P2       | Sensors              | Validate mapping quality and duplicate labels               | Open   |
| SENS-006 | P1       | Sensors              | Add direct inference-merge tests                            | Open   |
| RISK-001 | P1       | Risk                 | Recalculate risk when predictions change                    | Open   |
| RISK-002 | P1       | Alerts               | Correct reference-date versus target-date display           | Open   |
| RISK-003 | P2       | Alerts               | Make alert policy and freshness handling configurable       | Open   |
| RISK-004 | P3       | Alerts               | Configure and test failed-email output                      | Open   |
| RISK-005 | P1       | Alerts               | Detect per-station ingestion and prediction staleness       | Open   |
| RISK-006 | P0       | Alerts               | Fix alert crash from Date/datetime regression               | Done   |
| DB-001   | P1       | Database             | Repair non-authoritative SQL views                          | Open   |
| DB-002   | P2       | Database             | Unify bootstrap and migration behavior                      | Open   |
| DB-003   | P3       | Database             | Define referential-integrity strategy                       | Open   |
| ML-001   | P2       | ML/Operations        | Remove hard-coded production station/model choices          | Open   |
| ML-002   | P2       | ML                   | Bind preprocessing configuration to model artifacts         | Open   |
| ML-003   | P2       | ML                   | Handle incomplete/future inputs explicitly                  | Open   |
| ML-004   | P2       | ML                   | Correct the evaluation baseline horizon                     | Open   |
| ML-005   | P3       | ML                   | Add prediction uncertainty                                  | Open   |
| ML-006   | P3       | ML                   | Complete model/preprocessor abstractions                    | Open   |
| OPS-001  | P1       | Operations           | Add externally observable job and container health          | Open   |
| OPS-002  | P2       | Operations           | Define retention, backup, and log-rotation policy           | Open   |
| OPS-003  | P2       | Operations           | Make local PostgreSQL initialization production-like        | Open   |
| OPS-004  | P2       | Operations           | Make scheduling timezone explicit                           | Open   |
| TEST-001 | P2       | Testing              | Complete the advertised tox integration environment         | Open   |
| DX-001   | P3       | Developer experience | Simplify and verify installation workflow                   | Open   |
| DOC-002  | P3       | Documentation        | Automate documentation consistency checks                   | Open   |

## Security

### SEC-001 — Enable TLS certificate verification

- **Priority:** P0
- **Status:** Open
- **Issue/PR:** —

**Problem:** Open-Meteo and SWALIM HTTPS requests explicitly disable certificate verification, allowing a network
attacker to impersonate an upstream service and alter model inputs.

**Evidence:**

- `fetch_openmeteo_data()` in `src/flood_forecaster/data_ingestion/openmeteo/common.py` passes `verify=False`.
- SWALIM GET and POST requests in `src/flood_forecaster/data_ingestion/swalim/river_level_api.py` pass `verify=False`.
- The active warning is documented in `docs/high-level-design.md` and `docs/components/data-ingestion.md`.

**Done when:**

- [ ] Certificate verification is enabled by default for every active upstream request.
- [ ] Any development-only bypass is explicit, defaults to secure, and logs a prominent warning.
- [ ] Open-Meteo and SWALIM integration tests cover the secure path.
- [ ] Deployment and ingestion documentation no longer describes unconditional TLS bypass.

### SEC-002 — Stop persisting the complete container environment

- **Priority:** P1
- **Status:** Open
- **Issue/PR:** —

**Problem:** `docker-entrypoint.sh` writes all process environment variables to the repository-root `.env` so cron can
read them. This can persist unrelated secrets and broadens access beyond the original process environment.

**Evidence:** `printenv > "$REPOSITORY_ROOT_PATH/.env"` in `docker-entrypoint.sh`.

**Done when:**

- [ ] Cron receives only the variables required by the application, without dumping the complete environment.
- [ ] Any generated secret file has explicit restrictive permissions and a documented lifecycle.
- [ ] Container tests confirm cron still receives required database, Mailjet, and observability variables.
- [ ] Deployment documentation describes the final secret-handling model.

## Data ingestion and quality

### DATA-001 — Define and test timestamp/timezone semantics

- **Priority:** P1
- **Status:** Open
- **Issue/PR:** —

**Problem:** Weather, river, sensor, cron, and database timestamps are converted inconsistently or rely on implicit UTC
assumptions. Date truncation near midnight can assign data to the wrong day.

**Evidence:**

- Repeated `TODO: verify UTC / timezone management` comments in database loaders in
  `src/flood_forecaster/data_ingestion/load.py`.
- Sensor grouping parses `reading_ts` with `utc=True` but ignores device `original_date` and `original_time`.
- Open-Meteo sends `timezone=auto` while database loaders normalize timestamps to UTC before dropping time.

**Done when:**

- [ ] A written contract defines the timezone for every source, stored timestamp, daily boundary, log, and cron
  schedule.
- [ ] Conversions happen explicitly at source boundaries rather than during ad hoc date truncation.
- [ ] Tests cover readings around UTC/local midnight, month/year boundaries, and timezone-aware/naive inputs.
- [ ] Data-model, ingestion, sensor, and deployment guides reflect the contract.

### DATA-002 — Replace implicit missing-data behavior with explicit policy

- **Priority:** P1
- **Status:** Open
- **Issue/PR:** —

**Problem:** Different loaders warn, forward-fill, zero-fill, or continue on missing dates. Some strict checks are
commented out, making model-input quality dependent on the call path.

**Evidence:**

- Commented `FIXME` missing-date errors in `src/flood_forecaster/data_ingestion/load.py`.
- `__weather_df_without_missing_dates()` forward-fills internal gaps and zero-fills leading gaps.
- River inference uses experimental last-value filling.

**Done when:**

- [ ] A per-source policy defines reject, interpolate, forward-fill, zero-fill, and maximum-gap rules.
- [ ] Policies are configurable where operationally necessary and emit structured quality metrics.
- [ ] Inference fails clearly when required quality thresholds are not met.
- [ ] Tests cover leading, internal, trailing, consecutive, and all-missing ranges for every loader.
- [ ] Operations documentation explains recovery and failure behavior.

### DATA-003 — Verify historical Open-Meteo incremental boundaries

- **Priority:** P2
- **Status:** Open
- **Issue/PR:** —

**Problem:** Historical ingestion derives the next start timestamp from the table maximum while code comments report
duplicate and “yesterday” boundary problems. Upsert and cleanup hide some symptoms but do not establish correct date
semantics.

**Evidence:** `FIXME` comments in `src/flood_forecaster/data_ingestion/openmeteo/historical_weather.py` around the end
date and `max_date + one day` logic.

**Done when:**

- [ ] Incremental ranges are defined in calendar dates for all configured locations.
- [ ] Tests cover empty tables, current data, stale data, time components, and repeated runs.
- [ ] Repeated ingestion is idempotent without requiring post-fetch duplicate cleanup.
- [ ] Obsolete quick-fix comments and cleanup paths are removed or documented as migrations.

### DATA-004 — Harden SWALIM parsing and calendar handling

- **Priority:** P1 (raised from P2 on 2026-09-22: this is no longer hypothetical, see below)
- **Status:** Open
- **Issue/PR:** —

**Problem:** Latest-level ingestion depends on the first seven HTML rows; chart history derives an endpoint by string
replacement and skips leap-day conversion failures. Upstream format changes can silently reduce coverage.

**This has now happened in production.** On 2026-05-12 SWALIM inserted a new station, `Deefow`, into the
`maps-data-grid` table on <https://frrims.faoswalim.org/rivers/levels>. That pushed `Jowhar` from row 7 to row 8, where
`df.head(7)` discards it. Jowhar river levels stopped being ingested that day and Jowhar predictions stopped 30 days
later, when the last reading aged out of the inference lag window. The outage went undetected for over four months.

**Evidence:**

- `fetch_latest_river_data()` truncates with `df = df.head(7)  # Get the 7 stations`, and
  `_get_new_river_levels()` skips non-matching stations via `if row_list:` with no `else` branch, so a dropped station
  produces no log line at all. Both in `src/flood_forecaster/data_ingestion/swalim/river_level_api.py`.
- Live page row order as at 2026-09-23: `Dollow, Luuq, Bardheere, Bualle, Belet Weyne, Deefow, Bulo Burti, Jowhar`.
  Simulating `head(7)` against this order predicts exactly six ingested stations
  (`Bardheere, Belet Weyne, Bualle, Bulo Burti, Dollow, Luuq`) and Jowhar missing.
- Production data matches that prediction exactly: `flood_forecaster.historical_river_level` recorded 7 stations per day
  through 2026-05-11 and 6 per day from 2026-05-12, with `Jowhar` the only one absent.
- `Deefow` is not present in `data/static/station-metadata.csv`, `flood_forecaster.river_station_metadata`, or
  `public.station`, so no station inventory would have flagged its arrival.
- `fetch_river_data_from_chart_api()` is unaffected: it POSTs to `/rivers/graph` with an explicit `station_id` and the
  response self-identifies via `otherDetails.stationName`. For Jowhar it returned 134/134 days of the outage window.

**Done when:**

- [ ] Expected station identities are selected by stable identifiers/names, not HTML row position; `head(7)` is removed.
- [ ] A station present in the configured inventory but absent from the upstream response logs an actionable warning
      and is reflected in the command's exit status.
- [ ] An unrecognized upstream station (such as `Deefow`) is reported so the inventory can be reviewed deliberately.
- [ ] Endpoint configuration is explicit.
- [ ] Leap years and missing `previous_year`/`gaugeReadingList` structures are handled safely.
- [ ] Fixture tests cover changed HTML, empty responses, malformed JSON, leap day, and partial station data, including a
      regression fixture with eight rows and a new station inserted above `Jowhar`.
- [ ] Failures produce actionable logs and non-success status where appropriate.
- [ ] A decision is recorded on whether `/rivers/graph` (per-station, self-identifying) should replace the HTML scrape as
      the primary daily source; see the note under RISK-005 on source completeness.

### DATA-005 — Enforce historical river-level uniqueness

- **Priority:** P2
- **Status:** Open
- **Issue/PR:** —

**Problem:** `historical_river_level` has no database uniqueness constraint; duplicate prevention is
application-specific and direct writes can create conflicting feature rows.

**Evidence:** `sql/database_bootstrap.sql`, `docs/flood-forecaster-datamodel.md`, and the defensive deduplication in
`load_river_level_db()`.

**Done when:**

- [ ] Existing duplicates are audited and resolved with an explicit retention rule.
- [ ] A migration adds an appropriate station/date uniqueness constraint.
- [ ] Every ingestion/backfill path uses conflict-safe inserts or upserts.
- [ ] Database integration tests cover duplicate attempts and migration of existing data.

### DATA-006 — Consolidate river-station metadata ownership

- **Priority:** P2
- **Status:** Open
- **Issue/PR:** —

**Problem:** Risk assessment reads static CSV metadata while a database metadata table and multiple CSV inventories also
exist. Thresholds and station identifiers can diverge.

**Evidence:**

- `get_river_stations_static()` and TODOs in `src/flood_forecaster/data_model/river_station.py`.
- `river_station_metadata` in `sql/database_bootstrap.sql`.
- Static files `station-metadata.csv` and `river_stations_metadata.csv` have different roles/shapes.

**Done when:**

- [ ] One authoritative source and synchronization process are defined.
- [ ] Risk, ingestion, views, and CLI commands use consistent station identifiers and thresholds.
- [ ] Validation detects missing, duplicate, or conflicting station metadata.
- [ ] Migration and rollback instructions cover existing deployments.

### DATA-007 — Normalize loader date-range APIs

- **Priority:** P3
- **Status:** Open
- **Issue/PR:** —

**Problem:** Database loader functions require both date bounds while CSV helpers accept optional bounds, creating
inconsistent APIs and caller behavior.

**Evidence:** TODO above the database loaders and the `__load_csv()` signature in
`src/flood_forecaster/data_ingestion/load.py`.

**Done when:**

- [ ] A common date-range contract defines required, omitted, and one-sided bounds.
- [ ] Database and CSV loaders implement the same contract or expose intentionally different, clearly named interfaces.
- [ ] Existing callers are migrated without changing date inclusivity.
- [ ] Tests cover both bounds, each one-sided bound, and no bounds.

### CLI-001 — Implement or remove exposed no-op options and commands

- **Priority:** P2
- **Status:** Open
- **Issue/PR:** —

**Problem:** The CLI advertises behavior that it does not perform.

**Evidence:**

- `data-ingestion load-csv` only prints a placeholder message.
- `fetch-openmeteo --empty-table` is accepted but not passed to the fetch implementation.

**Done when:**

- [ ] Each exposed command/option either performs its documented behavior or is removed with a migration note.
- [ ] Exit status distinguishes success from unimplemented/invalid use.
- [ ] CLI tests verify effects, not only option parsing.
- [ ] `docs/components/configuration-and-cli.md` matches the final interface.

## Field sensors

The current operational facts remain in `docs/sensors-quick-guide.md` and the technical details remain in
`docs/sensor-readings-integration.md`.

### SENS-001 — Validate sensor coverage before enablement

- **Priority:** P2
- **Status:** Open
- **Issue/PR:** —

**Problem:** The flag can be enabled even when no mapped sensor location participates in a production station's weather
inputs. This is currently true for all three mapped sites and all five scheduled stations.

**Done when:**

- [ ] A command or startup check reports sensor-to-production coverage.
- [ ] Enabling sensors with zero overlap fails configuration validation or emits an unmistakable warning.
- [ ] Tests cover zero, partial, and full overlap.
- [ ] Quick and technical sensor guides are regenerated or updated when mappings change.

### SENS-002 — Make missing sensor rainfall fall back safely

- **Priority:** P1
- **Status:** Open
- **Issue/PR:** —

**Problem:** Once any sensor data exists, the inference loader can forward-fill a previous daily rainfall total or
zero-fill a location, then let that synthetic value override valid Open-Meteo data.

**Evidence:** `load_inference_sensor_rainfall()`, `__weather_df_without_missing_dates()`, and the sensor-first merge in
`src/flood_forecaster/ml_model/api.py`.

**Done when:**

- [ ] Missing sensor rows remain null through the merge so Open-Meteo provides the fallback, unless a separately
  configured and justified imputation policy is selected.
- [ ] Daily rainfall totals are never repeated implicitly across missing days.
- [ ] Tests cover empty, partial, leading-gap, internal-gap, and multi-location sensor data.
- [ ] Sensor documentation describes the corrected behavior.

### SENS-003 — Resolve sensor value, cadence, and timezone semantics

- **Priority:** P2
- **Status:** Open
- **Issue/PR:** —

**Problem:** Zero rainfall is discarded as a sentinel, values from `-100` to below zero survive cleaning,
`precipitation_hours` is a row count rather than measured hours, and UTC grouping ignores device-local date/time.

**Done when:**

- [ ] Device owners confirm units, valid ranges, zero semantics, cadence, duplicate behavior, and timestamp timezone.
- [ ] Cleaning rules are configuration- or sensor-type-aware and reject all impossible rainfall values.
- [ ] Coverage uses a clearly named metric, with duplicate timestamp handling.
- [ ] Wet, dry, malformed, duplicate, and midnight-boundary fixtures are tested.
- [ ] Validation and comparison commands expose rejected-row and coverage counts.

### SENS-004 — Decide whether to support IoT water-level readings

- **Priority:** P3
- **Status:** Open
- **Issue/PR:** —

**Problem:** The inventory lists water-level sensors, but the integration only queries rainfall and does not connect IoT
water levels to river features. This is either a missing feature or potentially misleading inventory scope.

**Done when:**

- [ ] Product/data owners decide whether IoT water-level data is in scope.
- [ ] If in scope, units, calibration, station identity, quality controls, and SWALIM fallback/precedence are designed
  and tested.
- [ ] If out of scope, documentation and inventory clearly label water-level rows as informational only.

### SENS-005 — Validate mapping quality and duplicate labels

- **Priority:** P2
- **Status:** Open
- **Issue/PR:** —

**Problem:** Mapping uses nearest geographic distance only, and duplicate device labels collapse to the first CSV row.
Watershed, elevation, sensor type, and conflicting coordinates are not evaluated.

**Done when:**

- [ ] Inventory validation rejects a label with conflicting coordinates and reports duplicate rows/types.
- [ ] Mappings can be explicitly approved or overridden instead of relying only on nearest distance.
- [ ] Coverage output includes distance and approval status.
- [ ] Tests cover ties, conflicting duplicates, threshold boundaries, and overrides.

### SENS-006 — Add direct inference-merge tests

- **Priority:** P1
- **Status:** Open
- **Issue/PR:** —

**Problem:** Mapping, sensor loading, and comparison CLI behavior have unit tests, but the `use_sensor_rainfall` branch
inside `infer()` is not directly tested.

**Done when:**

- [ ] Tests prove that disabled and empty-sensor paths leave weather unchanged.
- [ ] Tests prove precedence and fallback for partial sensor coverage.
- [ ] Tests cover multiple locations, future dates, schema errors, and the selected gap policy.
- [ ] The tests fail if synthetic sensor values unexpectedly replace Open-Meteo.

## Risk assessment and alerts

### RISK-001 — Recalculate risk when predictions change

- **Priority:** P1
- **Status:** Open
- **Issue/PR:** —

**Problem:** Prediction upserts change `level_m` without clearing `risk_level`, while risk assessment updates only rows
where `risk_level IS NULL`. A changed prediction can retain a stale classification and affect alerts.

**Evidence:** `create_inference_insert_statement()` and `create_update_statement()`.

**Done when:**

- [ ] Updating a prediction invalidates or atomically recalculates its risk classification.
- [ ] Manual overrides, if required, have a separate explicit representation.
- [ ] Tests cover threshold crossings in both directions after re-inference.
- [ ] Risk and operations guides no longer require manual null-reset instructions.

### RISK-002 — Correct reference-date versus target-date display

- **Priority:** P1
- **Status:** Open
- **Issue/PR:** —

**Problem:** Predictions store a reference date and horizon, but alert output labels the reference date as “Prediction
date.” `get_df_by_date()` computes a forecast date and immediately overwrites it with the reference date.

**Evidence and starting points** (all in `src/flood_forecaster/alert_module/flood_status.py`, verified 2026-09-23):

- Line 36 computes `result_df['date'] + forecast_days`; line 37 immediately overwrites it with
  `result_df['date'].dt.date`. Line 36 is therefore dead code and the emitted value is the reference date.
- Line 36 is also inconsistent with the formula in the first checklist item below: it adds `forecast_days` with no
  `- 1`, so the discarded value is itself a day beyond the intended target date. Deleting line 37 is **not** a
  sufficient fix; the formula has to be decided and applied deliberately.
- Line 43 renames the resulting column to `Prediction date`, which is the label an operator reads in the alert email.
  That string is the user-visible half of this item.
- The empty-result branch above returns different column names entirely
  (`location_name`, `flood_risk`, `water_level_m`, `predicted_flood_date`) from the populated branch
  (`Station`, `Flood risk`, `Water level (m)`, `Prediction date`). Whichever labels are chosen should be made
  consistent across both branches.

**Tests that pin the current behavior and must be updated together with the fix:**

- `src/tests/unit/test_flood_status.py::TestGetDfByDate::test_prediction_date_is_a_date_value` asserts that
  `Prediction date` equals the stored reference date. That assertion is deliberate (it guards the RISK-006 `.dt`
  crash), but it encodes pre-RISK-002 semantics and will fail once the target date is emitted. Keep an assertion on
  the column's *type* and add one for the new target-date *value*.
- `test_filters_earlier_dates_and_other_risk_levels` in the same file fixes `forecast_days=3` for every row, so it is
  a convenient place to assert the chosen formula.

**Done when:**

- [ ] A single target-date formula (`reference date + forecast_days - 1`) is used consistently.
- [ ] Alert tables label reference and target dates unambiguously.
- [ ] Queries, views, freshness checks, and tests use the intended date.
- [ ] The dead computation on line 36 is removed rather than left overwritten.
- [ ] Empty and populated results from `get_df_by_date()` use the same column labels.
- [ ] Data-model and alert documentation match the final semantics.

### RISK-003 — Make alert policy and freshness handling configurable

- **Priority:** P2
- **Status:** Open
- **Issue/PR:** —

**Problem:** Alerts are hard-coded to `full` risk and a two-day freshness rule. The code also assumes a latest
prediction exists before comparing dates.

**Done when:**

- [ ] Minimum alert risk and maximum accepted age are validated configuration values.
- [ ] Empty prediction tables and timezone boundaries have explicit outcomes.
- [ ] Tests cover each risk threshold, fresh/stale/empty data, delivery success, and delivery failure.
- [ ] Operators can distinguish “no risk,” “stale predictions,” and “alert delivery failed.”

### RISK-004 — Configure and test failed-email output

- **Priority:** P3
- **Status:** Open
- **Issue/PR:** —

**Problem:** Failed alert HTML is always written to `flood_alert_message.html` in the current working directory.

**Evidence:** TODO in `save_alert_as_file()`.

**Done when:**

- [ ] Output directory/name and retention are configured.
- [ ] Writes are atomic and failures are surfaced.
- [ ] Tests cover writable and unwritable destinations.
- [ ] Operations documentation identifies where failed alerts are stored.

### RISK-005 — Detect per-station ingestion and prediction staleness

- **Priority:** P1
- **Status:** Open
- **Issue/PR:** —

**Problem:** Every freshness and failure check in the pipeline is aggregate, so a single station can stop producing
predictions indefinitely while monitoring stays green. Jowhar stopped on 2026-06-10 and the gap was found four months
later by manual inspection, not by any alert (see DATA-004 for the root cause).

**Evidence:**

- `alert.py` checks `db_client.get_max_date(PredictedRiverLevel)` across all locations, with no `GROUP BY`
  `location_name`. Four healthy stations keep the check passing.
- `scripts/amadeus_saadaal_flood_forecaster_resilient.sh` catches a failed per-station inference and continues
  ("⚠️ Inference failed for $STATION, continuing with other stations"), exiting `2` on partial success. Nothing
  downstream consumes that exit code. **Confirmed as the deployed variant:** the crontab inside the running
  `srv-captain--saadaal-flood-forecaster` container is `0 12 * * * root bash .../amadeus_saadaal_flood_forecaster_resilient.sh`,
  which matches the daily template in `amadeus_saadaal_flood_forecaster_cron` (the only cron file the `Dockerfile`
  installs) rather than `..._cron_frequent`.
- `_get_new_river_levels()` emits no log line for a station that produced no row, so the ingestion gap that started the
  incident was silent at every layer.
- `flood_forecaster.predicted_river_level.created_at` is NULL on all 4694 rows, so there is no record of when any
  prediction was actually produced. The outage had to be dated from the `date` column instead. This removes the
  cheapest available forensic signal and compounds the detection gap; see also OPS-001 and DB-002.
- This is the alerting counterpart to OPS-001, which covers run-level observability; this item covers per-station data
  and prediction coverage specifically.

**Done when:**

- [ ] Ingestion and prediction freshness are evaluated per station against the configured production station list, not
      only in aggregate.
- [ ] A station missing from ingestion, or with no prediction newer than a configured maximum age, raises an alert that
      names the station.
- [ ] Partial-success exit status from the orchestration script reaches monitoring/Sentry distinctly from full success.
- [ ] Tests cover one station stale with the rest healthy, all stations stale, and an empty prediction table.
- [ ] Operations documentation states the per-station thresholds and the response procedure.

**Note on source selection (informs DATA-004):** `public.station_river_data` kept Jowhar flowing throughout the outage,
which makes it tempting as a replacement source. It should not become the primary one, for two independent reasons.

*It is outside this project's control.* The table is written by `/usr/bin/fetch_river.sh`, invoked from the **host** root
crontab as `0 10 * * *`. The host OS timezone is EAT (UTC+3), so that is 07:00 UTC, which matches the observed write
clock on `created_at` exactly. The script's implementation has not been inspected and it is not owned by this
repository. An earlier revision of this note claimed the table was populated from SWALIM's `/rivers/graph`; that was
inferred from `legacy/data-extractor/new_river.py`, which is neither used nor owned here, and the claim is withdrawn.
Reading the table as a fallback is acceptable; depending on it couples the forecaster to an unverified upstream that can
change without notice.

*It is less complete.* Over a 90-day window it carried 73 days for Belet Weyne and Bulo Burti against 86 from the
scrape, and Bardheere and Bualle stop at 2026-08-17. Each run writes only a 0-1 day window, so it shares the scrape's
property that a missed day is lost permanently.

Querying SWALIM's `/rivers/graph` directly is the more complete option, verified live on 2026-09-23: 134/134 days of
Jowhar's outage window against 124 from `public.station_river_data`. It is addressed by `station_id` and the response
self-identifies through `otherDetails.stationName`, making it immune to the row-position failure described in DATA-004.
Two caveats: it is an undocumented internal endpoint with no stability contract or versioning, and no public SWALIM API
is documented anywhere. Requesting a supported data feed from FAO SWALIM would remove that risk and is worth pursuing
independently of any code change.

Any source change should be validated on completeness per station, not only on whether it survived this incident.

### RISK-006 — Fix alert crash from Date/datetime regression

- **Priority:** P0
- **Status:** Done (2026-09-23, branch `fix/risk-006-alert-date-regression`)
- **Issue/PR:** —

**Problem:** The `flood-cli alert` command crashed on every run before any alert could be evaluated or sent, so the
entire alerting phase (Phase 4) was non-functional in production. Because this is the delivery path for flood warnings,
the outage was a safety risk, not only a correctness one.

**Evidence:**

- Production log (2026-09-23, Phase 4 "Send alerts") ended with
  `AttributeError: 'datetime.date' object has no attribute 'date'` and `flood-cli alert` exiting with code 1.
- `get_df_by_date()` in `src/flood_forecaster/alert_module/flood_status.py` filtered with
  `func.date(PredictedRiverLevel.date) >= date_begin.date()`, calling `.date()` on `date_begin`.
- `date_begin` is supplied by `main()` in `src/flood_forecaster/alert_module/alert.py` as
  `latest_db_date = db_client.get_max_date(PredictedRiverLevel)`.
- `PredictedRiverLevel.date` is `Column(Date)` (see `src/flood_forecaster/data_model/river_level.py`), so
  `get_max_date()` returns a `datetime.date`, which has no `.date()` method. The parameter was annotated
  `date_begin: datetime`, masking the mismatch.
- **Second crash on the same path:** a `Date` column is returned by `pd.read_sql()` as object-dtype `datetime.date`
  values, so `result_df['date'] + pd.to_timedelta(...)` raised
  `TypeError: unsupported operand type(s) for +: 'TimedeltaArray' and 'datetime.date'` and `result_df['date'].dt.date`
  raised `AttributeError: Can only use .dt accessor with datetimelike values`. This was latent behind the first crash and
  triggered only when the query returned rows, meaning it would have surfaced precisely when an alert had to be sent.
- Regression origin: commit `c79bd7c` ("Refactor date handling in predicted_river_level ... Now one prediction per
  day") changed the column from `DateTime` to `Date` without updating either site. Under the previous `DateTime` column,
  `get_max_date()` returned a `datetime.datetime` and the column arrived as `datetime64`, so both worked.

**Done when:**

- [x] `get_df_by_date()` no longer calls `.date()` on a value that is already a `datetime.date`; the date filter compares
      directly against the `Date` column and the redundant `func.date(...)` wrapper is removed.
- [x] `get_df_by_date()` accepts the actual type returned by `get_max_date()`; the annotation is
      `Union[date, datetime]` and a `datetime` is narrowed to its calendar day.
- [x] The retrieved `date` column is normalized to a datetime dtype before `.dt` is used, so returning rows no longer
      raises.
- [x] `flood-cli alert` completes without raising on a database whose `predicted_river_level.date` is a `Date` column.
- [x] A regression test exercises the alert query path against `Date`-typed prediction dates so a future column-type
      change cannot silently break delivery again
      (`src/tests/unit/test_flood_status.py`, verified to fail against the pre-fix code).

**Not addressed here (still open):** the displayed "Prediction date" remains the stored reference date rather than the
forecast target date; that semantic fix stays with RISK-002, which owns the target-date formula.

## Database

### DB-001 — Repair non-authoritative SQL views

- **Priority:** P1
- **Status:** Open
- **Issue/PR:** —

**Problem:** Optional views do not match application writes: inference does not populate `station_number`, risk summary
compares uppercase labels while the application writes lowercase labels, and date filters use stored reference dates as
if they were target dates.

**Evidence:** `sql/database_views.sql`, `create_inference_insert_statement()`, and `docs/components/database.md`.

**Done when:**

- [ ] Joins use a populated stable key or an explicitly normalized station name.
- [ ] Risk comparisons match canonical labels.
- [ ] Reference and target dates are exposed and filtered correctly.
- [ ] Database integration tests verify view rows and aggregates.
- [ ] Views can be described as authoritative in the database guide.

### DB-002 — Unify bootstrap and migration behavior

- **Priority:** P2
- **Status:** Open
- **Issue/PR:** —

**Problem:** A fresh `database_bootstrap.sql` database differs from a migrated database: indexes/views are separate, and
the predicted-level `updated_at` trigger exists only in a migration. Plain `ADD CONSTRAINT` statements also make
bootstrap reuse unsafe.

**Done when:**

- [ ] A documented migration tool or ordered, idempotent migration set defines schema evolution.
- [ ] Fresh and upgraded databases produce the same tables, constraints, indexes, views, triggers, and comments.
- [ ] CI tests both fresh bootstrap and upgrade paths.
- [ ] Compose and deployment instructions invoke the same supported process.

### DB-003 — Define referential-integrity strategy

- **Priority:** P3
- **Status:** Open
- **Issue/PR:** —

**Problem:** Relationships between station metadata, river observations, and predictions are conceptual name/code joins
with no foreign keys. This may be intentional because some sources are externally owned, but orphaned or inconsistently
named application rows are not automatically prevented.

**Done when:**

- [ ] The team records which relationships should be database-enforced and which must remain loose.
- [ ] Enforceable relationships receive migrations and delete/update behavior tests.
- [ ] Non-enforced relationships receive automated integrity checks with actionable reports.
- [ ] The data-model diagram distinguishes enforced constraints from conceptual joins.

## Machine learning and scheduling

### ML-001 — Remove hard-coded production station/model choices

- **Priority:** P2
- **Status:** Open
- **Issue/PR:** —

**Problem:** Production scripts hard-code five stations, horizon seven, and `Prophet_001`; adding a station or changing
production models requires shell edits in multiple places.

**Done when:**

- [ ] One validated production configuration defines stations, horizon, model, and output mode.
- [ ] Resilient, batch, and catch-up workflows consume the same configuration.
- [ ] Startup validation confirms matching mappings and model artifacts exist.
- [ ] Tests prove a configuration change alters orchestration without script changes.

### ML-002 — Bind preprocessing configuration to model artifacts

- **Priority:** P2
- **Status:** Open
- **Issue/PR:** —

**Problem:** Lag windows and preprocessing choices live in global `config.ini`, while model artifacts depend on them.
Changing configuration can make an existing artifact incompatible without a clear version check.

**Evidence:** FIXME in `config/config.ini`, preprocessor TODOs in `ml_model/api.py`, and model naming behavior.

**Done when:**

- [ ] Each model artifact records and validates its preprocessor type, lag features, horizon, feature schema, and
  training version.
- [ ] Inference rejects incompatible runtime configuration with an actionable error.
- [ ] Artifact compatibility and migration tests exist.
- [ ] ML documentation describes the versioning contract.

### ML-003 — Handle incomplete and future inputs explicitly

- **Priority:** P2
- **Status:** Open
- **Issue/PR:** —

**Problem:** ML package notes and loader comments report confusing schema failures or ad hoc filling when future or
incomplete inputs are requested.

**Evidence:** `src/flood_forecaster/ml_model/DESIGN.md`, missing-data paths in `load.py`, and completeness checks in
`infer()`.

**Done when:**

- [ ] Supported historical/future inference windows are defined and validated before preprocessing.
- [ ] Missing inputs return domain-specific errors rather than downstream Pandera/type failures.
- [ ] Boundary tests cover earliest/latest supported references and unavailable forecast horizons.
- [ ] CLI output tells operators what data is missing and how to recover it.

### ML-004 — Correct the evaluation baseline horizon

- **Priority:** P2
- **Status:** Open
- **Issue/PR:** —

**Problem:** Evaluation compares against a previous-day baseline using `shift(1)` regardless of `forecast_days`, and the
source questions whether the selected horizon should be used.

**Done when:**

- [ ] The baseline definition is agreed for each horizon.
- [ ] Evaluation aligns baseline and target rows without accidental index truncation.
- [ ] Tests cover horizons 1, 7, and another configured value.
- [ ] Evaluation output labels the baseline method.

### ML-005 — Add prediction uncertainty

- **Priority:** P3
- **Status:** Open
- **Issue/PR:** —

**Problem:** Prophet and XGBoost wrappers return point predictions without uncertainty, leaving operators unable to
distinguish confident and uncertain threshold crossings.

**Done when:**

- [ ] Product requirements define how uncertainty affects storage, risk, and alerts.
- [ ] Supported models expose calibrated intervals or another documented confidence measure.
- [ ] Schema migrations and evaluation metrics support uncertainty.
- [ ] Calibration and alert-display tests exist.

### ML-006 — Complete model/preprocessor abstractions

- **Priority:** P3
- **Status:** Open
- **Issue/PR:** —

**Problem:** `ml_model/api.py` and `registry.py` still contain model/preprocessor-specific TODOs, CSV-only intermediate
stages, and duplicated orchestration assumptions. Bulk inference also inserts each combination independently and catches
errors without a final failure status.

**Done when:**

- [ ] Model and preprocessor interfaces define train, load, infer, evaluate, serialize, and feature-contract behavior.
- [ ] Supported intermediate input formats are explicit.
- [ ] Bulk operations report aggregate success/failure and use efficient persistence.
- [ ] Contract tests run against every registered model implementation.
- [ ] `src/flood_forecaster/ml_model/DESIGN.md` describes current architecture rather than a historical issue list.

## Operations and deployment

### OPS-001 — Add externally observable job and container health

- **Priority:** P1
- **Status:** Open
- **Issue/PR:** —

**Problem:** The entrypoint tails a log to stay alive; cron failures or stale predictions do not make the container
unhealthy, and cron does not publish the resilient script's `0`/`1`/`2` result externally.

**Done when:**

- [ ] Each scheduled run records start/end time, status, failed stages, and exit code in a machine-readable signal.
- [ ] A container health check detects dead cron, stale successful runs, and critical data/prediction staleness.
- [ ] Partial success (`2`) is visible to monitoring/Sentry without being mistaken for full success.
- [ ] Container and failure-path tests verify healthy, degraded, and unhealthy states.
- [ ] Operations and deployment docs define response procedures.

### OPS-002 — Define retention, backup, and log-rotation policy

- **Priority:** P2
- **Status:** Open
- **Issue/PR:** —

**Problem:** The repository defines no retention, archival, automatic backup, or cron-log rotation policy. Long-running
databases/log files can grow indefinitely, while recovery expectations are unspecified.

**Done when:**

- [ ] Owners approve retention and recovery objectives per table/artifact/log.
- [ ] Backup, restore, cleanup, and dry-run procedures are implemented and tested.
- [ ] Model artifacts and externally owned sensor data have explicit ownership boundaries.
- [ ] Disk/database growth is monitored and logs rotate without losing incident evidence.
- [ ] The operations guide includes scheduled maintenance and restore verification.

### OPS-003 — Make local PostgreSQL initialization production-like

- **Priority:** P2
- **Status:** Open
- **Issue/PR:** —

**Problem:** `docker-compose.yml` initializes only bootstrap tables, omits indexes/views/migration-only objects, and has
no durable named volume. Local integration behavior can differ from deployed schema behavior.

**Done when:**

- [ ] Local initialization uses the supported migration path and creates the complete schema.
- [ ] Storage persistence is an explicit named volume or clearly documented ephemeral choice.
- [ ] A schema-health test verifies expected constraints, indexes, views, and triggers after startup.
- [ ] Local and deployment guides describe intentional differences only.

### OPS-004 — Make scheduling timezone explicit

- **Priority:** P2
- **Status:** Open
- **Issue/PR:** —

**Problem:** Cron runs at `12:00` in the container timezone, but the image does not set `TZ`; logs, data-day boundaries,
and operator expectations can diverge.

**Done when:**

- [ ] The production timezone is an explicit image/deployment setting with a documented default.
- [ ] Startup logs show effective timezone and next expected run.
- [ ] Tests or deployment checks verify cron interpretation.
- [ ] This decision aligns with DATA-001 daily boundaries.

## Testing, developer experience, and documentation

### TEST-001 — Complete the advertised tox integration environment

- **Priority:** P2
- **Status:** Open
- **Issue/PR:** —

**Problem:** `tox.ini` lists `test-integration` in `envlist` but defines no corresponding environment, so the advertised
default matrix is incomplete.

**Done when:**

- [ ] `test-integration` has explicit dependencies, commands, markers, service prerequisites, and skip/failure
  behavior—or is removed from `envlist`.
- [ ] CI invokes the intended unit, API integration, and database integration categories.
- [ ] Test documentation and local commands match CI.

### DX-001 — Simplify and verify installation workflow

- **Priority:** P3
- **Status:** Open
- **Issue/PR:** —

**Problem:** `README.md` records a TODO to simplify `install.sh`; manual instructions mix editable installs and
requirements generation, while container installation uses a different locked path.

**Done when:**

- [ ] One supported local installation command and one locked deployment command are defined.
- [ ] `install.sh` delegates to `pyproject.toml`/`uv.lock` without duplicating dependency logic.
- [ ] Clean-environment tests verify install, `flood-cli --help`, and uninstall.
- [ ] README removes the TODO and contradictory steps.

### DOC-002 — Automate documentation consistency checks

- **Priority:** P3
- **Status:** Open
- **Issue/PR:** —

**Problem:** Dates, station counts, config defaults, CLI options, source paths, and local links are manually
cross-checked and can drift from implementation.

**Done when:**

- [ ] CI checks Markdown formatting and local links.
- [ ] Tests verify documented station/sensor mappings and important config defaults from source data.
- [ ] CLI examples are smoke-tested with `--help` or controlled fixtures.
- [ ] Documentation review dates have a defined meaning and update policy.

## Source TODO/FIXME disposition

When an item is implemented, remove obsolete TODO/FIXME comments. If a comment remains, reference the stable backlog ID
so future searches lead here.

| Source area                       | Existing comment/theme                                    | Backlog item                 |
|-----------------------------------|-----------------------------------------------------------|------------------------------|
| `data_ingestion/load.py`          | Optional ranges, timezone, missing dates, fill edge cases | DATA-001, DATA-002, DATA-007 |
| `openmeteo/historical_weather.py` | Yesterday/incremental duplicate boundaries                | DATA-003                     |
| `swalim/river_level_api.py`       | Station IDs, endpoint, leap years, `head(7)` truncation   | DATA-004, DATA-006, RISK-005 |
| `data_model/river_station.py`     | Replace static metadata with model/database read          | DATA-006                     |
| `config/config.ini`               | Move lag/horizon settings into model configuration        | ML-002                       |
| `ml_model/api.py`, `registry.py`  | Preprocessor/model/input abstractions                     | ML-002, ML-003, ML-006       |
| `ml_model/api.py`                 | Baseline shift and prediction-date semantics              | ML-004, RISK-002             |
| Prophet/XGBoost wrappers          | Prediction uncertainty                                    | ML-005                       |
| `alert_module/alert.py`           | Failed-alert filename                                     | RISK-004                     |
| CLI data ingestion                | Placeholder CSV loader and ignored empty-table flag       | CLI-001                      |
| CLI bulk inference                | Naive per-combination writes/error reporting              | ML-006                       |
| `README.md`, `install.sh`         | Packaging/install simplification                          | DX-001                       |

## Domain-document rule

Keep a limitation in a domain guide when a reader must know it to operate the current system safely—for example, sensor
zero handling or stale risk labels. Add its backlog ID near that warning. Do not copy priority, status, proposed
implementation, or the full completion checklist into the domain guide; link to this file instead.
