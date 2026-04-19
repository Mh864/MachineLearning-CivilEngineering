from __future__ import annotations

import argparse
import json
from pathlib import Path

import joblib
import pandas as pd
from sklearn.metrics import accuracy_score, f1_score, precision_score, recall_score, roc_auc_score

from modeling.features import FEATURE_COLUMNS
from modeling.utils import time_based_split


def _metrics(y_true, y_pred) -> dict[str, float]:
    return {
        "accuracy": float(accuracy_score(y_true, y_pred)),
        "precision": float(precision_score(y_true, y_pred, zero_division=0)),
        "recall": float(recall_score(y_true, y_pred, zero_division=0)),
        "f1": float(f1_score(y_true, y_pred, zero_division=0)),
    }


def evaluate_model(
    *,
    features_path: str | Path = "data/processed/features.csv",
    model_path: str | Path = "models/model.pkl",
    metrics_out_path: str | Path = "results/metrics.json",
) -> Path:
    artifact = joblib.load(model_path)
    model = artifact["model"]
    feature_cols = artifact.get("feature_columns", FEATURE_COLUMNS)

    df = pd.read_csv(features_path, dtype={"site_id": "string"})
    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    df["target"] = pd.to_numeric(df["target"], errors="coerce")
    df = df.dropna(subset=["date", "target"]).sort_values(["site_id", "date"]).reset_index(drop=True)
    df = df[["site_id", "date"] + list(feature_cols) + ["target"]].dropna()

    split = time_based_split(df, time_col="date", target_col="target", train_frac=0.70, val_frac=0.15)

    def predict(X: pd.DataFrame):
        return model.predict(X[list(feature_cols)])

    y_val_true = split.y_val.astype(int)
    y_test_true = split.y_test.astype(int)
    y_val_pred = predict(split.X_val)
    y_test_pred = predict(split.X_test)

    metrics = {
        "validation": _metrics(y_val_true, y_val_pred),
        "test": _metrics(y_test_true, y_test_pred),
        "n_rows": int(len(df)),
        "n_train": int(len(split.X_train)),
        "n_val": int(len(split.X_val)),
        "n_test": int(len(split.X_test)),
    }

    print("Validation metrics:", json.dumps(metrics["validation"], indent=2))
    print("Test metrics:", json.dumps(metrics["test"], indent=2))

    metrics_out_path = Path(metrics_out_path)
    metrics_out_path.parent.mkdir(parents=True, exist_ok=True)
    metrics_out_path.write_text(json.dumps(metrics, indent=2), encoding="utf-8")
    return metrics_out_path


def compare_models(
    *,
    features_path: str | Path = "data/processed/features.csv",
    model_paths: list[str | Path],
    out_path: str | Path = "results/comparison.json",
) -> Path:
    df = pd.read_csv(features_path, dtype={"site_id": "string"})
    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    df["target"] = pd.to_numeric(df["target"], errors="coerce")
    df = df.dropna(subset=["date", "target"]).sort_values(["site_id", "date"]).reset_index(drop=True)

    split = time_based_split(df, time_col="date", target_col="target", train_frac=0.70, val_frac=0.15)
    y_val_true = split.y_val.astype(int)
    y_test_true = split.y_test.astype(int)

    results: dict[str, dict[str, object]] = {}
    best_f1_name: str | None = None
    best_f1_val = -1.0
    best_auc_name: str | None = None
    best_auc_val = -1.0
    rows: list[tuple[str, float, float, float | None]] = []

    for model_path in model_paths:
        artifact = joblib.load(model_path)
        model = artifact["model"]
        feature_cols = artifact.get("feature_columns", FEATURE_COLUMNS)
        model_name = str(artifact.get("model_name", Path(model_path).stem))

        X_val = split.X_val[list(feature_cols)].dropna()
        y_val = y_val_true.loc[X_val.index]
        X_test = split.X_test[list(feature_cols)].dropna()
        y_test = y_test_true.loc[X_test.index]

        y_val_pred = model.predict(X_val)
        y_test_pred = model.predict(X_test)
        val_metrics = _metrics(y_val, y_val_pred)
        test_metrics = _metrics(y_test, y_test_pred)

        test_roc_auc: float | None = None
        try:
            if hasattr(model, "predict_proba"):
                y_test_proba = model.predict_proba(X_test)[:, 1]
                test_roc_auc = float(roc_auc_score(y_test, y_test_proba))
        except Exception:
            test_roc_auc = None

        results[model_name] = {
            "validation": val_metrics,
            "test": test_metrics,
            "test_roc_auc": test_roc_auc,
        }
        rows.append((model_name, val_metrics["f1"], test_metrics["f1"], test_roc_auc))

        if test_metrics["f1"] > best_f1_val:
            best_f1_val = test_metrics["f1"]
            best_f1_name = model_name
        if test_roc_auc is not None and test_roc_auc > best_auc_val:
            best_auc_val = test_roc_auc
            best_auc_name = model_name

    results["summary"] = {
        "best_model_by_test_f1": best_f1_name,
        "best_model_by_test_roc_auc": best_auc_name,
        "n_rows": int(len(df)),
        "n_train": int(len(split.X_train)),
        "n_val": int(len(split.X_val)),
        "n_test": int(len(split.X_test)),
    }

    print(f"{'Model':<20} {'Val F1':>10} {'Test F1':>10} {'Test ROC-AUC':>14}")
    print("-" * 58)
    for model_name, val_f1, test_f1, test_auc in rows:
        auc_txt = f"{test_auc:.4f}" if test_auc is not None else "n/a"
        print(f"{model_name:<20} {val_f1:>10.4f} {test_f1:>10.4f} {auc_txt:>14}")

    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(results, indent=2), encoding="utf-8")
    return out_path


def evaluate_naive_baselines(
    *,
    features_path: str | Path = "data/processed/features.csv",
    out_path: str | Path = "results/naive_baselines.json",
) -> Path:
    """
    Non-ML baselines on the same chronological split as `compare_models`:
    - persistence: y_hat(t) = y(t-1) within each site (previous calendar row for that gauge)
    - majority: always predict the training-set majority class
    """
    df = pd.read_csv(features_path, dtype={"site_id": "string"})
    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    df["target"] = pd.to_numeric(df["target"], errors="coerce")
    df = df.dropna(subset=["date", "target"]).sort_values(["site_id", "date"]).reset_index(drop=True)

    df = df.sort_values(["date", "site_id"]).reset_index(drop=True)
    df["target_persist"] = df.groupby("site_id")["target"].shift(1)

    split = time_based_split(
        df.drop(columns=["target_persist"]),
        time_col="date",
        target_col="target",
        train_frac=0.70,
        val_frac=0.15,
    )

    maj = int(split.y_train.astype(int).mode().iloc[0])

    def _persist(y_true: pd.Series, idx: pd.Index) -> dict[str, float] | None:
        persist = df.loc[idx, "target_persist"]
        m = persist.notna()
        if int(m.sum()) == 0:
            return None
        return _metrics(y_true[m].astype(int), persist[m].astype(int))

    val_maj = _metrics(
        split.y_val.astype(int),
        pd.Series([maj] * len(split.y_val), index=split.y_val.index),
    )
    test_maj = _metrics(
        split.y_test.astype(int),
        pd.Series([maj] * len(split.y_test), index=split.y_test.index),
    )

    results = {
        "train_majority_class": maj,
        "split": {"train_frac": 0.70, "val_frac": 0.15},
        "descriptions": {
            "persistence": (
                "Predict today's class using yesterday's realized label for the same USGS site "
                "(aligned to the same time-ordered rows as time_based_split)."
            ),
            "majority": "Always predict the majority class observed on the training slice.",
        },
        "validation": {
            "persistence": _persist(split.y_val, split.X_val.index),
            "majority_class": val_maj,
        },
        "test": {
            "persistence": _persist(split.y_test, split.X_test.index),
            "majority_class": test_maj,
        },
        "n_train": int(len(split.X_train)),
        "n_val": int(len(split.X_val)),
        "n_test": int(len(split.X_test)),
    }

    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(results, indent=2), encoding="utf-8")
    return out_path


def build_arg_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="Evaluate model on validation and test splits; save metrics.json.")
    p.add_argument("--features-path", type=str, default="data/processed/features.csv")
    p.add_argument("--model-path", type=str, default="models/model.pkl")
    p.add_argument("--out-path", type=str, default="results/metrics.json")
    p.add_argument("--compare", action="store_true")
    p.add_argument(
        "--model-paths",
        nargs="+",
        help="Two or more .pkl artifacts to compare. If omitted with --compare, uses models/model.pkl and models/lgbm_model.pkl when both exist.",
    )
    p.add_argument(
        "--naive-baselines",
        action="store_true",
        help="Only compute persistence + majority baselines; writes separate JSON (default results/naive_baselines.json).",
    )
    return p


def main() -> int:
    args = build_arg_parser().parse_args()
    if args.naive_baselines:
        out_path = args.out_path
        if out_path == "results/metrics.json":
            out_path = "results/naive_baselines.json"
        out = evaluate_naive_baselines(features_path=args.features_path, out_path=out_path)
        print(f"Wrote naive baselines: {out.as_posix()}")
        return 0
    if args.compare:
        if args.model_paths:
            model_paths = list(args.model_paths)
            for p in model_paths:
                if not Path(p).is_file():
                    raise FileNotFoundError(f"Model artifact not found: {p}")
        else:
            default_paths = ["models/model.pkl", "models/lgbm_model.pkl"]
            model_paths = [p for p in default_paths if Path(p).is_file()]
            if len(model_paths) < 2:
                raise FileNotFoundError(
                    "Compare mode needs at least two trained artifacts. Either train both models first "
                    f"(expected {default_paths}) or pass explicit paths, e.g.\n"
                    '  python -m modeling.evaluate --compare --model-paths models/model.pkl models/lgbm_model.pkl'
                )
        if args.out_path == "results/metrics.json":
            args.out_path = "results/comparison.json"
        out = compare_models(
            features_path=args.features_path, model_paths=model_paths, out_path=args.out_path
        )
        print(f"Wrote comparison: {out.as_posix()}")
    else:
        out = evaluate_model(features_path=args.features_path, model_path=args.model_path, metrics_out_path=args.out_path)
        print(f"Wrote metrics: {out.as_posix()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

