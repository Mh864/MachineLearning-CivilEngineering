"""
Post-hoc probability calibration on the validation split (no extra training data leakage into
the base estimator: the base model is fit only on train; calibration uses val predictions).

- **sklearn >= 1.6:** `CalibratedClassifierCV(FrozenEstimator(base), method=...)` (replaces
  deprecated `cv="prefit"`).
- **Older sklearn:** falls back to `CalibratedClassifierCV(..., cv="prefit")` when available.

Tries isotonic first, then Platt scaling (sigmoid); if both fail or y_val has a single class,
returns the base estimator unchanged.
"""
from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd
from sklearn.calibration import CalibratedClassifierCV


def _calibrate_with_frozen(base_estimator: Any, X_val: pd.DataFrame, y_val: pd.Series, method: str) -> Any:
    from sklearn.frozen import FrozenEstimator

    cal = CalibratedClassifierCV(FrozenEstimator(base_estimator), method=method)
    cal.fit(X_val, y_val)
    return cal


def _calibrate_prefit(base_estimator: Any, X_val: pd.DataFrame, y_val: pd.Series, method: str) -> Any:
    cal = CalibratedClassifierCV(base_estimator, method=method, cv="prefit")
    cal.fit(X_val, y_val)
    return cal


def fit_calibrated_classifier(
    base_estimator: Any,
    X_val: pd.DataFrame,
    y_val: pd.Series,
) -> tuple[Any, str]:
    """
    Wrap `base_estimator` with validation-time calibration when possible.

    Returns (estimator_to_save, method) where method is 'isotonic', 'sigmoid', or 'none'.
    """
    yv = y_val.astype(int).to_numpy()
    if len(np.unique(yv)) < 2:
        return base_estimator, "none"

    for method in ("isotonic", "sigmoid"):
        try:
            try:
                cal = _calibrate_with_frozen(base_estimator, X_val, y_val, method)
            except Exception:
                cal = _calibrate_prefit(base_estimator, X_val, y_val, method)
            return cal, method
        except Exception:
            continue

    return base_estimator, "none"


def unwrap_calibrated_estimator(model: Any) -> Any:
    """
    Return the underlying fitted classifier (Pipeline / LGBM) for interpretability exports.
    If `model` is not a CalibratedClassifierCV, returns `model` unchanged.
    """
    cal = getattr(model, "calibrated_classifiers_", None)
    if not cal or len(cal) == 0:
        return model
    inner = getattr(cal[0], "estimator", None)
    if inner is None:
        return model
    try:
        from sklearn.frozen import FrozenEstimator
    except ImportError:
        FrozenEstimator = ()  # type: ignore[misc, assignment]

    if isinstance(inner, FrozenEstimator):
        return inner.estimator
    return inner
