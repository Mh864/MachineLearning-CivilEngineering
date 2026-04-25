# Features Guide

This document explains the engineered features used by the current models, why they exist, and how they are computed.

## Where features are defined

- Feature engineering code: `modeling/features.py`
- Inference reconstruction code: `api/predict.py`
- Feature list used by training/inference artifact: `FEATURE_COLUMNS` in `modeling/features.py`

Current feature columns:

- `discharge_lag1`
- `discharge_lag2`
- `discharge_lag3`
- `discharge_roll_mean_3`
- `discharge_roll_mean_7`
- `discharge_roll_std_3`
- `discharge_roll_std_7`
- `discharge_roll_max_3`
- `discharge_roll_max_7`
- `discharge_diff_1`
- `month_sin`
- `month_cos`
- `prcp_lag1`
- `prcp_lag2`
- `prcp_lag3`
- `prcp_roll_sum_3`
- `prcp_roll_sum_7`
- `prcp_roll_mean_3`
- `prcp_roll_mean_7`
- `heavy_rain_flag_1d`
- `days_since_last_heavy_rain`
- `tmax`
- `tmin`
- `tavg`
- `temp_range`
- `awnd`
- `snow`
- `snow_depth`
- `prcp_x_discharge_lag1`
- `prcp_roll_sum_3_x_discharge_roll_mean_3`

## Input needed before feature engineering

Feature generation starts from cleaned daily gauge data (`data/processed/clean_data.csv`) with:

- `site_id`
- `date`
- `discharge`

Then NOAA daily weather data from `data/raw/noaa` is merged by `site_id` + `date` when available.

Rows are sorted per site by date before any lag/rolling operation.

### Join choice and missing weather

- For each USGS site, weather rows are selected from the merged NOAA table for that `site_id` and merged onto the local daily discharge timeline with a **`left` join on `date`** (discharge timeline is authoritative).
- If no NOAA row exists for a given day, precipitation and temperature fields are missing until filled.
- **Post-merge fills** (in `_add_features_per_site`): `prcp`, `tmax`, `tmin`, `awnd`, `snow`, and snow depth (`snwd` → `snow_depth`) missing values are replaced with **`0.0`** so every training row has numeric inputs. This matches the API behavior when optional weather arrays are omitted (inference defaults to zeros for same-day weather scalars derived from the last day of the window).
- Duplicate `(site_id, date)` rows in merged NOAA input are **deduplicated** in `load_noaa_weather` (`keep="last"`).

## Feature-by-feature explanation

### 1) `discharge_lag1`

- Definition: **previous-day** discharge (`discharge.shift(1)` at calendar row `t`), i.e. discharge observed at **`t-1`**, not same-day `t`.
- What it does: gives the model the most recent **prior** river state used for predicting **next-day** exceedance.
- Why it helps: aligns with the binary target on `t+1` without leaking same-day discharge at `t` into the label.

### 2) `discharge_lag2`

- Definition: discharge value at day `t-1`
- What it does: adds one extra day of memory so the model can compare recent levels.
- Why it helps: distinguishes stable high flow from sudden spikes or drops.

### 3) `discharge_lag3`

- Definition: discharge value at day `t-2`
- What it does: extends short-term history to three recent points.
- Why it helps: helps capture persistence and multi-day buildup patterns.

### 4) `discharge_roll_mean_3`

- Definition: mean discharge over last 3 days (`t-2` to `t`)
- What it does: smooths day-to-day noise in raw discharge.
- Why it helps: reduces sensitivity to one-day anomalies and reflects a local trend level.

### 5) `discharge_roll_mean_7`

- Definition: mean discharge over last 7 days (`t-6` to `t`)
- What it does: captures broader week-scale river regime.
- Why it helps: gives context on whether current flow is high relative to recent baseline.

### 6) `discharge_diff_1`

- Definition: `discharge_lag1 - discharge_lag2`
- What it does: estimates first-order daily change (rise/fall speed).
- Why it helps: a rapidly rising river can indicate elevated next-day exceedance risk.

### 7) `month_sin`, `month_cos`

- Definition: cyclic encoding of month (`sin(2πm/12)`, `cos(2πm/12)`).
- What it does: injects seasonality without artificial jump between December and January.
- Why it helps: smoother seasonal learning than raw integer month.

### 8) `prcp_lag1`

- Definition: precipitation (mm) from previous day (`prcp.shift(1)`).
- What it does: adds immediate rainfall forcing before prediction day.
- Why it helps: recent rain is a direct driver of runoff and rising discharge.

### 9) `prcp_lag2`

- Definition: precipitation (mm) from two days ago (`prcp.shift(2)`).
- What it does: extends short rainfall memory.
- Why it helps: delayed basin response can make earlier rain still relevant.

### 10) `prcp_lag3`

- Definition: precipitation (mm) from three days ago (`prcp.shift(3)`).
- What it does: provides additional short-window rainfall history.
- Why it helps: catchment/storage effects may respond over multiple days.

### 11) `prcp_roll_sum_3`

- Definition: rolling 3-day precipitation sum (`rolling(3, min_periods=1).sum()`).
- What it does: captures near-term accumulated rainfall.
- Why it helps: flood response often depends on cumulative rain, not just a single day.

### 12) `prcp_roll_sum_7`

- Definition: rolling 7-day precipitation sum (`rolling(7, min_periods=1).sum()`).
- What it does: tracks week-scale wetness accumulation.
- Why it helps: sustained wet periods increase runoff efficiency and flood likelihood.

### 13) `prcp_roll_mean_3`

- Definition: rolling 3-day precipitation mean (`rolling(3, min_periods=1).mean()`).
- What it does: smooths short precipitation variability.
- Why it helps: helps separate persistent moderate rain from isolated spikes.

### 14) `prcp_roll_mean_7`

- Definition: rolling 7-day precipitation mean (`rolling(7, min_periods=1).mean()`).
- What it does: smooths broader precipitation regime over a week.
- Why it helps: captures overall wet/dry context around the forecast date.

### 15) `heavy_rain_flag_1d`

- Definition: binary flag where `1` if `prcp > heavy_rain_threshold`, else `0`.
- What it does: creates an event-style extreme rain indicator.
- Why it helps: heavy rainfall events can trigger abrupt flood-risk jumps.

### 16) `days_since_last_heavy_rain`

- Definition: days elapsed since most recent day where `prcp > heavy_rain_threshold` (per site, chronological).
- What it does: captures recency of extreme rainfall events.
- Why it helps: basin response often decays gradually after heavy rain.

### 16) `tmax`

- Definition: same-day maximum temperature (NOAA `TMAX`, numeric).
- What it does: adds thermal forcing context.
- Why it helps: warm conditions can influence snowmelt/runoff patterns.

### 17) `tmin`

- Definition: same-day minimum temperature (NOAA `TMIN`, numeric).
- What it does: adds nighttime cooling context.
- Why it helps: helps characterize freeze-thaw conditions and hydrologic state.

### 18) `tavg`

- Definition: `(tmax + tmin) / 2`.
- What it does: daily mean temperature proxy.
- Why it helps: useful compact signal for weather regime and snowmelt tendency.

### 19) `temp_range`

- Definition: `tmax - tmin`.
- What it does: intraday temperature variability.
- Why it helps: can reflect atmospheric instability and thermal transitions.

### 20) `awnd`

- Definition: average wind speed (NOAA `AWND`, numeric; fallback `0` if unavailable).
- What it does: adds additional weather forcing context.
- Why it helps: may correlate with storm-system intensity and evapotranspiration effects.

### 21) `snow`

- Definition: snowfall amount (NOAA `SNOW`, numeric; fallback `0` if unavailable).
- What it does: captures frozen precipitation input.
- Why it helps: snow accumulation can delay runoff and shift flood timing.

### 22) `snow_depth`

- Definition: snow depth (NOAA `SNWD`, numeric; fallback `0` if unavailable).
- What it does: proxy for stored water in snowpack.
- Why it helps: snowpack status affects melt-driven discharge risk.

### 23) `prcp_x_discharge_lag1`

- Definition: interaction term `prcp * discharge_lag1`.
- What it does: combines current rainfall with current river state.
- Why it helps: the same rain can have very different impact at low vs already-high flow.

### 24) `prcp_roll_sum_3_x_discharge_roll_mean_3`

- Definition: interaction term `prcp_roll_sum_3 * discharge_roll_mean_3`.
- What it does: combines recent cumulative rain with recent average discharge.
- Why it helps: captures compounding effects between wet catchment and elevated baseflow.

## Target definitions used with features

The dataset contains both binary and multiclass next-day targets.

Per site:

1. Compute per-site thresholds:
   - `threshold_medium` = p75 discharge
   - `threshold_high` = p90 discharge
   - `threshold` (compatibility binary) = p90 discharge
2. Compute `discharge_next_day` by shifting discharge by `-1`.
3. Set:
   - `target` (binary) = `1` if `discharge_next_day > threshold`, else `0`
   - `target_multiclass`:
     - `0` if `<= threshold_medium`
     - `1` if `threshold_medium < x <= threshold_high`
     - `2` if `> threshold_high`

Rows without enough history (lags/rolling) or missing next day are dropped.

## Time alignment intuition

At a conceptual prediction time `t`:

- Input features come from values available up to day `t`.
- Target represents day `t+1` crossing behavior.

This avoids direct leakage from future values into feature columns.

## Why these features are a good baseline

- They are simple, interpretable, and easy to debug.
- They use only routinely available gauge measurements.
- They model both absolute flow level and short-term dynamics.

## Limitations of current feature set

- NOAA weather is now included (precipitation, temperature, optional wind/snow), but humidity/pressure/radiation are still missing.
- No static watershed characteristics.
- No multi-site upstream/downstream relationship features.
- No upstream network topology features are included yet.

## Training vs API feature consistency

Consistency is maintained by:

- saving `feature_columns` inside model artifacts (`models/model.pkl`, `models/lgbm_model.pkl`)
- selecting inference columns by artifact order (`X = X[feature_cols]`) in model evaluation/inference paths
- allowing optional weather inputs in API inference (`recent_prcp`, `tmax`, `tmin`, `awnd`, `snow`, `snow_depth`) with safe defaults

This reduces risk of train/serve schema mismatch.

## Example feature row (illustrative)

Given recent discharge values (oldest -> newest):

`[100, 105, 110, 120, 130, 140, 150]`

Computed features:

- `discharge_lag1 = 150`
- `discharge_lag2 = 140`
- `discharge_lag3 = 130`
- `discharge_roll_mean_3 = (130+140+150)/3 = 140`
- `discharge_roll_mean_7 = (100+105+110+120+130+140+150)/7 = 122.14...`
- `discharge_diff_1 = 150 - 140 = 10`
- `month_sin/month_cos = from as_of_date or current UTC date`
- `prcp_lag1 = yesterday precipitation`
- `prcp_roll_sum_3 = precipitation sum over last 3 days`
- `prcp_roll_sum_7 = precipitation sum over last 7 days`
- `heavy_rain_flag_1d = 1 if prcp > threshold else 0`
- `tavg = (tmax + tmin)/2`
- `prcp_x_discharge_lag1 = prcp * discharge_lag1`

## NOAA availability and graceful fallback

- If NOAA files are missing for a site/date, weather inputs are safely defaulted (typically `0.0` for numeric weather fields).
- The pipeline prints:
  - which NOAA-derived features were generated
  - which source NOAA columns were unavailable (`PRCP`, `TMAX`, `TMIN`, `AWND`, `SNOW`, `SNWD`)
- This keeps feature generation robust while still surfacing missing-weather gaps.

## Future feature improvements

Recommended next additions:

- humidity, pressure, and radiation weather signals
- rolling max/min and volatility indicators
- site metadata (basin area, elevation, land cover)
- cyclic month encoding (`sin/cos`) instead of raw integer month
- event-based labels from flood occurrence datasets
