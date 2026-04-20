from __future__ import annotations

import argparse
from pathlib import Path

import joblib
import pandas as pd
from sklearn.ensemble import RandomForestRegressor
from sklearn.linear_model import LinearRegression
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

from modeling.stage_features import STAGE_FEATURE_COLUMNS
from modeling.utils import time_based_split


def train_stage_model(
    *,
    features_path: str | Path = "data/processed/stage_features.csv",
    model_out_path: str | Path = "models/stage_model.pkl",
    model_type: str = "baseline",
) -> Path:
    df = pd.read_csv(features_path, dtype={"site_id": "string"})
    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    df["stage_next_day"] = pd.to_numeric(df["stage_next_day"], errors="coerce")
    df = df.dropna(subset=["date", "stage_next_day"]).sort_values(["site_id", "date"]).reset_index(drop=True)
    df = df[["site_id", "date"] + STAGE_FEATURE_COLUMNS + ["stage_next_day"]].dropna()

    split = time_based_split(df, time_col="date", target_col="stage_next_day", train_frac=0.70, val_frac=0.15)
    X_train = split.X_train[STAGE_FEATURE_COLUMNS]
    y_train = split.y_train.astype(float)

    if model_type == "strong":
        model = RandomForestRegressor(
            n_estimators=300,
            max_depth=12,
            min_samples_leaf=3,
            random_state=42,
            n_jobs=-1,
        )
        model_name = "stage_random_forest"
    else:
        model = Pipeline([("scaler", StandardScaler()), ("reg", LinearRegression())])
        model_name = "stage_linear_baseline"

    model.fit(X_train, y_train)
    artifact = {
        "model": model,
        "feature_columns": STAGE_FEATURE_COLUMNS,
        "model_name": model_name,
        "target_name": "stage_next_day",
    }

    model_out_path = Path(model_out_path)
    model_out_path.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(artifact, model_out_path)
    return model_out_path


def build_arg_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="Train stage prediction regression model.")
    p.add_argument("--features-path", type=str, default="data/processed/stage_features.csv")
    p.add_argument("--model-out", type=str, default="models/stage_model.pkl")
    p.add_argument("--model-type", choices=["baseline", "strong"], default="strong")
    return p


def main() -> int:
    args = build_arg_parser().parse_args()
    out = train_stage_model(features_path=args.features_path, model_out_path=args.model_out, model_type=args.model_type)
    print(f"Saved stage model artifact: {out.as_posix()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
