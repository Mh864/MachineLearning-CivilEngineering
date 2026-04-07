# API Guide (FastAPI)

This document explains what FastAPI is, why it is used in this project, and how the current API works.

## What FastAPI is

FastAPI is a Python web framework for building APIs quickly with:

- automatic request parsing and validation
- automatic interactive docs (`/docs`)
- high performance (ASGI-based)
- clean Python type hints for input/output definitions

In this project, FastAPI is used to expose the trained flood-risk model as an HTTP endpoint so the frontend (or any client) can request predictions.

## Where FastAPI is used in this repository

- `api/app.py`: defines the FastAPI app and routes.
- `api/predict.py`: loads model artifact and runs prediction logic.
- `run_api.py`: helper script to launch the API from any working directory.

## Current API behavior

### App startup

When the API starts, it attempts to load the model artifact:

- file path: `models/model.pkl`
- loading function: `load_model_artifact()` in `api/predict.py`

The artifact is cached in memory (`_artifact`) so repeated requests do not reload the file each time.

### Main endpoint

- Method: `GET`
- Path: `/predict`

Query parameters:

- `site_id` (required, string)
  - USGS site identifier for traceability.
  - Current baseline model does not yet use site metadata as an input feature.
- `recent_discharge` (required, string)
  - Comma-separated discharge values ordered oldest to newest.
  - Must contain at least 7 numeric values.
- `as_of_date` (optional, string `YYYY-MM-DD`)
  - Used to generate the `month` feature.
  - If omitted, current UTC date is used.
- `recent_prcp` (optional, string)
  - Comma-separated PRCP(mm) values ordered oldest to newest.
  - If provided, must contain at least 7 numeric values.
  - If omitted, precipitation-derived inference features default to zero.
- `tmax`, `tmin` (optional, float)
  - Same-day max/min temperature inputs for weather features.
- `awnd`, `snow`, `snow_depth` (optional, float)
  - Optional same-day weather inputs for wind/snow-related features.
- `heavy_rain_threshold` (optional, float, default `20.0`)
  - Threshold used to compute `heavy_rain_flag_1d`.

Response (JSON):

- `site_id`: echoed input site id
- `prediction`: integer class (`0` or `1`)
  - `1` means higher likelihood that next-day discharge exceeds the high-flow threshold.
  - `0` means lower likelihood under current baseline.

## How request values become model features

The API converts raw query inputs into the same feature schema used during training:

- `discharge_lag1`: latest discharge
- `discharge_lag2`: second latest
- `discharge_lag3`: third latest
- `discharge_roll_mean_3`: mean of last 3
- `discharge_roll_mean_7`: mean of last 7
- `discharge_diff_1`: lag1 - lag2
- `month`: from `as_of_date` (or current UTC date)
- `prcp_lag1`, `prcp_lag2`, `prcp_lag3`
- `prcp_roll_sum_3`, `prcp_roll_sum_7`, `prcp_roll_mean_3`, `prcp_roll_mean_7`
- `heavy_rain_flag_1d`
- `tmax`, `tmin`, `tavg`, `temp_range`
- `awnd`, `snow`, `snow_depth`
- `prcp_x_discharge_lag1`
- `prcp_roll_sum_3_x_discharge_roll_mean_3`

These are assembled in `api/predict.py` and ordered using `artifact["feature_columns"]` before calling `model.predict`.

## How to run the API

From repository root:

```bash
uvicorn api.app:app --reload
```

Alternative helper:

```bash
python run_api.py
```

Default local URL:

- [http://127.0.0.1:8000](http://127.0.0.1:8000)

Interactive docs:

- [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)
- [http://127.0.0.1:8000/redoc](http://127.0.0.1:8000/redoc)

## Example calls

### Browser or curl

```text
http://127.0.0.1:8000/predict?site_id=01646500&recent_discharge=100,105,110,120,130,140,150&recent_prcp=0,0,2,5,12,18,24&tmax=24&tmin=13&as_of_date=2024-01-10
```

### curl command

```bash
curl "http://127.0.0.1:8000/predict?site_id=01646500&recent_discharge=100,105,110,120,130,140,150&recent_prcp=0,0,2,5,12,18,24&tmax=24&tmin=13&as_of_date=2024-01-10"
```

Expected style of response:

```json
{
  "site_id": "01646500",
  "prediction": 0
}
```

## Error cases to know

- If `recent_discharge` has fewer than 7 numbers, prediction logic raises an error.
- If `as_of_date` has invalid format, parsing fails.
- If `models/model.pkl` is missing or incompatible, startup/request will fail.

## Why this design is useful

- Keeps modeling code separate from web code.
- Ensures inference feature engineering matches training feature engineering.
- Makes integration simple for frontend and external clients.
- FastAPI docs allow quick manual testing without writing extra tools.

## Suggested next API improvements

- Add a `/health` endpoint for service monitoring.
- Return model probability (`predict_proba`) in addition to class label.
- Add structured error responses (`HTTPException` with clear messages).
- Add CORS middleware for frontend domains.
- Add request logging and basic rate limiting for deployment scenarios.
