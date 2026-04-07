from __future__ import annotations

from dataclasses import dataclass

import pandas as pd


@dataclass(frozen=True)
class SplitData:
    X_train: pd.DataFrame
    y_train: pd.Series
    X_val: pd.DataFrame
    y_val: pd.Series
    X_test: pd.DataFrame
    y_test: pd.Series


def time_based_split(
    df: pd.DataFrame,
    *,
    time_col: str = "date",
    target_col: str = "target",
    train_frac: float = 0.70,
    val_frac: float = 0.15,
) -> SplitData:
    """
    Time-based split (no shuffle), using chronological order of `time_col`.
    Splits by row order after sorting by time_col (and site_id if present).
    """
    if not 0 < train_frac < 1:
        raise ValueError("train_frac must be in (0, 1)")
    if not 0 < val_frac < 1:
        raise ValueError("val_frac must be in (0, 1)")
    if train_frac + val_frac >= 1:
        raise ValueError("train_frac + val_frac must be < 1")

    sort_cols = [time_col] + (["site_id"] if "site_id" in df.columns and "site_id" != time_col else [])
    sdf = df.sort_values(sort_cols).reset_index(drop=True)

    n = len(sdf)
    if n < 10:
        # Still proceed, but warn upstream by allowing tiny splits.
        pass

    train_end = int(n * train_frac)
    val_end = int(n * (train_frac + val_frac))

    train = sdf.iloc[:train_end]
    val = sdf.iloc[train_end:val_end]
    test = sdf.iloc[val_end:]

    X_train = train.drop(columns=[target_col])
    y_train = train[target_col]
    X_val = val.drop(columns=[target_col])
    y_val = val[target_col]
    X_test = test.drop(columns=[target_col])
    y_test = test[target_col]

    return SplitData(X_train, y_train, X_val, y_val, X_test, y_test)

