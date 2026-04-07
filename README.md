# MachineLearning-CivilEngineering

End-to-end flood-risk baseline project for civil engineering workflows.
The current implementation builds a binary classifier that predicts whether next-day river discharge is likely to exceed a high-flow threshold for a USGS gauge.

## What this project does

- Fetches raw daily river data from USGS (discharge and optional stage).
- Cleans and normalizes data into a continuous daily time series.
- Builds lag/rolling features and a binary next-day target.
- Trains a baseline `LogisticRegression` model.
- Evaluates on time-based validation/test splits and writes metrics.
- Serves predictions with a FastAPI backend.
- Includes a React/Vite frontend scaffold for manual prediction calls.

## Repository structure

```text
api/
  app.py                 FastAPI app and /predict endpoint
  predict.py             Artifact loading + feature reconstruction + inference

data/
  raw/
    usgs/                Raw USGS CSV exports
    noaa/                NOAA rainfall CSVs (rainfall_*.csv)
  processed/
    clean_data.csv       Cleaned daily time series
    features.csv         Model-ready feature matrix + target

data_ingestion/
  fetch_usgs.py          USGS NWIS daily values ingestion
  fetch_weather.py       NOAA ingestion scaffold (not implemented yet)
  sites.json             Gauge site configuration
  utils.py               Shared ingestion helpers (logging, HTTP retries, etc.)

data_processing/
  clean_data.py          Raw-to-clean processing with continuous daily index

modeling/
  features.py            Feature engineering + target construction (+ NOAA precip)
  train.py               Baseline + LightGBM model training
  evaluate.py            Single-model evaluation + model comparison
  lead_time.py           Forecast-horizon (lead-time) degradation analysis
  utils.py               Time-based split utility

models/
  model.pkl              Trained model artifact (model + feature columns)
  lgbm_model.pkl         Trained LightGBM artifact

results/
  metrics.json           Saved evaluation metrics
  comparison.json        Multi-model comparison metrics
  lead_time_analysis.json Lead-time performance analysis

frontend/vite-project/
  React frontend scaffold for making prediction requests

run_api.py               Convenience script to run API from any cwd
requirements.txt         Python dependencies
datasets.md              Dataset documentation (this repo)
api.md                   FastAPI documentation
features.md              Feature engineering documentation
run_full_pipeline.sh     Full ML pipeline runner
```

## Data pipeline flow

1. **Ingest raw USGS data** into `data/raw/usgs`.
2. **Clean and normalize** raw data to `data/processed/clean_data.csv`.
3. **Build features** to `data/processed/features.csv`.
4. **Train baseline and/or LightGBM models** and save artifacts.
5. **Evaluate one model** and/or compare multiple models.
6. **Analyze lead-time degradation** across forecast horizons.
7. **Serve predictions** via FastAPI.

## Setup

### 1) Python environment

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

### 2) (Optional) Frontend dependencies

```bash
cd frontend/vite-project
npm install
```

## Run the pipeline

From repository root:

### 1) Fetch USGS daily values

```bash
python -m data_ingestion.fetch_usgs --start-date 2018-01-01 --end-date 2024-12-31 --include-stage --per-site
```

Uses site ids from `data_ingestion/sites.json`.

### 2) Clean raw data

```bash
python -m data_processing.clean_data --raw-dir data/raw/usgs --out-path data/processed/clean_data.csv
```

### 3) Build features

```bash
python -m modeling.features --clean-path data/processed/clean_data.csv --out-path data/processed/features.csv --percentile 0.9 --noaa-dir data/raw/noaa
```

### 4) Train baseline model

```bash
python -m modeling.train --features-path data/processed/features.csv --model-out models/model.pkl --model-type baseline
```

### 5) Train LightGBM model

```bash
python -m modeling.train --features-path data/processed/features.csv --model-out models/lgbm_model.pkl --model-type lightgbm
```

### 6) Evaluate one model

```bash
python -m modeling.evaluate --features-path data/processed/features.csv --model-path models/lgbm_model.pkl --out-path results/metrics_lgbm.json
```

### 7) Compare models

```bash
python -m modeling.evaluate --features-path data/processed/features.csv --compare --model-paths models/model.pkl models/lgbm_model.pkl --out-path results/comparison.json
```

### 8) Lead-time analysis

```bash
python -m modeling.lead_time --clean-path data/processed/clean_data.csv --model-path models/lgbm_model.pkl --out-path results/lead_time_analysis.json
```

### 9) Full pipeline in one command

```bash
bash run_full_pipeline.sh
```

## Run the API

### Preferred (from repo root)

```bash
uvicorn api.app:app --reload
```

### If import path issues appear

```bash
python run_api.py
```

API docs: [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)

### Predict endpoint

`GET /predict`

Query params:

- `site_id`: string (currently included for traceability; baseline model does not use site metadata as input).
- `recent_discharge`: comma-separated numeric sequence (oldest to newest, at least 7 values).
- `as_of_date`: optional `YYYY-MM-DD`; if omitted, UTC today is used for month feature.

Example:

```text
/predict?site_id=01646500&recent_discharge=100,105,110,120,130,140,150&as_of_date=2024-01-10
```

## Frontend

The frontend app lives in `frontend/vite-project`.

Run it:

```bash
cd frontend/vite-project
npm run dev
```

Set backend URL with environment variable:

- `VITE_API_URL` (default expected by UI is local API).

Note: the current frontend references `src/lib/api` and may require a small integration file if not present in your local branch.

## Model details (current)

- Algorithm: `LogisticRegression(max_iter=2000, class_weight="balanced")`
- Alternative model: `LightGBM` (`LGBMClassifier`) with balanced class weights
- Features:
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
- Target:
  - For each site, threshold = discharge percentile (`--percentile`, default `0.9`)
  - `target = 1` if next-day discharge > threshold, else `0`
- Split:
  - Time-based chronological split using fractions train/val/test = `0.70/0.15/0.15`

## Outputs produced by pipeline

- `data/processed/clean_data.csv`: cleaned continuous daily gauge data.
- `data/processed/features.csv`: model-ready rows with engineered features and target.
- `models/model.pkl`: serialized artifact with trained model + feature column order.
- `models/lgbm_model.pkl`: serialized LightGBM artifact.
- `results/metrics*.json`: validation and test metrics (`accuracy`, `precision`, `recall`, `f1`).
- `results/comparison.json`: side-by-side baseline vs LightGBM metrics and summary.
- `results/lead_time_analysis.json`: performance by forecast horizon (1,2,3,5,7 days).

## Dataset documentation

See `datasets.md` for dataset sources, schemas, and planned data expansions.

## Project status: complete vs pending

### Complete

- USGS ingestion pipeline and configurable multi-site `sites.json`.
- Cleaning pipeline with deduplication and continuous daily indexing.
- Feature engineering for discharge dynamics and NOAA precipitation signals.
- Graceful NOAA fallback (missing rainfall data defaults to `0.0` features).
- Baseline logistic model training with time-based split.
- LightGBM training path with reproducible config.
- Standard evaluation metrics and multi-model comparison mode.
- Lead-time degradation analysis (`1, 2, 3, 5, 7` days ahead).
- FastAPI inference endpoint and separate frontend scaffold.
- Project documentation files: `datasets.md`, `api.md`, `features.md`.

### Not complete yet

- `data_ingestion/fetch_weather.py` is still a scaffold (`NotImplementedError`); NOAA ingestion is not implemented there.
- No automated tests yet (unit/integration/regression).
- No formal experiment tracking (MLflow/W&B) or model registry.
- No hyperparameter search pipeline beyond fixed baseline configs.
- Model outputs are mostly class labels; richer uncertainty/calibration workflows are pending.
- No production deployment/monitoring stack (CI/CD, drift monitoring, alerts).

## Current limitations / roadmap

- NOAA ingestion module remains scaffolded even though feature builder can consume prepared NOAA rainfall CSV files.
- Baseline feature set is still compact; no basin geomorphology/land-use/static attributes yet.
- No automated tests yet for ingestion, feature consistency, or API behavior.
- Probabilistic calibration and decision-threshold tuning are future improvements.