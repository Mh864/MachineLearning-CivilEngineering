# Features Guide

This document explains the engineered features used by the current baseline model, why they exist, and how they are computed.

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
- `discharge_diff_1`
- `month`
- `precip_mm_lag1`
- `precip_mm_roll_3`
- `precip_mm_roll_7`

## Input needed before feature engineering

Feature generation starts from cleaned daily gauge data (`data/processed/clean_data.csv`) with:

- `site_id`
- `date`
- `discharge`

Rows are sorted per site by date before any lag/rolling operation.

## Feature-by-feature explanation

### 1) `discharge_lag1`

- Definition: discharge value at day `t`
- What it does: gives the model the latest observed river state, which is often the strongest single predictor for near-term flow risk.
- Why it helps: flood risk tomorrow is usually correlated with how high the river is today.

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

### 7) `month`

- Definition: month extracted from `date` (`1` to `12`)
- What it does: injects coarse seasonality.
- Why it helps: high-flow behavior often follows seasonal snowmelt/rainfall cycles.

### 8) `precip_mm_lag1`

- Definition: precipitation (mm) from previous day (`precip_mm.shift(1)`).
- What it does: adds immediate rainfall forcing before prediction day.
- Why it helps: recent rain is a direct driver of runoff and rising discharge.

### 9) `precip_mm_roll_3`

- Definition: rolling 3-day precipitation sum (`rolling(3, min_periods=1).sum()`).
- What it does: captures short accumulation of rainfall over recent days.
- Why it helps: flood response often depends on cumulative rain, not one-day rain alone.

### 10) `precip_mm_roll_7`

- Definition: rolling 7-day precipitation sum (`rolling(7, min_periods=1).sum()`).
- What it does: captures longer wetness accumulation and catchment saturation proxy.
- Why it helps: sustained wet periods increase runoff efficiency and flood likelihood.

## Target definition used with features

The model predicts whether the **next day** is above a site-specific high-flow threshold.

Per site:

1. Compute `threshold` = percentile of historical discharge (default `0.9`).
2. Compute `discharge_next_day` by shifting discharge by `-1`.
3. Set `target = 1` if `discharge_next_day > threshold`, else `0`.

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

- NOAA precipitation is included, but no temperature/wind/humidity/snow features yet.
- No static watershed characteristics.
- No multi-site upstream/downstream relationship features.
- Month as integer is a coarse seasonal proxy.

## Training vs API feature consistency

Consistency is maintained by:

- saving `feature_columns` inside `models/model.pkl`
- reconstructing identical feature names/order in `api/predict.py`
- selecting columns at inference as `X = X[feature_cols]`

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
- `month = from as_of_date or current UTC date`
- `precip_mm_lag1 = yesterday precipitation`
- `precip_mm_roll_3 = precipitation sum over last 3 days`
- `precip_mm_roll_7 = precipitation sum over last 7 days`

## Future feature improvements

Recommended next additions:

- precipitation and temperature features (NOAA integration)
- rolling max/min and volatility indicators
- site metadata (basin area, elevation, land cover)
- cyclic month encoding (`sin/cos`) instead of raw integer month
- event-based labels from flood occurrence datasets
