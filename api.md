# API Guide (FastAPI)

The API exposes the trained classifier, optional stage-regression model, and supporting data endpoints. CORS is enabled for local development (`allow_origins=["*"]`).

## Run

```bash
uvicorn api.app:app --reload
# or
python run_api.py
```

- Swagger: [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)
- ReDoc: [http://127.0.0.1:8000/redoc](http://127.0.0.1:8000/redoc)

## Model loading order

On startup the app loads the first artifact that exists:

1. `models/lgbm_model.pkl`
2. `models/model.pkl` (logistic **Pipeline**)

The chosen path is reported by **`GET /health`**.
If `models/stage_model.pkl` exists, stage artifact status is also reported.

## `GET /health`

Lightweight **liveness/readiness** response for monitoring:

```json
{
  "status": "ok",
  "model_loaded": true,
  "artifact_path": "models/lgbm_model.pkl",
  "stage_model_loaded": true,
  "stage_artifact_path": "models/stage_model.pkl",
  "uptime_seconds": 123.456
}
```

- **`model_loaded`:** `false` only if loading failed (normally startup raises if no artifact exists).
- **`uptime_seconds`:** process uptime since module import.

## `GET /latest`

Returns the last 7 daily discharge values and optional stage values (plus aligned NOAA fields when `data/raw/noaa/rainfall_<Location>.csv` exists) for autofill in the UI. Response includes `rainfall_mm`, `tmax_c`, `tmin_c`, and when those files contain the columns, `awnd` (m/s), `snow` (mm), and `snow_depth` (mm, from SNWD). See `api/app.py` for query parameters (`site_id`, optional `end_date`).

## `GET /predict`

Query parameters:

| Parameter | Required | Description |
|-----------|----------|-------------|
| `site_id` | yes | USGS site id (traceability; not always a model feature) |
| `recent_discharge` | yes | Comma-separated **ft³/s** values, **oldest → newest**, ≥ 7 days |
| `as_of_date` | no | `YYYY-MM-DD` for seasonality features (`month_sin`, `month_cos`); default UTC today |
| `recent_prcp` | no | Comma-separated mm/day, oldest→newest, ≥ 7 if provided |
| `tmax`, `tmin` | no | Comma-separated same-day series (≥ 7 if used end-to-end) |
| `awnd`, `snow`, `snow_depth` | no | Same pattern when supplied |
| `heavy_rain_threshold` | no | mm/day threshold for heavy-rain flag (default `20.0`) |

Response:

Binary-compatible response:

```json
{
  "site_id": "01646500",
  "prediction": 1,
  "probability": 0.72,
  "risk_label": "high"
}
```

Multiclass response:

```json
{
  "site_id": "01646500",
  "prediction": 2,
  "probability": {
    "normal": 0.08,
    "medium": 0.21,
    "high": 0.71
  }
}
```

- **`prediction`:** class index (`0/1` for binary, `0/1/2` for multiclass).
- **`probability`:** either scalar positive-class probability (binary) or class-probability map (multiclass).

Feature construction matches `modeling/features.py` / `api/predict.py` (seven-day windows, lag alignment).

## `GET /predict-stage`

Predicts next-day river stage (regression) when `models/stage_model.pkl` is available.

Query parameters:

| Parameter | Required | Description |
|-----------|----------|-------------|
| `site_id` | yes | USGS site id |
| `recent_stage` | yes | Comma-separated stage values, oldest → newest, ≥ 7 |
| `recent_discharge` | no | Optional discharge series, oldest → newest, ≥ 7 |
| `recent_prcp` | no | Optional precipitation series |
| `tmax`, `tmin` | no | Optional temperature series |
| `as_of_date` | no | `YYYY-MM-DD` for month feature |

Response:

```json
{
  "site_id": "01646500",
  "predicted_stage_next_day": 3.84,
  "units": "ft"
}
```

## Error behavior

- Invalid or short `recent_discharge` / `recent_stage` → HTTP **400** with a clear `detail` message.
- Missing model files at startup → process fails fast (no silent fallback).

## Serving validation (recommended)

1. Start API: `python run_api.py`
2. `curl http://127.0.0.1:8000/health`
3. `curl` a `/predict` URL with 7+ discharge values (see README example).

Optional: compare API probabilities to offline evaluation on held-out rows (same feature builder) for regression checks after retraining.
