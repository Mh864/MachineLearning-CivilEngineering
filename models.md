# Models Guide

Supervised **binary classifiers** for **next-day** high-flow exceedance (per-site discharge threshold). **No random split:** training uses a **chronological** cut on the stacked multi-site table (`modeling/utils.py::time_based_split`, default `0.70 / 0.15 / 0.15`).

## 1) Official logistic baseline (Pipeline)

### Where

- Training: `modeling/train.py` → `train_baseline_model`
- Artifact: `models/model.pkl` (default)

### How it is trained

1. Load `data/processed/features.csv` with the same columns as `FEATURE_COLUMNS` + `site_id`, `date`, `target`.
2. Drop rows with missing features or target.
3. `time_based_split(..., train_frac=0.70, val_frac=0.15)`.
4. Fit:

```text
Pipeline([
  ("scaler", StandardScaler()),
  ("clf", LogisticRegression(max_iter=5000, class_weight="balanced")),
])
```

Standardization is **required** so the linear model converges stably with mixed-scale inputs.

### Artifact

```python
{
  "model": fitted_pipeline,  # predict / predict_proba delegate to the Pipeline
  "feature_columns": FEATURE_COLUMNS,
  "model_name": "logistic_baseline",
}
```

### Interpretability

```bash
python -m modeling.interpretability --out-dir results
```

Writes `results/logistic_coefficients.json`: standardized coefficients sorted by absolute value (from the `clf` step).

## 2) LightGBM (`LGBMClassifier`)

### Where

- Training: `modeling/train.py` → `train_lightgbm_model`
- Artifact: `models/lgbm_model.pkl`

### Config (fixed, reproducible)

- `n_estimators=300`, `learning_rate=0.05`, `num_leaves=31`, `class_weight="balanced"`, `random_state=42`, `n_jobs=-1`

### Interpretability

Same command as above produces `results/lgbm_feature_importance.json` (`feature_importances_`).

## 3) Naive baselines (same split as production models)

Not learned models; used to calibrate how much value ML adds.

```bash
python -m modeling.evaluate --naive-baselines --out-path results/naive_baselines.json
```

- **Persistence:** `ŷ(t) = y(t−1)` within each USGS site (previous row after `date`, `site_id` ordering used by `time_based_split`).
- **Majority:** always predict the **training-slice** majority class.

## 4) Evaluation and comparison

- Single model: `python -m modeling.evaluate --model-path models/model.pkl --out-path results/metrics.json`
- Compare: `python -m modeling.evaluate --compare --model-paths models/model.pkl models/lgbm_model.pkl --out-path results/comparison.json`

`compare_models` evaluates on the **same** `(X_val, X_test)` rows for every artifact (complete feature rows only).

## 5) Forward-window stability (test period)

Splits the **chronological test** set into contiguous time windows (default **4**) and reports metrics per window **without retraining** (same trained model).

```bash
python -m modeling.backtest --model-path models/lgbm_model.pkl --out-path results/forward_window_stability.json
```

Use this to see whether performance is stable over the test years or concentrated in one sub-period.

## 6) Lead-time analysis

Redefines the target as exceedance **k** days ahead (`k ∈ {1,2,3,5,7}`), rebuilds features from `clean_data.csv` + NOAA, and evaluates the **same frozen** classifier on each horizon. See `modeling/lead_time.py`.

## 7) Example metrics (official multi-site run)

After retraining on the full multi-site `features.csv`, a representative snapshot is:

**Logistic Regression (Pipeline)**

| Split | Accuracy | Precision | Recall | F1 |
|--------|------------|------------|--------|-----|
| Validation | 0.982 | 0.375 | 0.600 | **0.462** |
| Test | 0.963 | 0.730 | 0.871 | **0.794** |

**LightGBM**

| Split | Test F1 | Test ROC-AUC |
|--------|---------|----------------|
| (typical) | **~0.772** | **~0.984** |

On this snapshot the **baseline slightly exceeds LightGBM on test F1**; LightGBM is often stronger on **ROC-AUC**. **Always** use the numbers in your current `results/comparison.json` after training.

## 8) Metrics definitions

- **Accuracy:** fraction of correct labels (can be high when negatives dominate).
- **Precision / recall / F1:** standard binary definitions (`f1` uses `zero_division=0`).
- **ROC-AUC:** ranking quality from `predict_proba` on the test set (when available).

## 9) Where models are used

- `modeling/evaluate.py` — validation/test metrics
- `api/predict.py` + `api/app.py` — online inference (`GET /predict`)
- API prefers `models/lgbm_model.pkl` if present, otherwise `models/model.pkl`
