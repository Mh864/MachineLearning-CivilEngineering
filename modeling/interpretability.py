"""
Export coefficient / feature-importance tables for trained artifacts.

- Logistic baseline: standardized linear coefficients (Pipeline with StandardScaler + LogisticRegression).
- LightGBM: `feature_importances_` (gain-based split counts in sklearn API).
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import joblib
import numpy as np

from modeling.calibration import unwrap_calibrated_estimator
from modeling.features import FEATURE_COLUMNS


def _logistic_coefficients(model: Any, feature_cols: list[str]) -> list[dict[str, float]]:
    if hasattr(model, "named_steps") and "clf" in model.named_steps:
        coef = np.asarray(model.named_steps["clf"].coef_).ravel()
    elif hasattr(model, "coef_"):
        coef = np.asarray(model.coef_).ravel()
    else:
        raise TypeError("Expected sklearn LogisticRegression or Pipeline ending in LogisticRegression.")

    if len(coef) != len(feature_cols):
        raise ValueError(f"Coefficient length {len(coef)} != n_features {len(feature_cols)}")

    out = [{"feature": c, "coefficient": float(w)} for c, w in zip(feature_cols, coef, strict=True)]
    out.sort(key=lambda r: abs(r["coefficient"]), reverse=True)
    return out


def _lgbm_importance(model: Any, feature_cols: list[str]) -> list[dict[str, float]]:
    if not hasattr(model, "feature_importances_"):
        raise TypeError("Expected an estimator with feature_importances_ (e.g. LGBMClassifier).")
    imp = np.asarray(model.feature_importances_, dtype=float)
    out = [{"feature": c, "importance": float(v)} for c, v in zip(feature_cols, imp, strict=True)]
    out.sort(key=lambda r: r["importance"], reverse=True)
    return out


def export_interpretability(
    *,
    logistic_path: str | Path | None = "models/model.pkl",
    lgbm_path: str | Path | None = "models/lgbm_model.pkl",
    out_dir: str | Path = "results",
) -> dict[str, Path]:
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    written: dict[str, Path] = {}

    if logistic_path and Path(logistic_path).is_file():
        art = joblib.load(logistic_path)
        cols = list(art.get("feature_columns", FEATURE_COLUMNS))
        rows = _logistic_coefficients(unwrap_calibrated_estimator(art["model"]), cols)
        path = out_dir / "logistic_coefficients.json"
        payload = {
            "model_path": str(logistic_path),
            "model_name": art.get("model_name", "logistic"),
            "coefficients_sorted_by_abs": rows,
        }
        path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        written["logistic"] = path

    if lgbm_path and Path(lgbm_path).is_file():
        art = joblib.load(lgbm_path)
        cols = list(art.get("feature_columns", FEATURE_COLUMNS))
        rows = _lgbm_importance(unwrap_calibrated_estimator(art["model"]), cols)
        path = out_dir / "lgbm_feature_importance.json"
        payload = {
            "model_path": str(lgbm_path),
            "model_name": art.get("model_name", "lightgbm"),
            "feature_importance_sorted": rows,
        }
        path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        written["lightgbm"] = path

    if not written:
        raise FileNotFoundError("No model artifacts found; train models first or pass valid paths.")

    return written


def build_arg_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="Export logistic coefficients and LightGBM feature importance JSON.")
    p.add_argument("--logistic-path", type=str, default="models/model.pkl")
    p.add_argument("--lgbm-path", type=str, default="models/lgbm_model.pkl")
    p.add_argument("--out-dir", type=str, default="results")
    p.add_argument("--skip-logistic", action="store_true")
    p.add_argument("--skip-lgbm", action="store_true")
    return p


def main() -> int:
    args = build_arg_parser().parse_args()
    written = export_interpretability(
        logistic_path=None if args.skip_logistic else args.logistic_path,
        lgbm_path=None if args.skip_lgbm else args.lgbm_path,
        out_dir=args.out_dir,
    )
    for k, p in written.items():
        print(f"{k}: {p.as_posix()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
