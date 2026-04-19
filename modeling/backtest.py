"""
Forward-window stability: split the chronological test set into contiguous slices
and report metrics per slice (same trained model, no refit).

This answers whether test performance is stable over time or concentrated in a subset.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.metrics import roc_auc_score

from modeling.evaluate import _metrics
from modeling.features import FEATURE_COLUMNS
from modeling.utils import time_based_split


def forward_window_stability(
    *,
    features_path: str | Path = "data/processed/features.csv",
    model_path: str | Path = "models/lgbm_model.pkl",
    n_windows: int = 4,
    out_path: str | Path = "results/forward_window_stability.json",
) -> Path:
    df = pd.read_csv(features_path, dtype={"site_id": "string"})
    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    df["target"] = pd.to_numeric(df["target"], errors="coerce")
    df = df.dropna(subset=["date", "target"]).sort_values(["site_id", "date"]).reset_index(drop=True)

    artifact = joblib.load(model_path)
    model = artifact["model"]
    feature_cols = artifact.get("feature_columns", FEATURE_COLUMNS)

    split = time_based_split(df, time_col="date", target_col="target", train_frac=0.70, val_frac=0.15)

    Xt = split.X_test.copy()
    mask = Xt[list(feature_cols)].notna().all(axis=1)
    Xt = Xt.loc[mask]
    y_test = split.y_test.loc[Xt.index].astype(int)

    sub = Xt[list(feature_cols) + ["date"]].copy()
    sub["target"] = y_test.to_numpy()
    sub = sub.sort_values("date").reset_index(drop=True)
    y = sub["target"].astype(int).to_numpy()
    X = sub[list(feature_cols)]

    n = len(sub)
    if n < n_windows:
        raise ValueError(f"Test set too small ({n} rows) for {n_windows} windows.")

    edges = np.linspace(0, n, num=n_windows + 1, dtype=int)
    windows: list[dict[str, object]] = []

    for i in range(n_windows):
        lo, hi = int(edges[i]), int(edges[i + 1])
        if lo >= hi:
            continue
        X_w = X.iloc[lo:hi]
        y_w = y[lo:hi]
        y_pred = model.predict(X_w)
        m = _metrics(y_w, y_pred)
        chunk: dict[str, object] = {
            "window_index": i,
            "n_rows": int(hi - lo),
            "date_start": sub["date"].iloc[lo].strftime("%Y-%m-%d"),
            "date_end": sub["date"].iloc[hi - 1].strftime("%Y-%m-%d"),
            "metrics": m,
        }
        try:
            if hasattr(model, "predict_proba"):
                proba = model.predict_proba(X_w)[:, 1]
                chunk["test_roc_auc"] = float(roc_auc_score(y_w, proba))
        except Exception:
            pass
        windows.append(chunk)

    report = {
        "model_path": str(model_path),
        "n_windows": n_windows,
        "n_test_rows_used": n,
        "windows": windows,
    }

    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    return out_path


def build_arg_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="Test-set forward-window metric stability (no retraining).")
    p.add_argument("--features-path", type=str, default="data/processed/features.csv")
    p.add_argument("--model-path", type=str, default="models/lgbm_model.pkl")
    p.add_argument("--n-windows", type=int, default=4)
    p.add_argument("--out-path", type=str, default="results/forward_window_stability.json")
    return p


def main() -> int:
    args = build_arg_parser().parse_args()
    out = forward_window_stability(
        features_path=args.features_path,
        model_path=args.model_path,
        n_windows=args.n_windows,
        out_path=args.out_path,
    )
    print(f"Wrote {out.as_posix()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
