# API Guide (FastAPI)

The API exposes the trained classifier and supporting data endpoints for the flood exceedance task. CORS is enabled for local development (`allow_origins=["*"]`).

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

## `GET /health`

Lightweight **liveness/readiness** response for monitoring:

```json
{
  "status": "ok",
  "model_loaded": true,
  "artifact_path": "models/lgbm_model.pkl",
  "uptime_seconds": 123.456
}
```

- **`model_loaded`:** `false` only if loading failed (normally startup raises if no artifact exists).
- **`uptime_seconds`:** process uptime since module import.

## `GET /latest`

Returns the last 7 daily discharge values (and aligned NOAA fields when files exist) for autofill in the UI. See `api/app.py` for query parameters (`site_id`, optional `end_date`).

## `GET /predict`

Query parameters:

| Parameter | Required | Description |
|-----------|----------|-------------|
| `site_id` | yes | USGS site id (traceability; not always a model feature) |
| `recent_discharge` | yes | Comma-separated **ft³/s** values, **oldest → newest**, ≥ 7 days |
| `as_of_date` | no | `YYYY-MM-DD` for the **month** feature; default UTC today |
| `recent_prcp` | no | Comma-separated mm/day, oldest→newest, ≥ 7 if provided |
| `tmax`, `tmin` | no | Comma-separated same-day series (≥ 7 if used end-to-end) |
| `awnd`, `snow`, `snow_depth` | no | Same pattern when supplied |
| `heavy_rain_threshold` | no | mm/day threshold for heavy-rain flag (default `20.0`) |

Response:

```json
{
  "site_id": "01646500",
  "prediction": 0,
  "probability": 0.42
}
```

- **`prediction`:** binary class (`1` = higher estimated probability of next-day exceedance).
- **`probability`:** `predict_proba` positive class (`1`), from the loaded sklearn estimator (Pipeline or LightGBM).

Feature construction matches `modeling/features.py` / `api/predict.py` (seven-day windows, lag alignment).

## Error behavior

- Invalid or short `recent_discharge` → HTTP **400** with a clear `detail` message.
- Missing model files at startup → process fails fast (no silent fallback).

## Serving validation (recommended)

1. Start API: `python run_api.py`
2. `curl http://127.0.0.1:8000/health`
3. `curl` a `/predict` URL with 7+ discharge values (see README example).

Optional: compare API probabilities to offline evaluation on held-out rows (same feature builder) for regression checks after retraining.
