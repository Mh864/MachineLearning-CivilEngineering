#!/bin/bash
set -e

echo "=== Step 1: Fetch USGS data for all 10 sites ==="
python -m data_ingestion.fetch_usgs \
  --sites-config data_ingestion/sites.json \
  --start-date 2015-01-01 \
  --end-date 2023-12-31 \
  --out-dir data/raw/usgs \
  --include-stage

echo "=== Step 2: Clean data ==="
python -m data_processing.clean_data \
  --raw-dir data/raw/usgs \
  --out-path data/processed/clean_data.csv

echo "=== Step 3: Build features (with NOAA rainfall) ==="
python -m modeling.features \
  --clean-path data/processed/clean_data.csv \
  --out-path data/processed/features.csv \
  --noaa-dir data/raw/noaa

echo "=== Step 4: Train baseline model ==="
python -m modeling.train \
  --features-path data/processed/features.csv \
  --model-out models/model.pkl \
  --model-type baseline

echo "=== Step 5: Train LightGBM model ==="
python -m modeling.train \
  --features-path data/processed/features.csv \
  --model-out models/lgbm_model.pkl \
  --model-type lightgbm

echo "=== Step 6: Evaluate baseline ==="
python -m modeling.evaluate \
  --features-path data/processed/features.csv \
  --model-path models/model.pkl \
  --out-path results/metrics_baseline.json

echo "=== Step 7: Evaluate LightGBM ==="
python -m modeling.evaluate \
  --features-path data/processed/features.csv \
  --model-path models/lgbm_model.pkl \
  --out-path results/metrics_lgbm.json

echo "=== Step 8: Compare models ==="
python -m modeling.evaluate \
  --compare \
  --model-paths models/model.pkl models/lgbm_model.pkl \
  --out-path results/comparison.json

echo "=== Step 9: Lead-time analysis ==="
python -m modeling.lead_time \
  --clean-path data/processed/clean_data.csv \
  --model-path models/lgbm_model.pkl \
  --out-path results/lead_time_analysis.json

echo "=== Done. Results in results/ ==="
