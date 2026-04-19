# MachineLearning-CivilEngineering

End-to-end flood-risk project for civil engineering workflows: **binary classification** of whether **next-day** river discharge exceeds a **site-specific high-flow threshold** (daily data, multi-site, chronological train/validation/test split, no random split, no leakage). The **official baseline** is **logistic regression** (standardized features); the **strong nonlinear model** is **LightGBM**.

## What this project does

- Fetches raw daily river data from USGS (discharge and optional stage).
- Fetches NOAA daily weather data (PRCP/TMAX/TMIN via CDO; optional AWND/SNOW/SNWD when present in files).
- Cleans and normalizes data into continuous daily time series (`clean_data.csv`).
- Builds lag/rolling features and a binary next-day target (`features.csv`).
- Trains `LogisticRegression` inside a `StandardScaler` **Pipeline** (balanced class weights) and `LGBMClassifier` on the **same** feature rows and split.
- **Calibrates** predicted probabilities on the **validation** slice (isotonic regression if possible, else Platt scaling) so API/UI probabilities are better aligned with observed frequencies; see [Probability calibration](#probability-calibration) below.
- Evaluates with held-out metrics (including **Brier score** and **per-site test** breakdown in `--compare`), **naive baselines** (persistence + majority), **interpretability** exports, **forward-window** test stability, and **lead-time** analysis.
- Includes **Step 3 automated parity tests** (`tests/`) so inference feature reconstruction stays aligned with training; see [Feature parity tests (Step 3)](#feature-parity-tests-step-3).
- Serves predictions with FastAPI; optional Next.js dashboard under `frontend/` or `frontend1/`.

This README is the **single place** that lists what the project includes and **how to run commands** to see each part working. Details also appear in `features.md`, `models.md`, `datasets.md`, and `api.md`.

## Everything included (at a glance)

| Area | What it is |
|------|------------|
| **Core ML** | USGS + NOAA → `clean_data.csv` → `features.csv` → train logistic + LightGBM → chronological train/val/test, no leakage. |
| **Target** | Per gauge: next-day discharge **above** a site-specific high-flow threshold (default **90th percentile** of that site’s history)—not an official “flood” flag from an agency. |
| **Snow** | `snow` and `snow_depth` in `FEATURE_COLUMNS`; NOAA `SNOW`/`SNWD` merged when present; missing filled like other weather (see `features.md`). Retrain after adding these so artifacts match. |
| **Step 1 — Evaluation** | `modeling.evaluate --compare` writes **`test_brier`**, global metrics, and **`per_site_test`** (per USGS id on the held-out test slice). Console prints a **Test Brier** column. |
| **Step 2 — Calibration** | After training on **train**, probabilities are calibrated on **validation** (isotonic, else sigmoid). Saved in `models/*.pkl` under **`calibration`**. API `/predict` returns **calibrated** `probability` unless you use `--no-calibration`. |
| **Step 3 — Parity test** | `tests/test_feature_parity.py` checks **`api/predict._build_feature_frame`** matches **`modeling.features._add_features_per_site`** for the same 7-day window. Uses `merge_weather_into_site_discharge`. |
| **API** | FastAPI: `/health` (optional **`calibration`** JSON), `/latest`, `/predict`. |
| **Frontend** | Next.js dashboard (`frontend/` or `frontend1/`): station picker, 7-day inputs, **Predict**; needs API running. |

## How to verify the work (runbook)

Do these from the **repository root** after `pip install -r requirements.txt` (and `npm install` inside the frontend folder if you use the UI).

1. **Retrain and refresh metrics (sees Step 1 + Step 2 in outputs)**  
   ```bash
   python -m modeling.train --features-path data/processed/features.csv --model-out models/model.pkl --model-type baseline
   python -m modeling.train --features-path data/processed/features.csv --model-out models/lgbm_model.pkl --model-type lightgbm
   python -m modeling.evaluate --compare --model-paths models/model.pkl models/lgbm_model.pkl --out-path results/comparison.json
   ```  
   **Look for:** `results/comparison.json` — each model has **`test_brier`**, **`per_site_test`** (nested by site id), and validation/test F1. Console table includes **Test Brier**.

2. **Confirm Step 2 (calibration) on disk**  
   ```bash
   python -c "import joblib; a=joblib.load('models/lgbm_model.pkl'); print(a.get('calibration')); print(type(a['model']).__name__)"
   ```  
   **Look for:** `{'method': 'isotonic' or 'sigmoid', 'fit_on': 'validation'}` and typically **`CalibratedClassifierCV`** (or `method: none` / base class if you used `--no-calibration`).

3. **Confirm Step 2 in the API (server must be running)**  
   Terminal A: `python run_api.py`  
   Terminal B (stdlib, no `requests` required):  
   ```bash
   python -c "import urllib.request; print(urllib.request.urlopen('http://127.0.0.1:8000/health').read().decode())"
   ```  
   **Look for:** `"calibration":{"method":"...","fit_on":"validation"}` in the JSON.

4. **Step 3 — parity test (needs `data/processed/clean_data.csv` and `data/raw/noaa/`)**  
   ```bash
   python -m pytest tests/test_feature_parity.py -v
   ```  
   **Look for:** `PASSED`. If data are missing, the test **skips** with a clear reason.

5. **Frontend**  
   Terminal A: `python run_api.py`  
   Terminal B: `cd frontend1` (or `frontend`) → `npm install` → `npm run dev` → open the URL shown (usually `http://localhost:3000`).  
   **Look for:** header **API Connected**, load a station, **Predict** shows a probability.

**Optional — train without calibration (compare raw vs calibrated behavior):**  
`python -m modeling.train ... --no-calibration` (same flag on `run_pipeline.py`).

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

tests/
  test_feature_parity.py Step 3: pytest — API `_build_feature_frame` vs training `_add_features_per_site`

modeling/
  features.py            Feature engineering + target; `merge_weather_into_site_discharge` for tests
  train.py               Pipeline LR + LightGBM training + optional val calibration
  calibration.py         Validation-set probability calibration (sklearn CalibratedClassifierCV)
  evaluate.py            Metrics, compare_models, naive baselines, Brier, per-site test
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
frontend1/              Alternate Next.js dashboard (same API contract)

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
- `--no-calibration` — skip validation-set probability calibration for both models (same flag as `modeling.train`).

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
# Optional: train without wrapping the base estimator in probability calibration (raw base probabilities in API)
# python -m modeling.train ... --no-calibration
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
- **GET `/health`** — process uptime, whether a model artifact is loaded, which file (`models/lgbm_model.pkl` preferred over `models/model.pkl`), and when present the **`calibration`** block from the artifact (method and `fit_on: validation`).

## Probability calibration

**Why:** Tree and linear models often produce **ranking** scores that are not well-calibrated as probabilities. Reporting **Brier score** and calibration curves is easier if `P(flood tomorrow)` is aligned with how often the positive class actually occurs.

**What we do:** After fitting the base estimator on the **train** slice only, we fit `sklearn.calibration.CalibratedClassifierCV` on the **validation** slice (same chronological `0.70 / 0.15 / 0.15` split as training). The first method tried is **isotonic** regression; if that fails, **sigmoid** (Platt). If both fail (e.g. only one class in validation) or you pass **`--no-calibration`**, the saved artifact is the **uncalibrated** base model.

**Artifacts:** Each `models/*.pkl` dict includes `calibration: { "method": "isotonic" | "sigmoid" | "none", "fit_on": "validation" }`. Inference (`api/predict.py`) and evaluation (`modeling/evaluate.py`) call `predict` / `predict_proba` on the **saved** object, so calibrated probabilities flow to the API and to `results/comparison.json` **test Brier** when you retrain.

**sklearn versions:** On **scikit-learn ≥ 1.6**, prefitted calibration uses `FrozenEstimator` inside `CalibratedClassifierCV` (the old `cv="prefit"` style is deprecated). For older sklearn, `modeling/calibration.py` falls back to `cv="prefit"` when the frozen path is unavailable.

**Interpretability:** Coefficients and LightGBM importances are read from the **underlying** base estimator via `unwrap_calibrated_estimator` in `modeling/interpretability.py`, not from the calibration wrapper.

## Feature parity tests (Step 3)

**Goal:** Catch **training/inference drift** — if someone edits `FEATURE_COLUMNS`, `modeling/features.py`, or `api/predict.py` without updating the other side, predictions can silently use a different feature vector than the model was trained on.

**What runs:** `tests/test_feature_parity.py` loads `data/processed/clean_data.csv` and `data/raw/noaa/`, builds a training row with `_add_features_per_site`, extracts the **same** seven calendar days of discharge + weather used for that row, calls `_build_feature_frame` from `api/predict.py`, and asserts all `FEATURE_COLUMNS` match within tolerance. The test **skips** if those data paths are missing (e.g. CI without data).

**Refactor:** `merge_weather_into_site_discharge` in `modeling/features.py` is the shared “USGS + NOAA merge + fill” step used before lag/rolling features; tests use it to build the 7-day windows passed to the API.

**How to run** (from repo root, after `pip install -r requirements.txt`):

```bash
python -m pytest tests/test_feature_parity.py -v
```

Run this after any change to feature definitions or inference reconstruction.

## Model summary (official framing)

- **Task:** binary; **horizon:** 1 day; **sites:** 10 USGS gauges; **split:** chronological `0.70 / 0.15 / 0.15` on the stacked multi-site timeline (see `modeling/utils.py`).
- **Target:** per site, threshold = historical discharge quantile (default **90th**); `target = 1` if next-day discharge **>** threshold.
- **Baseline:** `Pipeline(StandardScaler, LogisticRegression(max_iter=5000, class_weight="balanced"))`, then wrapped with validation calibration unless `--no-calibration`.
- **Strong model:** `LGBMClassifier` (balanced; fixed hyperparameters in `modeling/train.py`), then same calibration step.

**Metrics:** After retraining, run `python -m modeling.evaluate --compare --model-paths models/model.pkl models/lgbm_model.pkl --out-path results/comparison.json`. That file reports validation/test **F1**, test **ROC-AUC**, test **Brier score** (lower is better for probability quality), and **per-site** test metrics. Numbers depend on `features.csv` and random seeds; do not rely on stale tables in docs.

## Frontend (`frontend/` or `frontend1/`)

Next.js App Router UI for the dashboard. From repo root:

```bash
cd frontend
# or: cd frontend1
npm install
npm run dev
```

Set **`NEXT_PUBLIC_API_URL`** if the FastAPI backend is not at `http://127.0.0.1:8000` (no trailing slash). Run **`python run_api.py`** in a separate terminal so the UI can reach `/latest` and `/predict`. The **`probability`** shown for predictions matches the **calibrated** `predict_proba` from the saved artifact (unless you trained with `--no-calibration`).

## Documentation

| File | Contents |
|------|----------|
| `datasets.md` | USGS/NOAA sources, schemas, site→weather mapping, coverage verification |
| `features.md` | Feature definitions, merge/join rules, missing-weather handling |
| `models.md` | Training, metrics, baselines, interpretability, stability analysis |
| `api.md` | Endpoints, parameters, health check |

## Project status

**Done:** multi-site ingestion through `features.csv`; chronological evaluation; Pipeline logistic baseline; LightGBM; **validation-set probability calibration** (default); aligned `compare_models` with **Brier** and **per-site test** metrics; **Step 3 pytest feature parity** (`tests/test_feature_parity.py`) + `merge_weather_into_site_discharge`; NOAA verification script; naive baselines; coefficient/importance exports (unwraps calibrated models); forward-window test diagnostics; `/health` (includes optional **calibration** metadata); lead-time script.

**Future:** production monitoring stack, calibration **visualization** dashboards, broader automated tests (e.g. API smoke tests), hyperparameter search beyond fixed configs.
