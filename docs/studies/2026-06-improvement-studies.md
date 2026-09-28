# June 2026 improvement studies

This document records the studies, measurements, and improvement proposals presented at the Amadeus–Shaqodoon
Tech4Impact session of **June 2026**. It replaces the session slide deck as the durable record, so the deck does not
need to be kept or circulated to understand what was investigated, what was measured, and what was decided.

Findings are reproduced as they were presented. Statements marked **verified** were re-checked against the
repositories on 2026-09-28; where the repository state has since moved on, that is stated explicitly rather than
silently corrected.

## Scope and reading order

The session spanned three repositories. This document covers all of them in one place because the drought, data-source,
and reporting threads are only coherent together, but planning is owned per repository.

| Area                                      | Repository                 | Section                                                       |
|-------------------------------------------|----------------------------|---------------------------------------------------------------|
| Data sources, drought, ML, weather sensors | `saadaal-flood-forecaster` | [1](#1-data-source-assessment)–[6](#6-ml-perspectives)        |
| Dashboard UI                              | `saadaal-collab`           | [7](#7-dashboard-ui-cross-repository)                         |
| AI reporting                              | `saadaal-scripts`          | [8](#8-ai-reporting-cross-repository)                         |

What belongs where:

- **This file** holds the evidence: what was studied, the numbers, and the conclusions drawn from them. It is dated and
  is not rewritten as the system changes.
- **[improvement-backlog.md](../improvement-backlog.md)** holds the work: priority, status, and completion criteria for
  the items this session generated. It is the only task list.
- **[Component guides](../README.md#component-guides)** hold current behavior. A limitation an operator must know to run
  the system safely belongs there, not here.

## Items this session added to the backlog

Flood-forecaster items received stable IDs. Cross-repository items are recorded in this document only; `saadaal-collab`
and `saadaal-scripts` have no equivalent backlog, and inventing one here would create a second competing task list.

| ID              | Area    | Item                                                          | From section |
|-----------------|---------|---------------------------------------------------------------|--------------|
| [DATA-011][d11] | Data    | Decide the rainfall source strategy                           | 1, 3         |
| [DATA-012][d12] | Data    | Add the selected new sources to the ingestion pipeline        | 1            |
| [SENS-007][s07] | Sensors | Decide the weather-sensor rainfall position on measured value | 3            |
| [RISK-009][r09] | Alerts  | Extend flood alerting beyond predicted river levels           | 6            |
| [ML-007][m07]   | ML      | Adopt cumulative and difference features beyond one station   | 4            |
| [ML-008][m08]   | ML      | Add experiment and tuning tracking to the ML workflow         | 5            |
| [DRGT-001][g01] | Drought | Reconstruct a predictive Combined Drought Index               | 2            |
| [DRGT-002][g02] | Drought | Define staged drought alerting                                | 2            |

[d11]: ../improvement-backlog.md#data-011--decide-the-rainfall-source-strategy
[d12]: ../improvement-backlog.md#data-012--add-the-selected-new-sources-to-the-ingestion-pipeline
[s07]: ../improvement-backlog.md#sens-007--decide-the-weather-sensor-rainfall-position-on-measured-value
[r09]: ../improvement-backlog.md#risk-009--extend-flood-alerting-beyond-predicted-river-levels
[m07]: ../improvement-backlog.md#ml-007--adopt-cumulative-and-difference-features-beyond-one-station
[m08]: ../improvement-backlog.md#ml-008--add-experiment-and-tuning-tracking-to-the-ml-workflow
[g01]: ../improvement-backlog.md#drgt-001--reconstruct-a-predictive-combined-drought-index
[g02]: ../improvement-backlog.md#drgt-002--define-staged-drought-alerting

---

## 1. Data source assessment

*Presented by Alfredo.* Every source listed in the supplied source catalogue was reviewed; three were taken further.

| Source                   | Reliability                          | Access                                 | Caveat                                  |
|--------------------------|--------------------------------------|----------------------------------------|-----------------------------------------|
| **ECMWF ERA5**           | Reliable                             | Easy daily; account for historical     | Reanalysis, not a forecast source       |
| **SWALIM datasets**      | Not very reliable                    | Dashboard scraping, no API             | Monthly; flood-extension data may help  |
| **ClimateSERV (CHIRPS)** | Reliable, best for rainfall accuracy | Straightforward API                    | Website does not render data; API only  |

Conclusions carried forward:

- ClimateSERV is the strongest candidate for improving rainfall accuracy, and it is reachable by API, which is what the
  ingestion pipeline needs.
- ERA5 requires an account decision before historical series can be pulled; that decision was not taken in the session.
- SWALIM's flood-extension data is interesting for impact-area work (see [section 6](#6-ml-perspectives)) rather than
  for daily model inputs.

**Verified:** no reference to ClimateSERV, CHIRPS, ERA5, ECMWF, or Copernicus exists anywhere in
`saadaal-flood-forecaster`, on any branch, as at 2026-09-28. All of this remains a proposal. Rainfall input today is
Open-Meteo, optionally coalesced with sensor rainfall.

→ [DATA-011](../improvement-backlog.md#data-011--decide-the-rainfall-source-strategy),
[DATA-012](../improvement-backlog.md#data-012--add-the-selected-new-sources-to-the-ingestion-pipeline)

## 2. Study on drought

*Presented by Florencia.*

### Why SWALIM's Combined Drought Index is not sufficient

The CDI is computed monthly by SWALIM. Four properties make it unusable as an early-warning input:

- Historical data since 2001 is published as CSV tables per district.
- It is computed at the **end** of each month, so it reports rather than predicts.
- There is no API.
- Since 2021 the Normalised Vegetation Drought Index (NDVI) is no longer included in the CDI, because it produced false
  positives.

Together these argue for a custom, context-specific CDI reconstruction with explicit datasets, operating in prediction
mode.

### Proposed model of the drought process

The session modelled drought as a three-stage chain:

> rainfall deficit → soil moisture deficit → vegetation stress

Candidate datasets per stage:

| Stage                     | Candidates                                        |
|---------------------------|---------------------------------------------------|
| Rainfall forecast         | Open-Meteo, CHIRPS via ClimateSERV                |
| Temperature forecast      | Open-Meteo, ERA5 (Copernicus)                     |
| Soil moisture, vegetation | ERA5 soil moisture, or MODIS NDVI                 |

Remaining work identified in the session: select one dataset per stage, define the CDI formula (possibly reusing
SWALIM's), and trigger alerts at graded stages rather than only at severe drought. The worked example of an early stage
was: **CDI below 0.85 and falling by 10% for two consecutive months.**

### What already exists

**Verified:** the `drought-prediction/` subproject is merged into `main` (PR #107, branch
`feature/drought-forecast-analysis`). It is an extraction of the exploratory notebook, not a pipeline component:

- `forecast_weather_cdi()` predicts next-month CDI from monthly BAIDOA_MOH sensor features (`00AT`, `00RH`, `WNDW`,
  `RAIN`) with a `RandomForestRegressor`.
- `forecast_rainfall_cdi()` predicts next-month CDI from rainfall plus the current CDI value with a
  `GradientBoostingRegressor` using a Huber loss.
- Both evaluate on a six-month chronological holdout and report MAE, then refit on all pairs for the next-month
  prediction.
- Inputs are CSV exports in `drought-prediction/data/`, not database reads. There is no CLI command, no scheduled run,
  and no alerting path.

So the drought work has a credible starting point for the index, and nothing yet for the three-stage chain, the dataset
selection, or the staged alerts.

→ [DRGT-001](../improvement-backlog.md#drgt-001--reconstruct-a-predictive-combined-drought-index),
[DRGT-002](../improvement-backlog.md#drgt-002--define-staged-drought-alerting)

## 3. Weather sensor studies

Two physical weather stations were used:

| Sensor  | Label        | Latitude  | Longitude  |
|---------|--------------|-----------|------------|
| Baidoa  | `BAIDOA_MOH` | 3.1108195 | 43.6233185 |
| Afgooye | `MOHADM_AFG` | 2.140976  | 45.1085611 |

### Study 1 — is Open-Meteo reliable against local sensors for rainfall intensity?

| Aggregation           | Agreement                   | Notes                                                                    |
|-----------------------|-----------------------------|--------------------------------------------------------------------------|
| Hourly rainfall       | Correlation about **0.10**  | Point mismatches reach Open-Meteo 0.0 mm against a sensor reading ~16 mm; mean hourly error about 0.66 mm |
| Daily rainfall totals | Correlation about **0.5**   | Daily totals are more stable and less noisy                              |

**Implication drawn:** model and report on **daily rainfall totals**; do not rely on hourly rainfall intensity alone.

### Study 2 — Open-Meteo against ClimateSERV

Rainfall amount (correlation with sensor):

| Station | Source      | Correlation |
|---------|-------------|-------------|
| Baidoa  | ClimateSERV | 0.45        |
| Baidoa  | Open-Meteo  | 0.50        |
| Afgooye | ClimateSERV | 0.01        |
| Afgooye | Open-Meteo  | 0.00        |

Rain occurrence, threshold > 0.1 mm (accuracy):

| Station | Source      | Accuracy |
|---------|-------------|----------|
| Baidoa  | ClimateSERV | 0.76     |
| Baidoa  | Open-Meteo  | 0.66     |
| Afgooye | ClimateSERV | 0.85     |
| Afgooye | Open-Meteo  | 0.48     |

Conclusions:

- At Afgooye, neither source tracks sensor rainfall **amounts**; Open-Meteo is marginally better there.
- ClimateSERV is consistently better at answering **whether** it rained at a location.
- Therefore, if the priority is fewer false alarms and cleaner alerting, ClimateSERV is preferable.

This is the finding that makes the source choice a real decision rather than a preference: the two sources win on
different questions, and alerting depends on occurrence more than on amount.

### Study 3 — does sensor rainfall improve the Jowhar river-level model?

Setup: for the Jowhar point of study, replace Open-Meteo with the weather sensor; new data variant covering June 2025 to
June 2026 rainfall; best-performing model XGBoost.

| Variant                     | MAE  |
|-----------------------------|------|
| Without weather-sensor rainfall | 0.06 |
| With weather-sensor rainfall    | 0.08 |

**The sensor did not improve prediction.** Two explanations were offered, and both are geographic rather than
algorithmic:

- The closest usable sensor is about 90 km from Jowhar, so it may not represent local rainfall.
- Jowhar river levels are driven largely by **upstream** rainfall, so one nearby gauge adds little.

### Why the production path could not have produced this result

The session explained the negative result by distance. The configuration says something stronger: **the production code
cannot deliver Afgooye rainfall to the Jowhar model at any distance**, so the "with sensor" variant must have been built
outside the pipeline.

`build_sensor_location_mapping()` in `src/flood_forecaster/utils/geo.py` assigns each sensor to its **single nearest**
forecast location and then applies `sensor_max_distance_km = 50` to that one pairing. It never considers the second
nearest. Executed against the tracked static data on 2026-09-28:

| Sensor                     | Assigned forecast location | Distance | Used by a production station? |
|----------------------------|----------------------------|----------|-------------------------------|
| `BAIDOA_MOH`               | `bay__baydhaba`            | 17.4 km  | No                            |
| `MOHADM_AFG`               | `lower_shabelle__afgooye`  | 16.3 km  | No                            |
| `MOH_EBW1` (water level)   | `bakool__ceel_barde`       | 36.6 km  | No                            |

Both weather sensors therefore map **successfully** — the 50 km gate excludes nothing here. The gap is the next step:
`data/static/station-mapping.json` lists `weather_locations` for the five production stations, and none of those three
locations appears in any of them. `bay__baydhaba` is not even in the file, which is what the session meant by "Baidoa is
not associated with a nearby river station".

Consequence in code, for a Jowhar inference with `use_sensor_rainfall = True`:

1. `infer()` in `ml_model/api.py` calls `load_inference_sensor_rainfall(config, station_metadata.weather_locations, …)`
   with Jowhar's eight weather locations.
2. `load_sensor_rainfall_db()` keeps only sensors whose assigned location is in that set —
   `relevant_station_ids` is **empty**.
3. It logs `No sensor stations found within 50.0 km of locations […]` and returns an empty frame.
4. `if not sensor_df.empty` is false, so the coalesce is skipped and the model runs on unmodified Open-Meteo data.

`MOHADM_AFG` is 83.5 km from `middle_shabelle__jowhar` and `BAIDOA_MOH` is 212.2 km from it, but neither pairing is ever
constructed, so those distances are not what blocks the sensor. The deck's ~90 km is consistent with a measurement to the
Jowhar river gauge rather than to the forecast location.

This matters for how the result is read. Measured through the production path the two variants would have been
**identical**, so the 0.06 against 0.08 difference came from a notebook that attached Afgooye rainfall to Jowhar by hand.
That is a legitimate experiment — it answers "would a sensor 84 km away help?" — but it is not evidence about the
shipped integration, and adopting the sensor would require changing the mapping rule, not just flipping
`use_sensor_rainfall`. The zero-overlap condition itself is already recorded as
[SENS-001](../improvement-backlog.md#sens-001--validate-sensor-coverage-before-enablement) and stated in
[sensors-quick-guide.md](../sensors-quick-guide.md); this study is the first measurement of what closing it would buy.

→ [SENS-007](../improvement-backlog.md#sens-007--decide-the-weather-sensor-rainfall-position-on-measured-value),
[DATA-011](../improvement-backlog.md#data-011--decide-the-rainfall-source-strategy)

## 4. ML preprocessing

*Presented by Thierry.* The proposal replaces absolute values sampled at lag days with **trends**:

- Cumulative precipitation over rolling windows instead of point-in-time snapshots, for example total rain over the past
  14 days. Positive lag windows look backwards (`lag01..lagN`); negative ones look forwards
  (`forecast01..forecast{|N|+1}`). Windows deeper than one day are summed row-wise into a `_cumsum` column; a single-day
  window is kept as-is. Missing values are imputed with the row mean before summation.
- River level differences instead of levels, for example current level against the level seven days ago.

Pipeline shape presented as `Preprocessor_002_DiffFlags`: base lag features and target, then cumulative precipitation,
then river-level differences, then drop the redundant raw lag columns while keeping `lag01` for absolute context.

Result and caveats:

| Outcome                         | Value                                    |
|---------------------------------|------------------------------------------|
| Weighted RMSE change at Jowhar  | **−12%** (error decreased)               |
| Stations analysed               | 1 (Jowhar)                               |
| Absolute lag values in the trial| Excluded, so some information may be lost |
| Hyper-parameter tuning          | Started, not complete                    |

**Verified:** `Preprocessor_002`, `DiffFlags`, and `cumsum` do not appear in `saadaal-flood-forecaster` on any branch as
at 2026-09-28. The closest pushed work is `origin/ml-enhance-feature-preprocessing`
(`f9c4269` "draft ml improvements to preprocessing features and modelling", `ad645d6` "Refactor and fixes for ML
evaluation metrics"), which touches `ml_model/api.py`, `ml_model/preprocess.py`, adds XGBoost and
RandomForestRegressor artefacts for Jowhar, and adds `src/notebooks/ml_model-Jowhar.ipynb` — but not the `_cumsum` and
diff feature builders described above. The measured −12% therefore cannot currently be reproduced from this repository.

→ [ML-007](../improvement-backlog.md#ml-007--adopt-cumulative-and-difference-features-beyond-one-station)

## 5. ML infrastructure

*Presented by Thierry.* Two tools were demonstrated running against the Jowhar experiments:

- **MLflow** for experiment tracking. Runs shown included `Preprocessor_002_DiffFlags_notebook-7-Jowhar-baseline`,
  `…-XGBoost_001`, and `Preprocessor_001-7-Jowhar-Prophet_001`, filtered on `metrics.rmse` and `params.model`.
- **Optuna** for tuning: study `optuna_xgboost_difflags_Jowhar_f7`, 100 trials, with hyper-parameter importance
  dominated by `gamma` (0.41), then `reg_alpha` (0.24), `reg_lambda` (0.11), and `subsample` (0.06).

Value of this for the project is comparability: without a tracking store, results like the −12% above live in notebooks
and cannot be audited or reproduced by another person.

**Verified:** neither `mlflow` nor `optuna` appears in the repository on any branch, including
`pyproject.toml`, as at 2026-09-28. Both were demonstrated from a local developer environment.

→ [ML-008](../improvement-backlog.md#ml-008--add-experiment-and-tuning-tracking-to-the-ml-workflow)

## 6. ML perspectives

*Presented by Thierry.* Two observations that change what "flood alerting" should mean, both framed in the session as
improvements rather than a finished design.

**Impact-area data is available, and the session proposed alerting on it.** SWALIM publishes flood-impact extents
derived from satellite imagery. The example cited: from a Sentinel-1 image acquired 3 May 2025, human-induced flooding
affected 3,823 ha in Middle Shabelle, of which 3,684 ha was agricultural land — 2,365 ha within Jowhar district and
1,319 ha within Balcad. About 1,300 buildings were affected, 572 in Jowhar and 728 in Balcad.

**Not all floods come from river breakages.** Extreme Gu-season rainfall causes large damage far from rivers. The
current approach is river-gauge-centric and therefore **non-comprehensive**. Addressing this properly needs a different
and more complex approach; the session was explicit that impact-area alerting is an increment, not that solution.
Reference material: the SWALIM weekly cumulative rainfall forecast built on the NOAA-NCEP Global Forecasting System
(GFS), published at
<https://faoswalim.org/resources/site_files/Somalia_Rainfall_Forecast_07_May_2025.pdf>.

→ [RISK-009](../improvement-backlog.md#risk-009--extend-flood-alerting-beyond-predicted-river-levels)

## 7. Dashboard UI (cross-repository)

*Presented by Badr. Repository: `saadaal-collab`.*

Issues identified on the Dashboard tab:

- No visible notification system for critical indicator and flood updates.
- River-level predictions missing from the main dashboard.
- Recent sensor data not shown on the main dashboard.

Implemented during the session:

- Alert system for indicators and river flooding, with a Notifications Overview split into indicator notifications
  (filters for indicator, region, month, status) and river-flooding notifications (filters for year, ISO week, status).
- Dynamic filtering on multiple criteria.
- Predicted river levels restored to the main dashboard, as a paginated table with location, prediction run date,
  forecast days, forecasted date, predicted level, predicted risk level, and ML model name, plus CSV export.
- Recent sensor data restored, as per-sensor cards with online status, latest value, last reading time, sync action, and
  history links.

The deck flagged these as living on a branch rather than in production.

**Verified, and the state has moved on:** `saadaal-collab/main` now contains `a951bf5` "Add Alerts System on Dashboard
with filters" and the merges of PR #36 (`feat/river-levels-dashboard`), #37 (`feat/indicators-table-ui-parity`), and
#38 (`feat/recent-sensor-data-dashboard`). So the work is merged to `main` as at 2026-09-28. Whether it is deployed was
not verified here; the deck's caveat should be re-checked against the running environment, not against `main`.

## 8. AI reporting (cross-repository)

*Presented by Prince. Repository: `saadaal-scripts`.*

The change of substance: the feature is no longer a prompt update, it is a report-generation flow with guardrails. **The
AI is one part of a controlled pipeline, not the source of truth.**

```
source data → prompt → validator → renderer → delivery
(CDI, rainfall,  (month-specific  (numbers,      (HTML brief    (reports folder
 market, NDVI,    sections)        districts,      plus PDF)      and email path)
 river)                            status, claims)
```

If validation fails, the run regenerates or stops before rendering.

### What was delivered

| Output                | Detail                                                              |
|-----------------------|---------------------------------------------------------------------|
| Combined report       | One brief covering CDI, rainfall, market, NDVI, and river           |
| Export path           | HTML web view plus printable PDF; print CSS preserves layout        |
| Validation findings   | 3 on the latest regenerated April 2026 report                       |
| Model benchmark       | 5 runs per model, March 2026 repeated-run comparison                |

The April 2026 report opens with at-a-glance metrics on page one — executive signal, CDI split, and commodity price
pressure — before long-form narrative, with Normal, Alert, and Alarm segregated.

Geographic rendering moved from bubble placeholders to district-level ADM2 boundaries: 16 ADM2 districts, 3 regions
(Bakool, Bay, Lower Shabelle), from one simplified local GeoJSON derived from geoBoundaries gbOpen Somalia ADM2. This is
what lets the brief show where CDI, rainfall, market, NDVI, and river signals concentrate by district.

### What the validator checks

| Check     | Rule                                                                  |
|-----------|-----------------------------------------------------------------------|
| Numbers   | Every reported value must appear in supplied data or derived counts   |
| Districts | District and station names must exist in the provided rows            |
| Status    | Normal, Alert, and Alarm claims are checked against source rows       |
| Causality | Unsupported driver claims are flagged instead of published            |
| Sections  | Sections whose data source is unavailable are removed until it exists  |

This does not make the model factual; it stops unsupported output from becoming a published report.

### Benchmark result

March 2026, 5 runs per model, maximum 3 retries. Artefacts:
`reports/benchmarks/gpt-4.1-vs-gpt-5.4-march-2026-retries3-5x`.

| Metric              | gpt-4.1 | gpt-5.4 |
|---------------------|---------|---------|
| Success             | 100%    | 0%      |
| Completeness        | 100%    | 100%    |
| Validation failures | 1.4     | 17      |
| Latency             | 52s     | 229s    |
| Tokens              | 18k     | 41k     |

gpt-4.1 won on quality, cost, and latency. The larger model produced **complete** reports that **failed the grounding
gate**: richer prose added interpretation where the data required strict grounding, more inference produced unsupported
numbers, statuses, and causal drivers, and the retries raised latency and token spend without improving the pass rate.

For this workflow the winner is the model that stays grounded under validation, not the one that writes the best
narrative.

**Decision: ship with gpt-4.1 as the generator behind deterministic validation; test smaller models as generator
candidates, never as validators.**

### Status at the session

Ready to show: feature branch current, April and March reports generate, PDF export available, validation tests in
place, benchmark artefacts compare model behavior. Still to finish: tune validator false positives, run a smaller-model
candidate benchmark, confirm the deployment path and owner signoff.

Recommended sequence: tune validator (reduce false positives while keeping hard gates) → regression run over February,
March, and April snapshots with saved artefacts → model bake-off of gpt-4.1 against smaller candidates over 5–10 runs →
scoped PR review → handover with demo report, known limits, and deployment checklist.

**Verified:** the commits cited in the session exist and are **not** on `main` as at 2026-09-28. All five are reachable
only from `origin/feature/ai-reporting`, `origin/feat/ai-reporting-v2`, and `origin/aj_ai_reporting_v2`.

| Commit    | Date       | Subject                                                     |
|-----------|------------|-------------------------------------------------------------|
| `b779bc4` | 2026-06-03 | feat: improve combined AI report export                     |
| `2f00f0b` | 2026-06-04 | Improve AI reporting visuals                                |
| `0efef0f` | 2026-06-05 | Add grounded AI report validation                            |
| `858b19a` | 2026-06-09 | Add combined report benchmarking and March comparison report |
| `2da4bb6` | 2026-06-09 | Ignore generated outputs directory                          |

Related dashboard-side plan: `saadaal-collab/docs/combined-ai-report-view-plan.md` covers viewing `combined_ai_report`
in the dashboard.

---

## Open decisions

These were left unresolved by the session and block the items above.

| # | Decision                                                                                          | Blocks                |
|---|---------------------------------------------------------------------------------------------------|-----------------------|
| 1 | Is rainfall **occurrence** accuracy (ClimateSERV) or rainfall **amount** accuracy (Open-Meteo) the pipeline's priority? | DATA-011, DATA-012 |
| 2 | Create an ECMWF account for historical ERA5, and who owns those credentials?                       | DATA-011, DRGT-001 |
| 3 | Keep, relocate, or retire weather-sensor rainfall as a model input given the 50 km threshold?      | SENS-007              |
| 4 | Custom CDI formula: reuse SWALIM's, or define our own against the three-stage chain?               | DRGT-001           |
| 5 | Does drought alerting reuse the flood alert delivery path, or get its own?                          | DRGT-002           |
| 6 | Is impact-area flood alerting in scope, or does it wait for the comprehensive non-riverine approach? | RISK-009            |

## Agreed next steps

From the session close, presented by Florencia:

1. Review and merge the open pull requests across the repositories.
2. Deploy the new modifications.
3. Data-source deep dive, specifically testing the data precision of ECMWF.
4. Add new data sources to the pipeline.
5. ML model implementation for drought prediction.

Next session: **September 2026.**

### Open pull requests in `saadaal-flood-forecaster`, as at 2026-09-28

| PR   | Title                                                                        | Branch                             | Opened     |
|------|------------------------------------------------------------------------------|------------------------------------|------------|
| #108 | Fix river gap-filling script and required deployment variables               | `fix/rework-scripts`               | 2026-09-25 |
| #101 | Calculate rainfall risk assessment                                           | `feature/rainfall-risk-assessment` | 2026-03-12 |
| #100 | [scripts] Add script to backfill historical river level data from SWALIM chart API (draft) | `feature/historical_river_level` | 2026-03-11 |
| #99  | Backfill river data from SWALIM API (draft)                                  | `feature/ensure-data-for-inference` | 2026-03-10 |
| #98  | Fallback for River Level data ingestion from Public schema station_river_data | `main`                             | 2026-03-06 |
| #94  | devops: multi-stage Docker, CI/CD, ruff, docker-compose                       | `devops/improvements`              | 2026-03-02 |
| #69  | [DO NOT MERGE] Add Dockerfile and implement data writing functions           | `adding_writing_capability_for_csv_and_db` | 2025-09-08 |

PR #101 is already tracked as
[RISK-007](../improvement-backlog.md#risk-007--wire-up-or-reject-rainfall-based-risk-for-ungauged-stations).
Pull requests for `saadaal-collab` and `saadaal-scripts` live in a different GitHub organisation (`shaqodoon`) and were
not enumerable from this workspace; branch-level state for those repositories is recorded in sections 7 and 8.

## Participants

Alfredo, Oana-Andrea, Matthiew, Nathan, Thierry, Badr, George, Corentin, Thomas, Prince, Florencia.
