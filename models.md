# Models Guide

This file explains all models in the project, how they are trained, where they are used, and whether they are supervised or unsupervised.

## Quick classification

- `LogisticRegression` baseline model: **supervised learning** (binary classification)
- `LightGBM (LGBMClassifier)` model: **supervised learning** (binary classification)
- Unsupervised models: **none currently implemented**

The prediction task is: classify whether next-day (or lead-day) discharge exceeds a site-specific high-flow threshold.

## 1) Baseline model (Logistic Regression)

### Where it is defined

- Training: `modeling/train.py` in `train_baseline_model`
- Default output artifact: `models/model.pkl`

### How it is trained

1. Load features from `data/processed/features.csv`
2. Parse `date` and `target`
3. Keep modeling columns: `["site_id", "date"] + FEATURE_COLUMNS + ["target"]`
4. Drop rows with missing values
5. Split data using `time_based_split` (`train=0.70`, `val=0.15`, `test=0.15`)
6. Fit:
   - `LogisticRegression(max_iter=2000, class_weight="balanced")`

### Artifact format

Saved with joblib as:

```python
{
  "model": fitted_model,
  "feature_columns": FEATURE_COLUMNS
}
```

### Where it is used

- Evaluation: `modeling/evaluate.py` (`evaluate_model`, `compare_models`)
- API inference: `api/predict.py` via artifact loading and `model.predict(...)`
- Optional lead-time testing: `modeling/lead_time.py` if this artifact is passed

## 2) Advanced model (LightGBM classifier)

### Where it is defined

- Training: `modeling/train.py` in `train_lightgbm_model`
- Default output artifact: `models/lgbm_model.pkl`

### How it is trained

Data preparation is intentionally the same as baseline:

1. Load `data/processed/features.csv`
2. Parse `date` and `target`
3. Keep same modeling columns and drop missing rows
4. Use the same `time_based_split` (`0.70/0.15/0.15`)

Model config:

- `n_estimators=300`
- `learning_rate=0.05`
- `num_leaves=31`
- `class_weight="balanced"`
- `random_state=42`
- `n_jobs=-1`

### Artifact format

Saved with joblib as:

```python
{
  "model": fitted_model,
  "feature_columns": FEATURE_COLUMNS,
  "model_name": "lightgbm"
}
```

### Where it is used

- Single-model evaluation: `modeling/evaluate.py` (`evaluate_model`)
- Multi-model comparison: `modeling/evaluate.py` (`compare_models`)
- Lead-time analysis: `modeling/lead_time.py` (default model path points to LightGBM)
- Can be used by API inference if selected model artifact is loaded

## 3) Evaluation models vs analysis scripts

### `modeling/evaluate.py`

Not a model itself. It evaluates trained supervised classifiers.

- `evaluate_model`: computes `accuracy`, `precision`, `recall`, `f1`
- `compare_models`: compares multiple trained artifacts and also tries `test_roc_auc` if `predict_proba` is available

### `modeling/lead_time.py`

Also not a model itself. It redefines the target for different forecast horizons (`1,2,3,5,7` days ahead), then evaluates a trained classifier on each horizon.

## 4) Supervised vs unsupervised in this project

### Supervised (implemented)

Both implemented models are supervised because:

- training data includes explicit labels (`target`)
- models learn mapping from features to known classes (`0`/`1`)
- performance is measured against labeled validation/test targets

### Unsupervised (not implemented)

No clustering, anomaly detection, PCA, autoencoders, or self-supervised modules are currently part of the training pipeline.

## 5) Training entry points (CLI)

- Baseline:
  - `python -m modeling.train --features-path data/processed/features.csv --model-out models/model.pkl --model-type baseline`
- LightGBM:
  - `python -m modeling.train --features-path data/processed/features.csv --model-out models/lgbm_model.pkl --model-type lightgbm`

## 6) Model usage across project lifecycle

1. Build features (`modeling/features.py`)
2. Train model (`modeling/train.py`)
3. Evaluate model (`modeling/evaluate.py`)
4. Compare models (`modeling/evaluate.py --compare`)
5. Stress-test forecast horizon (`modeling/lead_time.py`)
6. Serve predictions (`api/predict.py` through `api/app.py`)

## 7) Current practical note

The training feature set now includes precipitation-derived features. Any artifact used for inference must have feature columns that the inference path can construct consistently; this should be validated whenever feature engineering changes.
