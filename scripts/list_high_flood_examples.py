"""Print locations/dates with highest P(high flood) on time-based test split."""
from __future__ import annotations

import sys
from pathlib import Path

import joblib
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from modeling.utils import time_based_split

SITE_NAMES = {
    "01646500": "Potomac (DC)",
    "02087500": "Neuse (NC)",
    "03015500": "Allegheny (PA)",
    "05054000": "Red River (ND)",
    "06710247": "Cherry Creek (CO)",
    "08066500": "Trinity (TX)",
    "09380000": "Colorado (AZ)",
    "11425500": "Sacramento (CA)",
    "12301933": "Clark Fork (MT)",
    "14211720": "Willamette (OR)",
}


def main() -> None:
    df = pd.read_csv(ROOT / "data/processed/features.csv", parse_dates=["date"])
    df = df.dropna(subset=["target_multiclass"]).copy()
    df["target_multiclass"] = df["target_multiclass"].astype(int)

    artifact = joblib.load(ROOT / "models/lgbm_model.pkl")
    feat_cols = list(artifact["feature_columns"])
    split = time_based_split(df, time_col="date", target_col="target_multiclass")
    X_test = split.X_test[feat_cols]
    model = artifact["model"]
    proba = model.predict_proba(X_test)
    classes = list(model.classes_)
    idx_high = classes.index(2) if 2 in classes else proba.shape[1] - 1
    p_high = proba[:, idx_high]

    meta = split.X_test[["site_id", "date"]].copy()
    meta["p_high"] = p_high
    meta["pred"] = model.predict(X_test)
    meta["y_true"] = split.y_test.values

    print("Top 15 test rows by P(high flood class=2):\n")
    for _, r in meta.nlargest(15, "p_high").iterrows():
        sid = str(int(r["site_id"])).zfill(8)
        name = SITE_NAMES.get(sid, sid)
        d = pd.Timestamp(r["date"]).strftime("%Y-%m-%d")
        print(
            f"  {name:22}  {d}   P(high)={r['p_high']:.3f}   "
            f"pred={int(r['pred'])}   actual={int(r['y_true'])}"
        )

    print("\nTop 10 where model predicts class 2 (high), by P(high):\n")
    pred2 = meta[meta["pred"] == 2].nlargest(10, "p_high")
    for _, r in pred2.iterrows():
        sid = str(int(r["site_id"])).zfill(8)
        name = SITE_NAMES.get(sid, sid)
        d = pd.Timestamp(r["date"]).strftime("%Y-%m-%d")
        print(
            f"  {name:22}  {d}   P(high)={r['p_high']:.3f}   actual={int(r['y_true'])}"
        )


if __name__ == "__main__":
    main()
