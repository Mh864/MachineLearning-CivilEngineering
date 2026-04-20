# Operations Layer Guide (Refresh + Monitoring)

This guide describes the new no-refactor operations layer added on top of the existing ML pipeline.
It covers the logic, reasoning, and exact steps to run and schedule refresh and monitoring.

## Why this approach

The project already has a working modeling and API pipeline. Instead of changing core ML code, this ops layer:

- wraps existing commands safely,
- adds operational status files and logs,
- provides monitoring outputs for missingness, drift, and performance trend,
- and keeps the original architecture intact.

This matches the teacher requirements for:

- Step 6: serve and refresh predictions,
- Step 7: monitor the system over time.

## What was added

- `ops/daily_refresh.py`
  - Runs `run_pipeline.py` with chosen arguments.
  - Creates model backups before refresh.
  - Restores previous models automatically if refresh fails.
  - Writes refresh status to `results/ops/last_refresh_status.json`.
  - Writes detailed run logs to `results/ops/logs/`.

- `ops/monitoring_config.json`
  - Central thresholds and monitored columns.
  - Allows tuning without editing Python code.

- `ops/monitoring_report.py`
  - Generates:
    - `results/monitoring_report.json`
    - `results/monitoring_report.md`
  - Evaluates three monitoring dimensions:
    - missingness,
    - feature drift (PSI),
    - performance trend.

- `api/app.py` update
  - `/health` now includes `last_refresh` when `results/ops/last_refresh_status.json` exists.

## Detailed logic

## 1) Refresh logic (`ops/daily_refresh.py`)

### A) Pre-refresh model safety

Before running the pipeline, the script copies current model artifacts (if present):

- `models/model.pkl`
- `models/lgbm_model.pkl`

Backups are timestamped in:

- `results/ops/model_backups/`

Reasoning:

- Training can fail mid-run or produce broken output.
- Backups allow quick rollback to last known-good models.

### B) Pipeline execution

The script executes the existing pipeline command:

- `python run_pipeline.py --start-date ... --end-date ... --model-type ...`

Optional passthrough flags:

- `--skip-fetch`
- `--no-calibration`

All stdout/stderr are saved to one timestamped log file in:

- `results/ops/logs/`

Reasoning:

- Preserves your existing run order and model behavior.
- Gives an auditable record for debugging and grading/demo evidence.

### C) Failure handling and rollback

If pipeline exit code is non-zero:

- script restores backed-up model files to `models/`,
- marks run as failed,
- records restored model list.

Reasoning:

- Keeps API predictions available with previous models.
- Avoids leaving deployment in a partially updated state.

### D) Status artifact

After each run, script writes:

- `results/ops/last_refresh_status.json`

Includes:

- status (`success` or `failed`),
- start/end timestamps and duration,
- full command used,
- log path,
- args used,
- backup info,
- restore info on failure.

Reasoning:

- Enables machine-readable operational state for dashboards and `/health`.

## 2) Monitoring logic (`ops/monitoring_report.py`)

The script runs independently from training and reads existing artifacts/data.

## A) Missingness monitoring

Data source:

- `data/processed/clean_data.csv`

Method:

- Compare recent window (default 30 days) vs reference window (default 180 days before recent window).
- Compute missing percentage by configured columns:
  - `discharge`, `stage`, `prcp`, `tmax`, `tmin`, `awnd`, `snow`, `snow_depth`.
- Alert when recent missingness increases above threshold (default +10 percentage points).

Reasoning:

- Detects upstream ingestion issues or station data quality deterioration.

## B) Drift monitoring (PSI)

Data source:

- `data/processed/features.csv`

Method:

- Compare configured feature columns between reference and recent windows:
  - `discharge_lag1`, `discharge_roll_mean_7`, `prcp_roll_sum_7`, `month`.
- Compute Population Stability Index (PSI) per feature.
- Alert when PSI exceeds threshold (default 0.2).

Reasoning:

- Identifies data distribution changes that can degrade model reliability.

## C) Performance trend monitoring

Data sources:

- `results/comparison.json`
- `results/forward_window_stability.json` (if available)

Method:

- Uses best model snapshot from comparison output (`validation_f1`, `test_f1`, `test_brier`).
- Uses forward-window report to compare early vs late window average F1.
- Alerts if:
  - F1 drop exceeds configured threshold (default 0.1),
  - or test Brier exceeds configured threshold (default 0.02).

Reasoning:

- Catches degradation over time and weak generalization from validation to test behavior.

## D) Outputs

Script writes:

- `results/monitoring_report.json` (machine readable)
- `results/monitoring_report.md` (human readable summary)

Overall status:

- `ok` if no alerts,
- `alert` if one or more alerts are triggered.

## 3) How to run manually

From repository root:

```bash
python ops/daily_refresh.py --start-date 2018-01-01 --end-date 2024-12-31 --model-type both
python ops/monitoring_report.py
```

Single-command wrapper (recommended for clean runs):

```bash
python run_ops.py --start-date 2018-01-01 --end-date 2024-12-31 --model-type both
```

Optional refresh flags:

```bash
python ops/daily_refresh.py --skip-fetch --model-type both
python ops/daily_refresh.py --model-type lightgbm --no-calibration
```

Wrapper flags:

```bash
python run_ops.py --skip-fetch --model-type both
python run_ops.py --model-type lightgbm --no-calibration
python run_ops.py --model-type both --with-stage
python run_ops.py --skip-monitoring
```

## 4) How to schedule on Windows (Task Scheduler)

Create two tasks:

1. Daily Refresh (e.g., 02:00)
2. Daily Monitoring (e.g., 02:30, after refresh)

Action command example (Program/script):

- `C:\path\to\python.exe`

Arguments:

- `ops/daily_refresh.py --start-date 2018-01-01 --end-date 2024-12-31 --model-type both`

Start in:

- repository root path

For monitoring task arguments:

- `ops/monitoring_report.py`

## 5) How to verify this is working

After running refresh:

- check `results/ops/last_refresh_status.json`,
- check latest log in `results/ops/logs/`,
- call API `/health` and confirm `last_refresh` appears.

After running monitoring:

- check `results/monitoring_report.json`,
- open `results/monitoring_report.md`,
- confirm alert list matches expected thresholds.

## 6) Suggested tuning strategy

Start with defaults, then tune based on your historical baseline:

- missingness threshold:
  - tighter if data is typically clean,
  - looser if some gauges frequently have gaps.
- PSI threshold:
  - keep 0.2 for moderate sensitivity in student projects.
- F1/Brier thresholds:
  - tune using observed variance in your forward-window outputs.

All tuning lives in:

- `ops/monitoring_config.json`

No code edits are needed for threshold adjustments.

## 7) Scope boundaries (intentional)

This ops layer is intentionally lightweight and local:

- no cloud orchestration,
- no external alerting service integration,
- no database persistence beyond JSON/Markdown artifacts.

It is designed to be robust enough for an academic end-to-end demonstration while keeping the project simple and reproducible.
