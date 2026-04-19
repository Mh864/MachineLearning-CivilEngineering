"""
run_pipeline.py — End-to-end pipeline runner.

Usage (from project root):
    python run_pipeline.py
    python run_pipeline.py --model-type lightgbm
    python run_pipeline.py --skip-fetch   # if data already downloaded
"""
from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).parent


def run(cmd: list[str], step: str) -> None:
    print(f"\n{'='*60}")
    print(f"  {step}")
    print(f"{'='*60}")
    result = subprocess.run([sys.executable] + cmd, cwd=ROOT)
    if result.returncode != 0:
        print(f"\n[ERROR] Step failed: {step}")
        sys.exit(result.returncode)


def main() -> int:
    p = argparse.ArgumentParser(description="Run the full flood risk ML pipeline.")
    p.add_argument("--skip-fetch", action="store_true", help="Skip USGS data download (use existing raw data)")
    p.add_argument("--start-date", type=str, default="2018-01-01")
    p.add_argument("--end-date", type=str, default="2024-12-31")
    p.add_argument("--model-type", choices=["baseline", "lightgbm", "both"], default="both")
    p.add_argument(
        "--no-calibration",
        action="store_true",
        help="Pass through to modeling.train: skip validation-set probability calibration.",
    )
    args = p.parse_args()

    if not args.skip_fetch:
        run([
            "-m", "data_ingestion.fetch_usgs",
            "--sites-config", "data_ingestion/sites.json",
            "--start-date", args.start_date,
            "--end-date", args.end_date,
            "--out-dir", "data/raw/usgs",
            "--include-stage",
        ], "Step 1: Fetch USGS data for all 10 sites")
    else:
        print("\n[Skipping USGS fetch — using existing raw data]")

    run([
        "-m", "data_ingestion.verify_noaa_coverage",
        "--noaa-dir", "data/raw/noaa",
        "--expected-start", args.start_date,
        "--expected-end", args.end_date,
        "--out-json", "results/noaa_coverage.json",
        "--warn-only",
    ], "Step 1b: Verify NOAA rainfall CSV coverage (informational)")

    run([
        "-m", "data_processing.clean_data",
        "--raw-dir", "data/raw/usgs",
        "--out-path", "data/processed/clean_data.csv",
    ], "Step 2: Clean and align data")

    run([
        "-m", "modeling.features",
        "--clean-path", "data/processed/clean_data.csv",
        "--out-path", "data/processed/features.csv",
        "--noaa-dir", "data/raw/noaa",
    ], "Step 3: Build features (discharge + NOAA precipitation)")

    model_paths: list[str] = []

    if args.model_type in ("baseline", "both"):
        train_baseline = [
            "-m", "modeling.train",
            "--features-path", "data/processed/features.csv",
            "--model-out", "models/model.pkl",
            "--model-type", "baseline",
        ]
        if args.no_calibration:
            train_baseline.append("--no-calibration")
        run(train_baseline, "Step 4a: Train baseline model (Logistic Regression)")
        model_paths.append("models/model.pkl")

        run([
            "-m", "modeling.evaluate",
            "--features-path", "data/processed/features.csv",
            "--model-path", "models/model.pkl",
            "--out-path", "results/metrics_baseline.json",
        ], "Step 5a: Evaluate baseline model")

    if args.model_type in ("lightgbm", "both"):
        train_lgbm = [
            "-m", "modeling.train",
            "--features-path", "data/processed/features.csv",
            "--model-out", "models/lgbm_model.pkl",
            "--model-type", "lightgbm",
        ]
        if args.no_calibration:
            train_lgbm.append("--no-calibration")
        run(train_lgbm, "Step 4b: Train LightGBM model")
        model_paths.append("models/lgbm_model.pkl")

        run([
            "-m", "modeling.evaluate",
            "--features-path", "data/processed/features.csv",
            "--model-path", "models/lgbm_model.pkl",
            "--out-path", "results/metrics_lgbm.json",
        ], "Step 5b: Evaluate LightGBM model")

    if len(model_paths) >= 2:
        run([
            "-m", "modeling.evaluate",
            "--compare",
            "--features-path", "data/processed/features.csv",
            "--model-paths", *model_paths,
            "--out-path", "results/comparison.json",
        ], "Step 6: Compare models side by side")

    run([
        "-m", "modeling.evaluate",
        "--naive-baselines",
        "--features-path", "data/processed/features.csv",
        "--out-path", "results/naive_baselines.json",
    ], "Step 6b: Naive baselines (persistence + majority class)")

    if model_paths:
        run([
            "-m", "modeling.interpretability",
            "--out-dir", "results",
        ], "Step 6c: Export logistic coefficients + LightGBM feature importance")

    if "models/lgbm_model.pkl" in model_paths:
        run([
            "-m", "modeling.backtest",
            "--features-path", "data/processed/features.csv",
            "--model-path", "models/lgbm_model.pkl",
            "--out-path", "results/forward_window_stability.json",
        ], "Step 6d: Forward-window test stability (LightGBM)")

    if "models/lgbm_model.pkl" in model_paths:
        run([
            "-m", "modeling.lead_time",
            "--clean-path", "data/processed/clean_data.csv",
            "--model-path", "models/lgbm_model.pkl",
            "--noaa-dir", "data/raw/noaa",
            "--out-path", "results/lead_time_analysis.json",
        ], "Step 7: Lead-time analysis (1, 2, 3, 5, 7 days)")
    elif "models/model.pkl" in model_paths:
        run([
            "-m", "modeling.lead_time",
            "--clean-path", "data/processed/clean_data.csv",
            "--model-path", "models/model.pkl",
            "--noaa-dir", "data/raw/noaa",
            "--out-path", "results/lead_time_analysis.json",
        ], "Step 7: Lead-time analysis (1, 2, 3, 5, 7 days)")

    print("\n" + "=" * 60)
    print("  Pipeline complete. Results saved in results/")
    print("=" * 60)
    print("  results/metrics_baseline.json  — Logistic Regression metrics")
    print("  results/metrics_lgbm.json      — LightGBM metrics")
    print("  results/comparison.json        — Side-by-side comparison")
    print("  results/lead_time_analysis.json — Accuracy at 1-7 day horizons")
    print("  results/noaa_coverage.json        — NOAA file/date coverage audit")
    print("  results/naive_baselines.json      — Persistence + majority baselines")
    print("  results/logistic_coefficients.json  — Standardized LR coefficients")
    print("  results/lgbm_feature_importance.json — LightGBM gain importances")
    print("  results/forward_window_stability.json — Test-period window metrics (LGBM)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
