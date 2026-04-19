# MachineLearning-CivilEngineering

End-to-end flood-risk project for civil engineering workflows: **binary classification** of whether **next-day** river discharge exceeds a **site-specific high-flow threshold** (daily data, multi-site, chronological train/validation/test split, no random split, no leakage). The **official baseline** is **logistic regression** (standardized features); the **strong nonlinear model** is **LightGBM**.

## What this project does

- Fetches raw daily river data from USGS (discharge and optional stage).
- Fetches NOAA daily weather data (PRCP/TMAX/TMIN via CDO; optional AWND/SNOW/SNWD when present in files).
- Cleans and normalizes data into continuous daily time series (`clean_data.csv`).
- Builds lag/rolling features and a binary next-day target (`features.csv`).
- Trains `LogisticRegression` inside a `StandardScaler` **Pipeline** (balanced class weights) and `LGBMClassifier` on the **same** feature rows and split.
- Evaluates with held-out metrics, **naive baselines** (persistence + majority), **interpretability** exports, **forward-window** test stability, and **lead-time** analysis.
- Serves predictions with FastAPI; optional Next.js dashboard under `frontend/`.

## Repository structure

```text
api/
  app.py                 FastAPI: /latest, /predict, /health
  predict.py             Artifact loading + feature reconstruction + inference

data/
  raw/usgs/              Raw USGS CSV exports
  raw/noaa/              NOAA rainfall_*.csv + optional noaa_daily_*.csv
  processed/
    clean_data.csv       Cleaned daily time series
    features.csv         Model-ready feature matrix + target

data_ingestion/
  fetch_usgs.py          USGS NWIS daily values
  fetch_weather.py       NOAA CDO (token; paginated windows)
  verify_noaa_coverage.py Offline audit of rainfall files vs sites + date span
  sites.json             Gauge list (10 USGS sites)

data_processing/
  clean_data.py          Raw-to-clean processing

modeling/
  features.py            Feature engineering + target (per-site percentile threshold)
  train.py               Pipeline LR + LightGBM training
  evaluate.py            Metrics, compare_models, naive baselines
  interpretability.py    Logistic coefficients + LGBM importances → JSON
  backtest.py            Forward-window stability on chronological test set
  lead_time.py           Lead-day target shift (1,2,3,5,7) evaluation
  utils.py               time_based_split

models/
  model.pkl              Logistic Pipeline artifact (preferred name for baseline)
  lgbm_model.pkl         LightGBM artifact

results/
  metrics*.json          Per-model validation/test metrics
  comparison.json        Side-by-side LR vs LightGBM
  naive_baselines.json   Persistence + majority baselines
  noaa_coverage.json     NOAA file/date coverage report
  logistic_coefficients.json
  lgbm_feature_importance.json
  forward_window_stability.json
  lead_time_analysis.json

frontend/               Next.js app (dashboard)

run_api.py               Run API with repo root on sys.path
run_pipeline.py          End-to-end ML steps
requirements.txt
datasets.md, features.md, models.md, api.md
```

## Setup

```bash
python -m venv .venv
.venv\Scripts\activate   # Windows
pip install -r requirements.txt
```

## Run the pipeline (recommended defaults)

Full study period for gauges and NOAA (adjust if needed):

```bash
python run_pipeline.py --start-date 2018-01-01 --end-date 2024-12-31
```

Options:

- `--skip-fetch` — use existing `data/raw/usgs` files.
- `--model-type baseline` | `lightgbm` | `both` (default `both`).

Steps include: USGS fetch (unless skipped), **NOAA coverage audit**, clean data, features, training, evaluation, comparison, **naive baselines**, **interpretability JSON**, **forward-window stability** (LightGBM), lead-time analysis.

### NOAA weather fetch (separate token step)

```bash
set NOAA_CDO_TOKEN=your_token
python -m data_ingestion.fetch_weather --sites-config data_ingestion/sites.json --start-date 2018-01-01 --end-date 2024-12-31 --out-dir data/raw/noaa
```

### Manual verification (offline)

```bash
python -m data_ingestion.verify_noaa_coverage --noaa-dir data/raw/noaa --out-json results/noaa_coverage.json
```

Add `--warn-only` to always exit 0 (report-only in CI).

### Individual commands

```bash
python -m data_processing.clean_data --raw-dir data/raw/usgs --out-path data/processed/clean_data.csv
python -m modeling.features --clean-path data/processed/clean_data.csv --out-path data/processed/features.csv --noaa-dir data/raw/noaa
python -m modeling.train --features-path data/processed/features.csv --model-out models/model.pkl --model-type baseline
python -m modeling.train --features-path data/processed/features.csv --model-out models/lgbm_model.pkl --model-type lightgbm
python -m modeling.evaluate --compare --model-paths models/model.pkl models/lgbm_model.pkl --out-path results/comparison.json
python -m modeling.evaluate --naive-baselines --out-path results/naive_baselines.json
python -m modeling.interpretability --out-dir results
python -m modeling.backtest --model-path models/lgbm_model.pkl --out-path results/forward_window_stability.json
python -m modeling.lead_time --model-path models/lgbm_model.pkl --noaa-dir data/raw/noaa
```

## Run the API

```bash
uvicorn api.app:app --reload
# or
python run_api.py
```

- Docs: [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)
- **GET `/health`** — process uptime, whether a model artifact is loaded, and which file (`models/lgbm_model.pkl` preferred over `models/model.pkl`).

## Model summary (official framing)

- **Task:** binary; **horizon:** 1 day; **sites:** 10 USGS gauges; **split:** chronological `0.70 / 0.15 / 0.15` on the stacked multi-site timeline (see `modeling/utils.py`).
- **Target:** per site, threshold = historical discharge quantile (default **90th**); `target = 1` if next-day discharge **>** threshold.
- **Baseline:** `Pipeline(StandardScaler, LogisticRegression(max_iter=5000, class_weight="balanced"))`.
- **Strong model:** `LGBMClassifier` (balanced; fixed hyperparameters in `modeling/train.py`).

**Example official metrics** (reproduce with current `features.csv` and training scripts; see `models.md` for the full table):

| Split | Logistic (F1) | LightGBM (F1) |
|--------|----------------|---------------|
| Validation | 0.462 | 0.671 |
| Test | **0.794** | 0.772 |

On this snapshot the logistic baseline **slightly outperforms LightGBM on test F1**; LightGBM often leads on **ROC-AUC** (~0.98). Always trust a fresh `results/comparison.json` after retraining.

## Frontend (`frontend/`)

Next.js App Router UI for the dashboard. From repo root:

```bash
cd frontend
npm install
npm run dev
```

Set **`NEXT_PUBLIC_API_URL`** if the FastAPI backend is not at `http://127.0.0.1:8000` (no trailing slash). Run **`python run_api.py`** in a separate terminal so the UI can reach `/latest` and `/predict`.

## Documentation

| File | Contents |
|------|----------|
| `datasets.md` | USGS/NOAA sources, schemas, site→weather mapping, coverage verification |
| `features.md` | Feature definitions, merge/join rules, missing-weather handling |
| `models.md` | Training, metrics, baselines, interpretability, stability analysis |
| `api.md` | Endpoints, parameters, health check |

## Project status

**Done:** multi-site ingestion through `features.csv`; chronological evaluation; Pipeline logistic baseline; LightGBM; aligned `compare_models` row sets; NOAA verification script; naive baselines; coefficient/importance exports; forward-window test diagnostics; `/health`; lead-time script.

**Future:** production monitoring stack, calibration dashboards, automated tests, hyperparameter search beyond fixed configs.
