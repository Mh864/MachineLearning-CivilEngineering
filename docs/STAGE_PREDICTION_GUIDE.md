# Stage Prediction Extension

This extension adds next-day river stage prediction (regression) on top of the existing flood-threshold classification pipeline.

## What was added

- `modeling/stage_features.py`
  - Builds `data/processed/stage_features.csv` from `clean_data.csv` + NOAA weather.
  - Creates stage-specific lag and rolling features.
  - Target is `stage_next_day`.

- `modeling/stage_train.py`
  - Trains stage regression model and saves `models/stage_model.pkl`.
  - Supports:
    - `baseline` = linear regression (scaled),
    - `strong` = random forest regressor.

- `modeling/stage_evaluate.py`
  - Evaluates stage model and writes `results/stage_metrics.json`.
  - Metrics: MAE, RMSE, R2 (global and per-site test).

- `api/predict_stage.py` and `api/app.py`
  - New API endpoint: `GET /predict-stage`
  - Predicts next-day stage from last 7 stage values (+ optional discharge/weather).
  - `/health` now reports stage model availability.
  - `/latest` now includes `stage` and `stage_available`.

## How to run stage pipeline manually

From repo root:

```bash
python -m modeling.stage_features --clean-path data/processed/clean_data.csv --out-path data/processed/stage_features.csv --noaa-dir data/raw/noaa
python -m modeling.stage_train --features-path data/processed/stage_features.csv --model-out models/stage_model.pkl --model-type strong
python -m modeling.stage_evaluate --features-path data/processed/stage_features.csv --model-path models/stage_model.pkl --out-path results/stage_metrics.json
```

## Run from main pipeline

Use `--with-stage`:

```bash
python run_pipeline.py --start-date 2018-01-01 --end-date 2024-12-31 --model-type both --with-stage
```

Or in the one-command ops wrapper:

```bash
python run_ops.py --start-date 2018-01-01 --end-date 2024-12-31 --model-type both --with-stage
```

## API usage

Example call:

```text
/predict-stage?site_id=01646500&recent_stage=3.1,3.2,3.4,3.3,3.6,3.7,3.8
```

Optional inputs:

- `recent_discharge`
- `recent_prcp`
- `tmax`
- `tmin`
- `as_of_date=YYYY-MM-DD`

## Notes

- Stage model requires stage data to exist in `clean_data.csv`.
- If `models/stage_model.pkl` is missing, `/predict-stage` returns 404 with a clear message.
- Classification endpoints (`/predict`) are unchanged.
