from __future__ import annotations

import argparse
from pathlib import Path

import joblib
import pandas as pd
from sklearn.linear_model import LogisticRegression
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
) -> Path:
    df = pd.read_csv(features_path, dtype={"site_id": "string"})
    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    df["target"] = pd.to_numeric(df["target"], errors="coerce")
    df = df.dropna(subset=["date", "target"]).sort_values(["site_id", "date"]).reset_index(drop=True)

    # Keep only required modeling columns
    keep_cols = ["site_id", "date"] + FEATURE_COLUMNS + ["target"]
    df = df[keep_cols].dropna()

    split = time_based_split(df, time_col="date", target_col="target", train_frac=0.70, val_frac=0.15)

    X_train = split.X_train[FEATURE_COLUMNS]
    y_train = split.y_train.astype(int)

    model = Pipeline(
        [
            ("scaler", StandardScaler()),
            (
                "clf",
                LogisticRegression(max_iter=5000, class_weight="balanced"),
            ),
        ]
    )
    model.fit(X_train, y_train)

    X_val = split.X_val[FEATURE_COLUMNS]
    y_val = split.y_val.astype(int)
    if calibrate:
        model, cal_method = fit_calibrated_classifier(model, X_val, y_val)
    else:
        cal_method = "none"

    artifact = {
        "model": model,
        "feature_columns": FEATURE_COLUMNS,
        "model_name": "logistic_baseline",
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
) -> Path:
    try:
        from lightgbm import LGBMClassifier
    except ImportError:
        raise ImportError("Install lightgbm: pip install lightgbm")

    df = pd.read_csv(features_path, dtype={"site_id": "string"})
    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    df["target"] = pd.to_numeric(df["target"], errors="coerce")
    df = df.dropna(subset=["date", "target"]).sort_values(["site_id", "date"]).reset_index(drop=True)

    keep_cols = ["site_id", "date"] + FEATURE_COLUMNS + ["target"]
    df = df[keep_cols].dropna()

    split = time_based_split(df, time_col="date", target_col="target", train_frac=0.70, val_frac=0.15)

    X_train = split.X_train[FEATURE_COLUMNS]
    y_train = split.y_train.astype(int)

    model = LGBMClassifier(
        n_estimators=300,
        learning_rate=0.05,
        num_leaves=31,
        class_weight="balanced",
        random_state=42,
        n_jobs=-1,
    )
    model.fit(X_train, y_train)

    X_val = split.X_val[FEATURE_COLUMNS]
    y_val = split.y_val.astype(int)
    if calibrate:
        model, cal_method = fit_calibrated_classifier(model, X_val, y_val)
    else:
        cal_method = "none"

    artifact = {
        "model": model,
        "feature_columns": FEATURE_COLUMNS,
        "model_name": "lightgbm",
        "calibration": {"method": cal_method, "fit_on": "validation"},
    }

    model_out_path = Path(model_out_path)
    model_out_path.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(artifact, model_out_path)
    return model_out_path


def build_arg_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="Train baseline model with time-based split and save artifact.")
    p.add_argument("--features-path", type=str, default="data/processed/features.csv", help="Input features CSV")
    p.add_argument("--model-out", type=str, default="models/model.pkl", help="Output model artifact path")
    p.add_argument("--model-type", type=str, choices=["baseline", "lightgbm"], default="baseline")
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
            features_path=args.features_path, model_out_path=args.model_out, calibrate=calibrate
        )
    else:
        out = train_baseline_model(
            features_path=args.features_path, model_out_path=args.model_out, calibrate=calibrate
        )
    print(f"Saved model artifact: {out.as_posix()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

