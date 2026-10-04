# Improvement backlog

This is the canonical list of known gaps, risks, incomplete features, and worthwhile technical improvements in Saadaal
Flood Forecaster. It was verified against the repository on 2026-09-23.

The backlog describes work that is **not yet complete**, with the exception of items explicitly marked `Done`, which are
retained so that their stable IDs keep old pull request and incident references understandable. Current behavior and
operator warnings remain in the relevant domain guides; priority, status, and completion criteria live here to avoid
maintaining two competing task lists.

Items that originate in a research session cite their measurements rather than restating them. That evidence lives in
[`studies/`](studies/), which is dated and not rewritten as the system changes — currently
[June 2026 improvement studies](studies/2026-06-improvement-studies.md).

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
| DATA-004 | P1       | Data                 | Replace positional SWALIM scraping with per-station fetch   | Open   |
| DATA-005 | P1       | Data                 | Enforce historical river-level uniqueness                   | Done   |
| DATA-006 | P2       | Data                 | Consolidate river-station metadata ownership                | Open   |
| DATA-007 | P3       | Data                 | Normalize loader date-range APIs                            | Open   |
| DATA-009 | P1       | Data                 | Guarantee a complete lag window per station                 | Open   |
| DATA-010 | P3       | Data                 | Separate absent upstream readings from fetch failures       | Open   |
| DATA-011 | P2       | Data                 | Decide the rainfall source strategy                         | Open   |
| DATA-012 | P2       | Data                 | Add the selected new sources to the ingestion pipeline      | Open   |
| CLI-001  | P2       | CLI                  | Implement or remove exposed no-op options and commands      | Open   |
| SENS-001 | P2       | Sensors              | Validate sensor coverage before enablement                  | Open   |
| SENS-002 | P1       | Sensors              | Make missing sensor rainfall fall back safely               | Open   |
| SENS-003 | P2       | Sensors              | Resolve zero, negative, cadence, and timezone semantics     | Open   |
| SENS-004 | P3       | Sensors              | Decide whether to support IoT water-level readings          | Open   |
| SENS-005 | P2       | Sensors              | Validate mapping quality and duplicate labels               | Open   |
| SENS-006 | P1       | Sensors              | Add direct inference-merge tests                            | Open   |
| SENS-007 | P2       | Sensors              | Decide the weather-sensor rainfall position                  | Open   |
| RISK-001 | P1       | Risk                 | Recalculate risk when predictions change                    | Open   |
| RISK-002 | P1       | Alerts               | Correct reference-date versus target-date display           | Open   |
| RISK-003 | P2       | Alerts               | Make alert policy and freshness handling configurable       | Open   |
| RISK-004 | P3       | Alerts               | Configure and test failed-email output                      | Open   |
| RISK-005 | P1       | Alerts               | Detect per-station ingestion and prediction staleness       | Open   |
| RISK-006 | P0       | Alerts               | Fix alert crash from Date/datetime regression               | Done   |
| RISK-007 | P2       | Risk                 | Wire up or reject rainfall-based risk for ungauged stations | Open   |
| RISK-008 | P2       | Alerts               | Prevent duplicate alert emails on repeated runs             | Open   |
| RISK-009 | P3       | Alerts               | Extend flood alerting beyond predicted river levels         | Open   |
| DB-001   | P1       | Database             | Repair non-authoritative SQL views                          | Open   |
| DB-002   | P2       | Database             | Unify bootstrap and migration behavior                      | Open   |
| DB-003   | P3       | Database             | Define referential-integrity strategy                       | Open   |
| ML-001   | P2       | ML/Operations        | Remove hard-coded production station/model choices          | Open   |
| ML-002   | P2       | ML                   | Bind preprocessing configuration to model artifacts         | Open   |
| ML-003   | P2       | ML                   | Handle incomplete/future inputs explicitly                  | Open   |
| ML-004   | P2       | ML                   | Correct the evaluation baseline horizon                     | Open   |
| ML-005   | P3       | ML                   | Add prediction uncertainty                                  | Open   |
| ML-006   | P3       | ML                   | Complete model/preprocessor abstractions                    | Open   |
| ML-007   | P2       | ML                   | Adopt cumulative and difference features beyond one station | Open   |
| ML-008   | P3       | ML                   | Add experiment and tuning tracking to the ML workflow       | Open   |
| DRGT-001 | P2       | Drought              | Reconstruct a predictive Combined Drought Index             | Open   |
| DRGT-002 | P2       | Drought              | Define staged drought alerting                              | Open   |
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

**This has produced a false flood alert in production.** During the Jowhar ingestion outage (see DATA-004), river levels
stopped on 2026-05-11 but inference continued for ten more days, because `load_inference_river_levels` passes
`fill_missing_dates=True` and the forward fill kept the 30-day window populated from a single frozen reading of 4.88 m.
The ten predictions of 1-10 June 2026 were built on 21 to 29 of 30 days fabricated, and every one over-predicted,
comparing each run against the actual reading on its target date (`date + forecast_days - 1`):

| Run date   | Target date | Predicted | Risk     | Actual | Error   |
|------------|-------------|-----------|----------|--------|---------|
| 2026-06-01 | 2026-06-07  | 4.37      | low      | 3.30   | +1.07   |
| 2026-06-05 | 2026-06-11  | 4.40      | low      | 3.00   | +1.40   |
| 2026-06-09 | 2026-06-15  | **5.43**  | **high** | 3.75   | +1.68   |
| 2026-06-10 | 2026-06-16  | 4.72      | low      | 3.78   | +0.94   |

Errors ran from +0.52 m to +1.68 m and were biased high throughout, because the frozen anchor sat above a falling river.
The 2026-06-09 run crossed Jowhar's 5.25 m high-risk threshold and was classified `high`. Jowhar did not reach 5.25 m on
any day from May to September 2026; monthly maxima were 4.98, 3.88, 3.15, 4.20 and 4.10. Actual readings for the
comparison come from `public.station_river_data`, corroborated against SWALIM `/rivers/graph` with zero value
disagreements across 104 overlapping dates.

The degradation was undetectable from inside `infer()`: the gaps are filled by the loader before the completeness check
at `api.py` runs, so that check saw a full window. Forward filling therefore does not merely reduce accuracy, it can
manufacture a flood warning that no observation supports. A maximum-gap rule that fails instead of filling past N
missing days would have prevented all ten predictions.

**Done when:**

- [ ] A per-source policy defines reject, interpolate, forward-fill, zero-fill, and maximum-gap rules.
- [ ] A maximum consecutive-gap limit exists for river levels, above which inference fails rather than fills, so a
      frozen anchor cannot drive a risk classification.
- [ ] Predictions record how much of their input window was imputed, so a degraded forecast is identifiable after the
      fact rather than only reconstructable from the gaps.
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

### DATA-004 — Replace positional SWALIM scraping with per-station fetches

- **Priority:** P1 (raised from P2 on 2026-09-22: this is no longer hypothetical, see below)
- **Status:** Open
- **Issue/PR:** —

**Problem:** Latest-level ingestion depends on the first seven HTML rows; chart history derives an endpoint by string
replacement and skips leap-day conversion failures. Upstream format changes can silently reduce coverage.

**Direction, decided 2026-09-24:** rather than making positional scraping trustworthy, remove the dependency on
position. The per-station chart endpoint becomes the primary daily source, and the HTML levels page is demoted to
inventory discovery. This resolves the source question that was previously left open at the end of this item. The
rationale is that the chart endpoint is addressed by explicit `station_id`, its response self-identifies, and it returns
full history on every call — so it is both immune to the failure that caused this incident and self-healing for gaps,
which is what DATA-009 depends on.

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
- The chart endpoint URL is derived by string replacement, `swalim_api_url.replace("/levels", "/graph")`, with a
  standing `FIXME`.
- `fetch_river_data_from_chart_api()` takes its station id from static metadata via
  `get_river_station_metadata(config, station_name).id`, while `river_station_metadata.swalim_internal_id` holds the
  same mapping in the database. Which is authoritative is unresolved — see DATA-006.
- Cost of the swap is 7 POSTs per day in place of 1 GET, against a pipeline that already queries Open-Meteo per forecast
  location and runs 5 inferences. The limiting factor is write behaviour, not request volume — see DATA-005.

**Done when:**

- [ ] The daily river ingestion fetches per station by explicit `station_id` and verifies that the returned
      `otherDetails.stationName` matches the requested station before anything is stored; `head(7)` and row-position
      matching are removed.
- [ ] Endpoint URLs are explicit configuration rather than string replacement, retiring the `FIXME`.
- [ ] The station-id mapping has one authoritative source, consistent with the DATA-006 decision.
- [ ] The HTML levels page is retained only as an inventory-discovery check: it reports stations that are new (such as
      `Deefow`), renamed, or no longer listed, and never feeds stored readings.
- [ ] A station present in the configured inventory but absent from the upstream response logs an actionable warning
      and is reflected in the command's exit status.
- [ ] Fetch failures and malformed responses produce actionable logs and non-success exit status where appropriate.
- [ ] Leap years and missing `previous_year`/`gaugeReadingList` structures are handled safely.
- [ ] A null `readingValue` is recorded as "no reading upstream" rather than as a fetch failure or a gap; see DATA-010.
- [ ] Repeated daily runs are idempotent, which requires DATA-005.
- [ ] The flood thresholds returned in the chart response (`indicator.moderateRiskLevelVal`, `highRiskLevelVal`,
      `bankFullVal`) are compared against stored station metadata and divergence is reported; see DATA-006.
- [ ] Fixture tests cover a station-name mismatch, an empty `gaugeReadingList`, a missing `previous_year`, null
      readings, malformed JSON, leap day, and — for the retained discovery check — an eight-row HTML table with a new
      station inserted above `Jowhar`.
- [ ] `docs/components/data-ingestion.md` describes the new source precedence and the HTML page's reduced role.

**Related:** DATA-005 (prerequisite for idempotent daily writes; `Done` as at 2026-09-30), DATA-006 (station identity and
thresholds), DATA-009
(consumes the chart endpoint as its repair source), DATA-010 (null-reading semantics), RISK-005 (detection and
alerting).

### DATA-005 — Enforce historical river-level uniqueness

- **Priority:** P1 (raised from P2 on 2026-09-24: duplicates are now measured, and this blocks DATA-009)
- **Status:** Done (2026-09-30, branch `fix/data-005-river-level-uniqueness`)
- **Issue/PR:** —

**Problem:** `historical_river_level` has no database uniqueness constraint; duplicate prevention is
application-specific and direct writes can create conflicting feature rows. Beyond the integrity risk, this is the
structural blocker for running gap repair as part of the daily pipeline: without a constraint there is no safe
`ON CONFLICT` target, so every write path has to pre-check row by row.

**Evidence:**

- `sql/database_bootstrap.sql` declares `historical_river_level(id, location_name, date, level_m)` with no unique
  constraint on `(location_name, date)`, unlike `historical_weather` and `forecast_weather`, which both have one.
- **Measured, not hypothetical:** the 2026-09-22 production snapshot contains **962 duplicate `(location_name, date)`
  pairs**, i.e. 962 rows beyond one-per-station-per-day.
- `insert_river_data()` in `src/flood_forecaster/data_ingestion/swalim/river_level_api.py` delegates to
  `__filter_river_data_exists()`, which issues **one `SELECT` per candidate row** and then `session.add_all()`. That is
  an N+1 read-modify-write with no database-level guard, so concurrent or repeated runs can still duplicate.
- The same function logs a warning when a stored level differs from the fetched one but never updates the row, so a
  corrected upstream reading is silently discarded.
- Any consumer that estimates coverage as `COUNT(*)` rather than `COUNT(DISTINCT date)` over-reports and can conclude a
  station is complete when it is not. This is the failure mode that makes duplicate rows actively dangerous rather than
  merely untidy.
- `docs/flood-forecaster-datamodel.md` and the defensive deduplication in `load_river_level_db()` document the current
  application-level workaround.

**Done when:**

- [x] Existing duplicates are audited and resolved with an explicit retention rule (962 pairs as at 2026-09-22).
      `scripts/maintenance/remove_duplicate_historical_river_level.py` keeps a non-NULL `level_m` over a NULL one, then
      the highest `id`. Verified on a copy of the snapshot: exactly 962 rows deleted, all 88,320 distinct station-days
      preserved.
- [x] A migration adds an appropriate station/date uniqueness constraint, following the pattern already used in
      `sql/add_historical_weather_unique_constraint.sql`.
      `sql/add_historical_river_level_unique_constraint.sql` adds `uq_historical_river_level_location_date`; it refuses
      to run while duplicates remain and is idempotent. The constraint is also declared on the SQLAlchemy model and in
      `sql/database_bootstrap.sql`, so a fresh install gets it without the migration.
      **Deployment order is not free:** `ON CONFLICT (location_name, date)` needs a matching unique index, so the new
      code fails outright ("there is no unique or exclusion constraint matching the ON CONFLICT specification") against a
      database without the constraint. The constraint must therefore be applied *before* the code ships, which the
      previously deployed code tolerates. Since the Python cleanup ships with that code,
      `sql/deduplicate_historical_river_level.sql` provides a psql-only equivalent so the database can be prepared ahead
      of the deployment. Both directions were verified against a copy of the snapshot.
- [x] Every ingestion/backfill path uses conflict-safe bulk inserts or upserts; the per-row `SELECT` pre-check in
      `__filter_river_data_exists()` is removed.
      `insert_river_data()` is a single `ON CONFLICT (location_name, date) DO UPDATE`. Batches are collapsed to one row
      per station-day first, because one statement cannot touch the same conflict target twice; the collapse keeps the
      latest *available* measurement, so a NULL cannot displace a reading seen earlier in the same batch (raised in PR
      review; plain last-wins destroyed valid data before it reached the database and defeated the NULL guard in the
      upsert).
      `scripts/backfill/fill_river_data_gaps.py` now fills a NULL placeholder in place instead of inserting a second row
      for the date, which the constraint would have rejected.
- [x] A decision is recorded on whether a differing upstream value should update the stored row or be rejected, rather
      than being warned about and dropped.
      **Decided: update.** All nine value-conflicting pairs were arbitrated against `public.station_river_data` and the
      more recently ingested value was correct in 9/9, three of them correcting a whole-metre transcription error. One
      exception: a NULL incoming level never overwrites a stored reading, since that would manufacture a gap (DATA-010).
- [x] Coverage and gap calculations count distinct dates, not rows.
      `get_existing_range()` in `scripts/backfill/fill_river_data_gaps.py` and the per-location query in
      `scripts/diagnostics/check_river_data_availability.py` both use `COUNT(DISTINCT date)`.
- [x] Database integration tests cover duplicate attempts, repeated ingestion of the same window, and migration of
      existing data.
      `src/tests/integration/test_river_level_api.py` covers constraint presence, in-batch duplicates, repeated
      ingestion, in-place update, NULL non-overwrite, and rejection of a raw duplicate `INSERT`.
      `src/tests/unit/test_river_level_upsert.py` covers the same write path plus date-representation normalization on
      SQLite. Migration of existing data was rehearsed end to end against a copy of the 2026-09-22 snapshot: the
      migration refuses while duplicates exist, applies once they are gone, and is idempotent on re-run.

**Unblocks:** DATA-009 (daily per-station repair is now cheap and safe: there is a stable `ON CONFLICT` target, and
coverage can be measured in distinct dates).

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

### DATA-009 — Guarantee a complete lag window per station

- **Priority:** P1
- **Status:** Open
- **Issue/PR:** —

**Problem:** The pipeline treats river ingestion as "did the fetch return anything", but inference needs something
stricter: a **complete trailing window per station**. `river_station_lag_days = [1, 3, 7, 14, 30]` means every
prediction consumes the level at t-1, t-3, t-7, t-14 and t-30, so one missing day degrades five separate future
predictions, and a station stops producing predictions once its last reading ages past 30 days. Nothing in the pipeline
checks this, and nothing repairs it; gap filling exists only as a manual script run by a human who already suspects a
problem.

**Note on urgency:** `exclude_today_river_level = true`, so same-day freshness is explicitly *not* required. The
requirement is window completeness, not latency, which means repair can run immediately after ingestion within the same
daily job.

**Evidence:**

- `river_station_lag_days` and `exclude_today_river_level` in `config/config.ini` under `[model]`.
- The Jowhar timeline in DATA-004 matches the lag window exactly: ingestion stopped 2026-05-12, predictions stopped 30
  days later when the last reading left the t-30 slot.
- `scripts/amadeus_saadaal_flood_forecaster_resilient.sh` gates the run on forecast *weather* freshness
  (`check_forecast_freshness`, requiring today+5) but has no equivalent check for river levels, and its ingestion step
  reports success as long as the command exits 0.
- Three sources exist with different costs, and only the first is used daily: the HTML page (1 GET), the chart endpoint
  (1 POST per station, full history), and `public.station_river_data` (SQL in the same database, no network). The last
  two are reachable only from `scripts/backfill/fill_river_data_gaps.py`.
- Any repair driven by an aggregate signal is insufficient: on the Jowhar pattern six of seven stations still ingest
  normally, so totals look healthy. Window completeness has to be evaluated per station against the configured
  production list.
- A repair window bounded by `MAX(stored date)` cannot see a trailing gap, which is the bound
  `scripts/backfill/fill_river_data_gaps.py` deliberately removed in commit `d242f44`.

**Done when:**

- [ ] The configured production station list is the reference for which stations must have a complete window.
- [ ] After ingestion and before inference, the pipeline verifies per station that every date in the lag window is
      present with a non-null level.
- [ ] A station with an incomplete window triggers repair from the cheapest available source, in a documented precedence
      (`public.station_river_data`, then the chart endpoint), until the window is complete or the sources are exhausted.
- [ ] The repair window runs to the current date, never to `MAX(stored date)`.
- [ ] The daily repair is bounded to the lag window; unbounded full-history backfill stays in the manual tool.
- [ ] Dates that no source can supply are reported per station and named, and reaching inference with an incomplete
      window is a distinct, visible outcome rather than a silently degraded prediction; see RISK-005 and OPS-001.
- [ ] Repair is idempotent and does not re-request dates already known to be unavailable upstream; see DATA-005 and
      DATA-010.
- [ ] Tests cover a complete window, a single interior hole, a trailing hole, a station absent from every source, and
      one station incomplete while the others are healthy.
- [ ] `docs/components/data-ingestion.md` and `docs/components/scheduling-and-deployment.md` describe the completeness
      precondition and the repair cascade.

**Related:** DATA-005 (was blocking this; `Done` as at 2026-09-30, so the `ON CONFLICT` target and distinct-date coverage
this item needs now exist), DATA-004 (root cause of the motivating outage, and the source this item repairs
from), RISK-005 (detection and alerting; this item is the repair counterpart), ML-003 (inference behaviour on incomplete
inputs).

### DATA-010 — Separate absent upstream readings from fetch failures

- **Priority:** P3
- **Status:** Open
- **Issue/PR:** —

**Problem:** A date with no reading upstream is indistinguishable from a date the pipeline failed to retrieve. Both
appear as an absent row, and `level_m IS NULL` rows are deliberately treated as absent by the gap logic. A daily repair
loop therefore re-requests the same permanently unavailable dates forever, and the accumulating tail is the one place
where routine repair does waste real work.

**Evidence:**

- `get_existing_dates()` in `scripts/backfill/fill_river_data_gaps.py` excludes `level_m IS NULL` rows, with a comment explaining
  that the loader drops null levels, so such a row occupies a date without being usable.
- The SWALIM chart response can carry a null `readingValue` for dates that have not been entered by a gauge reader;
  `scripts/backfill_river_data_from_swalim.py` documents this as a known limitation with no resolution.
- Nothing records that a specific station/date was checked and found genuinely empty upstream, so no repair pass can
  learn from a previous one.

**Done when:**

- [ ] A representation distinguishes "no reading exists upstream", "not yet retrieved", and "retrieval failed".
- [ ] Repair passes skip dates known to be unavailable, with a bounded re-check policy for late upstream entry.
- [ ] Missing-data metrics separate upstream absence from pipeline failure, so operational alerting is not triggered by
      gaps nobody can fix.
- [ ] The chosen representation is consistent with the DATA-002 missing-data policy.
- [ ] Tests cover a late-arriving upstream reading, a permanently absent date, and a transient fetch failure.

**Related:** DATA-002 (missing-data policy), DATA-009 (consumer of this distinction), DATA-004 (where null readings
enter).

### DATA-011 — Decide the rainfall source strategy

- **Priority:** P2
- **Status:** Open
- **Issue/PR:** —

**Problem:** Rainfall is the primary driver of both flood and drought signals, and the pipeline takes it from one source
(Open-Meteo) that was never selected against measured alternatives. The June 2026 studies measured three candidates and
found that they win on **different questions**, so there is no single best source and the choice has to be made
deliberately per use: amount accuracy for modelling, occurrence accuracy for alerting.

**Evidence** (full detail in [studies/2026-06-improvement-studies.md](studies/2026-06-improvement-studies.md)):

- Against local sensors, Open-Meteo hourly rainfall correlates about 0.10, with point mismatches such as 0.0 mm reported
  against a sensor reading near 16 mm. Aggregated to daily totals, correlation rises to about 0.5.
- Rainfall **amount** correlation at Baidoa: Open-Meteo 0.50, ClimateSERV 0.45. At Afgooye both fail — 0.00 and 0.01.
- Rain **occurrence** accuracy (> 0.1 mm): ClimateSERV 0.76 against Open-Meteo 0.66 at Baidoa, and 0.85 against 0.48 at
  Afgooye. ClimateSERV is the better occurrence detector at both stations.
- ClimateSERV (CHIRPS) is reachable by API; its website does not render data. ERA5 is reliable and easy for daily
  consumption but requires an account for historical series. SWALIM datasets were judged unreliable and are monthly.
- No reference to ClimateSERV, CHIRPS, ERA5, ECMWF, or Copernicus exists anywhere in the repository, on any branch, as
  at 2026-09-28.

**Done when:**

- [ ] A recorded decision states which source supplies modelled rainfall amounts and which supplies alerting occurrence,
      including whether they may differ.
- [ ] The decision is justified against measurements on more than the two available sensor sites, or the limitation of a
      two-site sample is stated as an accepted risk.
- [ ] Daily totals, not hourly intensity, are the documented modelling unit, or a justification is recorded for keeping
      hourly inputs.
- [ ] The ECMWF account question is resolved with a named owner if historical ERA5 is in scope.
- [ ] `docs/components/data-ingestion.md` states the chosen sources and their roles.

**Related:** DATA-012 (implements whatever this decides), SENS-007 (the sensor's position in the same comparison),
DRGT-001 (consumes the rainfall and temperature choice), ML-007 (feature work that assumes daily totals).

### DATA-012 — Add the selected new sources to the ingestion pipeline

- **Priority:** P2
- **Status:** Open
- **Issue/PR:** —

**Problem:** Once DATA-011 selects a source, it has to become a real ingestion path with the same guarantees as the
existing ones. Adding a second rainfall provider touches uniqueness, missing-data policy, and provenance: without an
explicit per-source record, two providers writing the same station and date cannot be told apart or compared after the
fact.

**Evidence:**

- The pipeline's existing weather path is Open-Meteo only, with `historical_weather` and `forecast_weather` keyed by
  location and date, and a unique constraint on each.
- `use_sensor_rainfall` already coalesces a second rainfall source into the weather frame inside
  `src/flood_forecaster/ml_model/api.py`, and SENS-002 records that this merge can let a synthetic value override valid
  Open-Meteo data. A third source must not repeat that failure.
- The June 2026 session listed "add new data sources to pipeline" as a next step without specifying provenance or
  precedence.

**Done when:**

- [ ] Each stored rainfall value records which source produced it.
- [ ] Source precedence and fallback are configuration, not implicit merge order, and a missing preferred source does
      not silently substitute another without a log line.
- [ ] Ingestion for the new source is idempotent and respects the DATA-002 missing-data policy.
- [ ] Integration tests cover the new source's fetch, an upstream outage, and a disagreement between two sources for the
      same station and date.
- [ ] A comparison command or report can quantify divergence between configured sources over a date range.
- [ ] `docs/components/data-ingestion.md` and the data-model guide describe the new source and its provenance field.

**Related:** DATA-011 (decides what to add), DATA-002 (missing-data policy), DATA-005 (uniqueness pattern), SENS-002
(the merge failure mode to avoid).

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

### SENS-007 — Decide the weather-sensor rainfall position on measured value

- **Priority:** P2
- **Status:** Open
- **Issue/PR:** —

**Problem:** Weather-sensor rainfall is implemented, configurable, and — measured — does not help. The June 2026 study
replaced Open-Meteo with sensor rainfall for the Jowhar model and the error got **worse**. SENS-001 through SENS-006
treat the integration as something to make correct; this item asks the prior question of whether it should feed models at
all, because continuing to harden a feature that degrades predictions is the more expensive mistake.

**Evidence** (full detail in [studies/2026-06-improvement-studies.md](studies/2026-06-improvement-studies.md)):

- Jowhar, XGBoost, data variant June 2025 to June 2026: MAE 0.06 **without** weather-sensor rainfall against 0.08
  **with** it.
- **The production path cannot reproduce either variant's sensor input.** `build_sensor_location_mapping()` in
  `src/flood_forecaster/utils/geo.py` assigns each sensor to its single nearest forecast location and applies
  `sensor_max_distance_km` to that pairing only. Executed against the tracked static data on 2026-09-28:
  `BAIDOA_MOH` → `bay__baydhaba` (17.4 km), `MOHADM_AFG` → `lower_shabelle__afgooye` (16.3 km),
  `MOH_EBW1` → `bakool__ceel_barde` (36.6 km). All three are inside the 50 km gate, and none of the three locations
  appears in any station's `weather_locations` in `data/static/station-mapping.json`.
- For a Jowhar inference, `load_sensor_rainfall_db()` therefore computes an empty `relevant_station_ids`, logs
  `No sensor stations found within 50.0 km of locations […]`, and returns an empty frame; the coalesce in
  `ml_model/api.py` is skipped and the model runs on unmodified Open-Meteo data. The measured comparison came from a
  notebook that attached Afgooye rainfall to Jowhar manually, so adopting it requires changing the mapping rule, not
  enabling a flag.
- `MOHADM_AFG` is 83.5 km from `middle_shabelle__jowhar` and `BAIDOA_MOH` is 212.2 km from it, but neither pairing is
  ever constructed by the nearest-neighbour rule, so distance is not the operative blocker.
- Jowhar river levels respond largely to **upstream** rainfall, so a single downstream gauge is weak by construction, not
  by data quality.
- `use_sensor_rainfall = False` in `config/config.ini`, so nothing in production depends on the decision today.

**Done when:**

- [ ] A recorded decision states whether weather-sensor rainfall remains a model input, becomes validation-only
      reference data, or is retired.
- [ ] If retained as a model input, the mapping rule can actually express "sensor → a location a production station
      uses": nearest-neighbour assignment is replaced or supplemented (explicit mapping, or all locations within the
      threshold rather than only the closest), since today a sensor cannot reach a production location that is not its
      nearest. See SENS-005.
- [ ] A measured improvement is then demonstrated at that station through the production code path, not only in a
      notebook.
- [ ] If retained as reference data only, the sensor comparison command stays and the inference merge path is removed or
      disabled by design rather than by a default flag value.
- [ ] If retired, SENS-001 through SENS-006 are closed or re-scoped accordingly rather than left implying future work.
- [ ] Any upstream-rainfall alternative considered (additional upstream forecast locations, catchment aggregation) is
      recorded, since that is the direction the study points.
- [ ] `docs/sensors-quick-guide.md` states the sensor's role in one sentence that matches the decision.

**Related:** SENS-001 (coverage validation, same root finding), SENS-002 (merge safety if retained), DATA-011 (the source
comparison this decision belongs to), RISK-007 (the other consumer of sensor rainfall).

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

**Related:** RISK-008 (alerting has no dispatch record, so a stale `full` classification is re-sent on every run rather
than being caught downstream).

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
  which matches the daily template in `amadeus_saadaal_flood_forecaster_cron` — since 2026-09-28 the only cron file in
  the repository, and the only one the `Dockerfile` installs.
- `_get_new_river_levels()` emits no log line for a station that produced no row, so the ingestion gap that started the
  incident was silent at every layer.
- `flood_forecaster.predicted_river_level.created_at` is NULL on all 4694 rows, so there is no record of when any
  prediction was actually produced. The outage had to be dated from the `date` column instead. This removes the
  cheapest available forensic signal and compounds the detection gap; see also OPS-001 and DB-002.
- This is the alerting counterpart to OPS-001, which covers run-level observability; this item covers per-station data
  and prediction coverage specifically. It is also the **detection** counterpart to DATA-009, which owns per-station
  repair: detection without repair still loses a day of predictions, and repair without detection hides whatever the
  cascade could not fix.

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

### RISK-007 — Wire up or reject rainfall-based risk for ungauged stations

- **Priority:** P2
- **Status:** Open
- **Issue/PR:** PR #101 "Calculate rainfall risk assessment" (`feature/rainfall-risk-assessment` → `main`, opened
  2026-03-12, not updated since, not merged)

**Problem:** A station with no usable river gauge cannot be served by the river-level model, so it produces no
prediction, therefore no risk classification and no alert. PR #101 proposes a second, independent risk path for exactly
those stations: classify flood risk from nearby rainfall-sensor totals (24-hour and 72-hour) instead of from a predicted
river level. The capability addresses a real coverage gap and the submitted implementation is substantially complete,
but it is unreviewed, has sat unchanged for six months, and nothing in the scheduled pipeline calls the command it adds.
Merging it as-is would ship a feature that never runs in production.

**Why this matters:** Jowhar is the concrete case. DATA-004 records that its ingestion stopped on 2026-05-12 and its
predictions stopped 30 days later, undetected for four months. A rainfall-based path would have preserved some risk
signal for that station while the gauge feed was broken. RISK-005 covers *detecting* that situation; this item covers
having a fallback once it is detected.

**Evidence** (PR #101: 8 files, +373/−4):

- New `src/flood_forecaster/risk_assessment/rainfall_risk.py` providing `assess_rainfall_flood_risk()`,
  `_query_sensor_rainfall()`, `_classify_risk(rain_24h, rain_72h)`, `_load_non_functional_with_sensors()` and
  `_clean_sensor_value()`.
- New CLI command implemented in `src/flood_forecaster_cli/commands/rainfall_risk_assessment.py` and registered in
  `src/flood_forecaster_cli/main.py` as `cli.add_command(run_rainfall_risk_assessment, "rainfall-risk-assessment")`.
- Adds `map_sensors_to_non_functional_stations()` to `src/flood_forecaster/utils/geo.py`. That module already exists on
  `main` and already provides `haversine_distance()`, so this is an addition to existing code: the overlap with the
  sensor mapping introduced by PR #97 must be resolved rather than assumed absent.
- Also edits `config/config.ini`, `data/static/station-mapping.json` and `data/static/river_stations_metadata.csv`.
- Neither `amadeus_saadaal_flood_forecaster_cron` nor `scripts/amadeus_saadaal_flood_forecaster_resilient.sh` is
  touched. The scheduled pipeline's four phases (ingestion, inference, risk assessment, alerting) do not invoke the new
  command, so on merge it would be reachable only by hand.

**Done when:**

- [ ] A decision is recorded on whether rainfall-based risk is in scope. If it is not, PR #101 is closed with that
      rationale rather than left open.
- [ ] The `_classify_risk()` rainfall thresholds are justified against a documented source instead of chosen inline, and
      live in configuration alongside the river-level thresholds.
- [ ] `map_sensors_to_non_functional_stations()` is reconciled with the existing sensor mapping and
      `sensor_max_distance_km`; exactly one mapping implementation survives. See SENS-005.
- [ ] `_clean_sensor_value()` is reconciled with the existing sensor cleaning rules rather than duplicating them, and
      applies the same zero/negative/range decisions. See SENS-003.
- [ ] The station and threshold metadata this PR edits is consistent with the authoritative source chosen in DATA-006,
      and it is explicit which stations count as non-functional and who maintains that list.
- [ ] Rainfall-derived and river-level-derived classifications are distinguishable in storage, so an operator can tell
      which method produced any given risk value.
- [ ] Alert output states the basis of the risk; a rainfall-based warning is never presented as a river-level
      prediction. Date and label semantics stay with RISK-002.
- [ ] Unit tests cover threshold boundaries in both directions, a non-functional station with no mapped sensor, a mapped
      sensor with no readings, and stale readings.
- [ ] If accepted, the scheduled pipeline invokes the command as an explicit phase whose failure is visible, so the
      feature cannot merge and then silently never run — the failure mode recorded in RISK-006.
- [ ] `docs/components/risk-and-alerts.md` and `docs/components/configuration-and-cli.md` describe the second risk path,
      its configuration, and its station scope.

**Dependencies:** SENS-003 and SENS-005 (sensor value and mapping semantics this feature relies on), DATA-006 (station
metadata ownership), SENS-001 (sensor coverage validation). Proceeding without at least a recorded position on SENS-003
risks building risk classification on cleaning rules that are themselves unresolved.

### RISK-008 — Prevent duplicate alert emails on repeated runs

- **Priority:** P2
- **Status:** Open
- **Issue/PR:** —

**Problem:** Alert dispatch keeps no record of what has already been sent, so it is not idempotent. Every successful run
that finds a `full` prediction mails the contact list again. The once-daily production schedule keeps this latent, but
any repeat run on the same day re-sends: a manual `scripts/ops/trigger_forecast_now.sh`, a catch-up, a redeploy that
triggers a verification run, or any increase in cron frequency.

**Evidence** (verified 2026-09-28):

- `src/flood_forecaster/alert_module/alert.py` — `main()` runs the query, calls `deploy_alert()`, and writes nothing
  back to the database. There is no `alert_sent` or `notified_at` column on `predicted_river_level` and no
  dispatched-alerts table in `sql/database_bootstrap.sql`.
- `src/flood_forecaster/alert_module/flood_status.py` — `get_df_by_date()` filters only on `date >= latest_db_date` and
  `risk_level ILIKE 'full'`. Nothing excludes rows that were already alerted on.
- The only things that suppress a send are an empty result set and the two-day freshness gate in `main()`. Neither is a
  dedup check.
- `config/config.ini` sends to a single Mailjet contact-list address, so one send fans out to every subscriber.
- A 30-minute test schedule (`amadeus_saadaal_flood_forecaster_cron_frequent`) shipped in this repository until
  2026-09-28. It would have produced up to 48 identical flood warnings per day, and was removed on this basis.

**Done when:**

- [ ] A dispatch record identifies what has been alerted on, keyed at least on station, target date, and risk level.
- [ ] A repeat run with unchanged predictions sends nothing and says so in the log.
- [ ] A genuine change — a new station entering `full`, or a risk level that moved — still alerts.
- [ ] The intended behaviour for an ongoing multi-day event is decided explicitly: re-alert daily, or alert on change
      only.
- [ ] Delivery failures do not mark an alert as sent, so the next run retries it.
- [ ] Tests cover repeat runs, changed predictions, and a failed delivery followed by a successful retry.
- [ ] Operations documentation states that running the pipeline more than once a day is safe.

**Related:** RISK-001 (a stale `risk_level` keeps an out-of-date `full` label alive, so the two defects compound: the
duplicate send is driven by a classification that should no longer apply), RISK-003 (alert policy and freshness become
configuration, which is where a "re-alert after N hours" rule would belong), RISK-005 (per-station staleness detection
adds alert paths that must not themselves duplicate).

### RISK-009 — Extend flood alerting beyond predicted river levels

- **Priority:** P3
- **Status:** Open
- **Issue/PR:** —

**Problem:** Every alert the system can raise is derived from a predicted river level at one of five gauged stations.
Floods that do not originate from a river breakage are therefore invisible: extreme Gu-season rainfall causes large
damage far from rivers, and no signal in the pipeline can express it. The June 2026 session named this directly — the
current approach is **non-comprehensive**, and closing it properly needs a different and more complex model, not a
threshold change.

**Evidence** (full detail in [studies/2026-06-improvement-studies.md](studies/2026-06-improvement-studies.md)):

- SWALIM publishes flood-impact extents from satellite imagery. The cited example, from a Sentinel-1 image of
  2025-05-03: 3,823 ha flooded in Middle Shabelle, 3,684 ha of it agricultural — 2,365 ha in Jowhar district, 1,319 ha in
  Balcad — and about 1,300 buildings affected (Jowhar 572, Balcad 728). Impact area is expressed per district, which is
  the unit an operator acts on; a predicted level in metres is not.
- SWALIM's weekly cumulative rainfall forecast is built on NOAA-NCEP GFS and covers the whole country, including areas
  with no gauge.
- `data/static/station-mapping.json` defines five stations, all river-gauge based. `data/static/forecast-locations.csv`
  contains locations, such as `lower_shabelle__afgooye`, that no station consumes, so rainfall is already available for
  places the alert path cannot describe.
- RISK-007 (PR #101) proposes rainfall-based risk for **ungauged stations**, which is a narrower version of the same
  gap: it extends coverage to more stations but keeps stations as the unit.

**Done when:**

- [ ] A recorded decision states whether impact-area or area-based flood alerting is in scope, and whether it is an
      increment on the station model or waits for a comprehensive redesign.
- [ ] If in scope, the alert unit (district, catchment, or impact polygon) is defined along with how it relates to the
      existing station-based risk levels.
- [ ] Impact-area data licensing, cadence, and latency are confirmed to be adequate for warning rather than
      after-the-fact review, since the cited source is retrospective satellite analysis.
- [ ] An area-based warning is distinguishable in storage and in alert output from a river-level prediction, so an
      operator always knows which mechanism fired. See RISK-002 for label semantics.
- [ ] Tests cover an area alert with no corresponding station alert, and the reverse.
- [ ] `docs/components/risk-and-alerts.md` states the coverage limits of each alerting mechanism.

**Related:** RISK-007 (narrower version of the same coverage gap; settle that first), DATA-011 (rainfall occurrence
accuracy is what an area alert would rest on), DRGT-002 (the drought counterpart of the same "new alert class" question).

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

### ML-007 — Adopt cumulative and difference features beyond one station

- **Priority:** P2
- **Status:** Open
- **Issue/PR:** —

**Problem:** Preprocessing feeds the model absolute values sampled at individual lag days. The June 2026 study replaced
those with trends — cumulative rainfall over rolling windows, and river-level differences against earlier days — and
measured a 12% reduction in weighted RMSE at Jowhar. The result is promising and **unmerged**, measured at one station,
and obtained in a trial that dropped absolute lag values entirely, so it cannot be adopted as-is and it cannot currently
be reproduced from this repository.

**Evidence** (full detail in [studies/2026-06-improvement-studies.md](studies/2026-06-improvement-studies.md)):

- Presented as a `Preprocessor_002_DiffFlags` pipeline: base lag features and target, then cumulative precipitation over
  each configured window, then river-level difference features, then drop redundant raw lag columns while keeping
  `lag01` for absolute context.
- Reported outcome: −12% weighted RMSE at Jowhar, the only station analysed. The trial excluded absolute lag values, and
  the session flagged that some information may have been lost. Hyper-parameter tuning had started but was incomplete.
- `Preprocessor_002`, `DiffFlags`, and `cumsum` appear nowhere in the repository on any branch as at 2026-09-28. The
  closest pushed work is `origin/ml-enhance-feature-preprocessing` (`f9c4269`, `ad645d6`), which modifies
  `ml_model/api.py` and `ml_model/preprocess.py` and adds Jowhar XGBoost and RandomForestRegressor artefacts plus
  `src/notebooks/ml_model-Jowhar.ipynb`, but does not contain the cumulative or difference feature builders.
- `river_station_lag_days = [1, 3, 7, 14, 30]` in `config/config.ini` is the window set these features would derive
  from, and ML-002 records that lag configuration is not yet bound to model artefacts — a new preprocessor makes that
  binding more important, not less.

**Done when:**

- [ ] The feature builders exist in the repository with tests, rather than only in a notebook or a local branch.
- [ ] A variant retaining absolute lag values alongside the trend features is evaluated, so the information-loss question
      is answered rather than assumed.
- [ ] The comparison is repeated on every production station, not only Jowhar, and per-station results are recorded.
- [ ] Results are reproducible from a recorded experiment rather than from a screenshot; see ML-008.
- [ ] The new preprocessor is registered and its configuration is bound to the artefacts it produces; see ML-002.
- [ ] `docs/components/ml-pipeline.md` describes the feature set actually used in production.

**Related:** ML-002 (artefact/config binding), ML-008 (reproducibility of the comparison), DATA-011 (daily totals as the
rainfall unit these windows sum), DATA-009 (a complete lag window is a precondition for cumulative features).

### ML-008 — Add experiment and tuning tracking to the ML workflow

- **Priority:** P3
- **Status:** Open
- **Issue/PR:** —

**Problem:** Model comparisons are reported as numbers in notebooks and presentations with no durable record of the
inputs, parameters, and code version that produced them. A result such as ML-007's −12% cannot be audited, reproduced by
another person, or compared against a later attempt. MLflow and Optuna were demonstrated solving exactly this, from a
developer's local environment, and none of it is in the repository.

**Evidence** (full detail in [studies/2026-06-improvement-studies.md](studies/2026-06-improvement-studies.md)):

- MLflow runs shown for `Preprocessor_002_DiffFlags_notebook-7-Jowhar-baseline`, the same with `XGBoost_001`, and
  `Preprocessor_001-7-Jowhar-Prophet_001`, filtered on `metrics.rmse` and `params.model`.
- Optuna study `optuna_xgboost_difflags_Jowhar_f7`, 100 trials, hyper-parameter importance led by `gamma` (0.41),
  `reg_alpha` (0.24), `reg_lambda` (0.11), `subsample` (0.06).
- Neither `mlflow` nor `optuna` appears in the repository on any branch, including `pyproject.toml`, as at 2026-09-28.
- `src/flood_forecaster/ml_model/api.py` writes metrics to logs and CSV intermediates; nothing persists a run identity
  that links metrics to parameters and data range.

**Done when:**

- [ ] Training and evaluation runs record model, preprocessor, parameters, data range, station, horizon, metrics, and
      code version in one queryable store.
- [ ] The tracking store's location, retention, and whether it is developer-local or shared are decided and documented.
- [ ] Tuning runs are reproducible from a recorded study rather than from ad hoc scripts.
- [ ] Tracking is optional for scheduled inference, so a tracking outage cannot break production predictions.
- [ ] Dependencies are added to `pyproject.toml` with pinned versions, and the developer workflow is documented in
      `docs/components/ml-pipeline.md`.

**Related:** ML-007 (the comparison that needs this to be trustworthy), ML-002 (artefact metadata overlaps with run
metadata), ML-004 (baseline definition, which is only comparable once runs are recorded).

## Drought

Drought work is newer than the flood pipeline and currently lives in the `drought-prediction/` subproject, which is an
extraction of an exploratory notebook rather than a pipeline component: CSV inputs, no CLI command, no scheduled run,
no alerting path. The items below are the gap between that and an operational early-warning signal.

### DRGT-001 — Reconstruct a predictive Combined Drought Index

- **Priority:** P2
- **Status:** Open
- **Issue/PR:** —

**Problem:** SWALIM's Combined Drought Index cannot serve as an early-warning input. It is computed at the end of each
month, so it reports rather than predicts; it is published as per-district CSV tables with no API; and since 2021 it
excludes NDVI because that component produced false positives. A drought early-warning capability therefore needs its own
index, computed from selected datasets, in prediction mode.

**Evidence** (full detail in [studies/2026-06-improvement-studies.md](studies/2026-06-improvement-studies.md)):

- SWALIM CDI properties as established in the June 2026 study: monthly, retrospective, historical series since 2001 in
  per-district CSV, no API, NDVI removed since 2021.
- The session modelled drought as rainfall deficit → soil moisture deficit → vegetation stress, with candidate datasets
  per stage: rainfall forecast from Open-Meteo or CHIRPS via ClimateSERV; temperature forecast from Open-Meteo or ERA5;
  soil moisture and vegetation from ERA5 soil moisture or MODIS NDVI. No dataset was selected.
- Whether to reuse SWALIM's formula or define a new one was left open.
- What exists today, verified 2026-09-28: `drought-prediction/src/drought_prediction/predictive_analysis/cdi_forecasting.py`
  provides `forecast_weather_cdi()` (next-month CDI from monthly `BAIDOA_MOH` features `00AT`, `00RH`, `WNDW`, `RAIN`
  with a `RandomForestRegressor`) and `forecast_rainfall_cdi()` (next-month CDI from rainfall plus current CDI with a
  Huber-loss `GradientBoostingRegressor`), each on a six-month chronological holdout. Both read CSV exports in
  `drought-prediction/data/` and predict the existing SWALIM CDI rather than a reconstructed index.
- Merged through PR #107 (`feature/drought-forecast-analysis`); it has no entry point in `flood-cli` and no place in the
  scheduled pipeline.

**Done when:**

- [ ] One dataset is selected per stage of the rainfall/soil-moisture/vegetation chain, with the selection justified.
- [ ] A decision is recorded on reusing the SWALIM formula against defining a custom one, including how NDVI's
      false-positive history is handled if NDVI is used.
- [ ] The index is computed from ingested data rather than from manual CSV exports, and its inputs follow the DATA-002
      missing-data policy.
- [ ] Forecast skill is evaluated against held-out months and against a naive persistence baseline, per district rather
      than only for Baidoa.
- [ ] The district granularity and the geographic coverage are stated explicitly.
- [ ] The index has a defined refresh cadence and a documented run path, so it can produce a value before a month ends.
- [ ] A component guide describes the drought pipeline, or `drought-prediction/README.md` is promoted into the
      documentation set with the same standards.

**Related:** DATA-011 (rainfall and temperature source choice), DATA-012 (ingestion for whatever is selected),
DRGT-002 (consumes the index), ML-008 (the evaluation should be tracked like any other model work).

### DRGT-002 — Define staged drought alerting

- **Priority:** P2
- **Status:** Open
- **Issue/PR:** —

**Problem:** Drought degrades slowly, so a single severe-condition threshold warns too late to be actionable. The session
proposed alerting at graded stages, from early degradation signals and climatic drivers through to severe drought, and
offered one worked example — CDI below 0.85 and falling by 10% for two consecutive months — but no staging scheme,
thresholds, or delivery path exist.

**Evidence** (full detail in [studies/2026-06-improvement-studies.md](studies/2026-06-improvement-studies.md)):

- The June 2026 session's stated intent to "trigger alerts at different stages", with the CDI < 0.85 and −10% over two
  months example as an early-warning illustration only.
- The existing alert path is flood-specific end to end: `src/flood_forecaster/alert_module/alert.py` queries
  `PredictedRiverLevel`, `flood_status.py` filters on `risk_level ILIKE 'full'`, and delivery is a single Mailjet
  contact list configured in `config/config.ini`. There is no drought equivalent.
- Open alert defects would be inherited by any reuse of that path: RISK-003 (hard-coded risk level and freshness rule),
  RISK-008 (no dispatch record, so repeated runs re-send), RISK-002 (reference-date versus target-date labelling).
- A monthly index implies a different cadence from daily flood alerts, so freshness and duplicate-suppression rules
  cannot simply be copied.

**Done when:**

- [ ] Alert stages are defined with thresholds and the sustained-change rules that separate them, justified against
      historical CDI series rather than chosen inline.
- [ ] A decision is recorded on whether drought alerts reuse the flood alert delivery path or get their own, and on who
      receives them.
- [ ] Cadence, freshness, and duplicate-suppression rules are defined for a monthly signal, consistent with RISK-008.
- [ ] Drought alerts are distinguishable from flood alerts in storage and in delivered output.
- [ ] Tests cover entering a stage, remaining in it across consecutive periods, and recovering out of it.
- [ ] `docs/components/risk-and-alerts.md` describes the drought stages alongside the flood risk levels.

**Related:** DRGT-001 (produces the index), RISK-003 and RISK-008 (defects not to inherit), RISK-009 (the flood
counterpart of adding a new alert class).

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
