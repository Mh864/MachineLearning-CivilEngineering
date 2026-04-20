from __future__ import annotations

import argparse
import json
from pathlib import Path

import joblib
import pandas as pd
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score

from modeling.stage_features import STAGE_FEATURE_COLUMNS
from modeling.utils import time_based_split


def _reg_metrics(y_true: pd.Series, y_pred) -> dict[str, float]:
    mse = float(mean_squared_error(y_true, y_pred))
    return {
        "mae": float(mean_absolute_error(y_true, y_pred)),
        "rmse": float(mse ** 0.5),
        "r2": float(r2_score(y_true, y_pred)),
    }


def evaluate_stage_model(
    *,
    features_path: str | Path = "data/processed/stage_features.csv",
    model_path: str | Path = "models/stage_model.pkl",
    out_path: str | Path = "results/stage_metrics.json",
) -> Path:
    artifact = joblib.load(model_path)
    model = artifact["model"]
    feature_cols = artifact.get("feature_columns", STAGE_FEATURE_COLUMNS)

    df = pd.read_csv(features_path, dtype={"site_id": "string"})
    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    df["stage_next_day"] = pd.to_numeric(df["stage_next_day"], errors="coerce")
    df = df.dropna(subset=["date", "stage_next_day"]).sort_values(["site_id", "date"]).reset_index(drop=True)
    df = df[["site_id", "date"] + list(feature_cols) + ["stage_next_day"]].dropna()

    split = time_based_split(df, time_col="date", target_col="stage_next_day", train_frac=0.70, val_frac=0.15)
    X_val = split.X_val[list(feature_cols)]
    X_test = split.X_test[list(feature_cols)]
    y_val = split.y_val.astype(float)
    y_test = split.y_test.astype(float)

    val_pred = model.predict(X_val)
    test_pred = model.predict(X_test)

    per_site_test: dict[str, dict[str, float]] = {}
    if "site_id" in split.X_test.columns:
        for site_id in sorted(split.X_test["site_id"].astype(str).unique()):
            m = split.X_test["site_id"].astype(str) == site_id
            Xs = split.X_test.loc[m, list(feature_cols)]
            ys = y_test.loc[m]
            if len(ys) < 2:
                continue
            ps = model.predict(Xs)
            per_site_test[str(site_id)] = {"n": int(len(ys)), **_reg_metrics(ys, ps)}

    report = {
        "model_name": artifact.get("model_name"),
        "target_name": artifact.get("target_name", "stage_next_day"),
        "validation": _reg_metrics(y_val, val_pred),
        "test": _reg_metrics(y_test, test_pred),
        "per_site_test": per_site_test,
        "n_rows": int(len(df)),
        "n_train": int(len(split.X_train)),
        "n_val": int(len(split.X_val)),
        "n_test": int(len(split.X_test)),
    }

    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print("Validation stage metrics:", json.dumps(report["validation"], indent=2))
    print("Test stage metrics:", json.dumps(report["test"], indent=2))
    return out_path


def build_arg_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="Evaluate stage regression model.")
    p.add_argument("--features-path", type=str, default="data/processed/stage_features.csv")
    p.add_argument("--model-path", type=str, default="models/stage_model.pkl")
    p.add_argument("--out-path", type=str, default="results/stage_metrics.json")
    return p


def main() -> int:
    args = build_arg_parser().parse_args()
    out = evaluate_stage_model(features_path=args.features_path, model_path=args.model_path, out_path=args.out_path)
    print(f"Wrote stage metrics: {out.as_posix()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
