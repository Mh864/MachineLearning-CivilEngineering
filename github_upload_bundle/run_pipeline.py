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
    p.add_argument("--start-date", type=str, default="2015-01-01")
    p.add_argument("--end-date", type=str, default="2023-12-31")
    p.add_argument("--model-type", choices=["baseline", "lightgbm", "both"], default="both")
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
        run([
            "-m", "modeling.train",
            "--features-path", "data/processed/features.csv",
            "--model-out", "models/model.pkl",
            "--model-type", "baseline",
        ], "Step 4a: Train baseline model (Logistic Regression)")
        model_paths.append("models/model.pkl")

        run([
            "-m", "modeling.evaluate",
            "--features-path", "data/processed/features.csv",
            "--model-path", "models/model.pkl",
            "--out-path", "results/metrics_baseline.json",
        ], "Step 5a: Evaluate baseline model")

    if args.model_type in ("lightgbm", "both"):
        run([
            "-m", "modeling.train",
            "--features-path", "data/processed/features.csv",
            "--model-out", "models/lgbm_model.pkl",
            "--model-type", "lightgbm",
        ], "Step 4b: Train LightGBM model")
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
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
