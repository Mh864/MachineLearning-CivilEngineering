from __future__ import annotations

import argparse
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import f1_score, recall_score
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

from modeling.calibration import fit_calibrated_classifier
from modeling.features import FEATURE_COLUMNS
from modeling.utils import time_based_split


def train_baseline_model(
    *,
    features_path: str | Path = "data/processed/features.csv",
    model_out_path: str | Path = "models/model.pkl",
    calibrate: bool = True,
    target_col: str = "target",
    optimize_for: str = "f1",
) -> Path:
    df = pd.read_csv(features_path, dtype={"site_id": "string"})
    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    df[target_col] = pd.to_numeric(df[target_col], errors="coerce")
    df = df.dropna(subset=["date", target_col]).sort_values(["site_id", "date"]).reset_index(drop=True)

    # Keep only required modeling columns
    keep_cols = ["site_id", "date"] + FEATURE_COLUMNS + [target_col]
    df = df[keep_cols].dropna()

    split = time_based_split(df, time_col="date", target_col=target_col, train_frac=0.70, val_frac=0.15)

    X_train = split.X_train[FEATURE_COLUMNS]
    y_train = split.y_train.astype(int)
    is_multiclass = target_col == "target_multiclass"

    clf_kwargs = {"max_iter": 5000, "class_weight": "balanced"}
    if is_multiclass:
        # Keep compatibility across sklearn variants where `multi_class` may be removed.
        try:
            clf = LogisticRegression(multi_class="multinomial", **clf_kwargs)
        except TypeError:
            clf = LogisticRegression(**clf_kwargs)
    else:
        clf = LogisticRegression(**clf_kwargs)
    model = Pipeline([("scaler", StandardScaler()), ("clf", clf)])
    model.fit(X_train, y_train)

    X_val = split.X_val[FEATURE_COLUMNS]
    y_val = split.y_val.astype(int)
    if calibrate and not is_multiclass:
        model, cal_method = fit_calibrated_classifier(model, X_val, y_val)
    else:
        cal_method = "none"
    best_threshold = None
    if not is_multiclass and hasattr(model, "predict_proba"):
        val_proba = model.predict_proba(X_val)[:, 1]
        best_threshold = _select_best_binary_threshold(y_val, val_proba, objective=optimize_for)

    artifact = {
        "model": model,
        "feature_columns": FEATURE_COLUMNS,
        "model_name": "logistic_multiclass" if is_multiclass else "logistic_baseline",
        "target_column": target_col,
        "target_type": "multiclass" if is_multiclass else "binary",
        "class_labels": [0, 1, 2] if is_multiclass else [0, 1],
        "best_threshold": best_threshold,
        "calibration": {"method": cal_method, "fit_on": "validation"},
    }

    model_out_path = Path(model_out_path)
    model_out_path.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(artifact, model_out_path)
    return model_out_path


def train_lightgbm_model(
    *,
    features_path: str | Path = "data/processed/features.csv",
    model_out_path: str | Path = "models/lgbm_model.pkl",
    calibrate: bool = True,
    target_col: str = "target",
    optimize_for: str = "f1",
) -> Path:
    try:
        from lightgbm import LGBMClassifier
    except ImportError:
        raise ImportError("Install lightgbm: pip install lightgbm")

    df = pd.read_csv(features_path, dtype={"site_id": "string"})
    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    df[target_col] = pd.to_numeric(df[target_col], errors="coerce")
    df = df.dropna(subset=["date", target_col]).sort_values(["site_id", "date"]).reset_index(drop=True)

    keep_cols = ["site_id", "date"] + FEATURE_COLUMNS + [target_col]
    df = df[keep_cols].dropna()

    split = time_based_split(df, time_col="date", target_col=target_col, train_frac=0.70, val_frac=0.15)

    X_train = split.X_train[FEATURE_COLUMNS]
    y_train = split.y_train.astype(int)
    is_multiclass = target_col == "target_multiclass"

    model_kwargs = dict(
        n_estimators=300,
        learning_rate=0.05,
        num_leaves=31,
        class_weight="balanced",
        objective="multiclass" if is_multiclass else "binary",
        random_state=42,
        n_jobs=-1,
    )
    if is_multiclass:
        model_kwargs["num_class"] = 3
    model = LGBMClassifier(**model_kwargs)
    model.fit(X_train, y_train)

    X_val = split.X_val[FEATURE_COLUMNS]
    y_val = split.y_val.astype(int)
    if calibrate and not is_multiclass:
        model, cal_method = fit_calibrated_classifier(model, X_val, y_val)
    else:
        cal_method = "none"
    best_threshold = None
    if not is_multiclass and hasattr(model, "predict_proba"):
        val_proba = model.predict_proba(X_val)[:, 1]
        best_threshold = _select_best_binary_threshold(y_val, val_proba, objective=optimize_for)

    artifact = {
        "model": model,
        "feature_columns": FEATURE_COLUMNS,
        "model_name": "lightgbm_multiclass" if is_multiclass else "lightgbm",
        "target_column": target_col,
        "target_type": "multiclass" if is_multiclass else "binary",
        "class_labels": [0, 1, 2] if is_multiclass else [0, 1],
        "best_threshold": best_threshold,
        "calibration": {"method": cal_method, "fit_on": "validation"},
    }

    model_out_path = Path(model_out_path)
    model_out_path.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(artifact, model_out_path)
    return model_out_path


def _select_best_binary_threshold(y_true, y_proba, objective: str = "f1") -> float:
    y = y_true.astype(int).to_numpy()
    thresholds = np.arange(0.05, 0.951, 0.01)
    best_t = 0.5
    best_score = -1.0
    for t in thresholds:
        yp = (y_proba >= t).astype(int)
        if objective == "recall":
            score = float(recall_score(y, yp, zero_division=0))
        else:
            score = float(f1_score(y, yp, zero_division=0))
        if score > best_score:
            best_score = score
            best_t = float(t)
    return best_t


def build_arg_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="Train baseline model with time-based split and save artifact.")
    p.add_argument("--features-path", type=str, default="data/processed/features.csv", help="Input features CSV")
    p.add_argument("--model-out", type=str, default="models/model.pkl", help="Output model artifact path")
    p.add_argument("--model-type", type=str, choices=["baseline", "lightgbm"], default="baseline")
    p.add_argument("--target-column", type=str, choices=["target", "target_multiclass"], default="target")
    p.add_argument("--optimize-threshold-for", type=str, choices=["f1", "recall"], default="f1")
    p.add_argument(
        "--no-calibration",
        action="store_true",
        help="Skip validation-set probability calibration (API will expose raw base estimator probabilities).",
    )
    return p


def main() -> int:
    args = build_arg_parser().parse_args()
    calibrate = not args.no_calibration
    if args.model_type == "lightgbm":
        out = train_lightgbm_model(
            features_path=args.features_path,
            model_out_path=args.model_out,
            calibrate=calibrate,
            target_col=args.target_column,
            optimize_for=args.optimize_threshold_for,
        )
    else:
        out = train_baseline_model(
            features_path=args.features_path,
            model_out_path=args.model_out,
            calibrate=calibrate,
            target_col=args.target_column,
            optimize_for=args.optimize_threshold_for,
        )
    print(f"Saved model artifact: {out.as_posix()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

