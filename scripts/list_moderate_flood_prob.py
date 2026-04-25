"""
List rows where P(multiclass high flood) is in [low_pct, high_pct] (default 30–70%).

Writes results/moderate_high_prob_30_70.csv and prints a per-river summary.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import joblib
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

# site_id in CSV is numeric (leading zeros dropped); normalize with zfill(8).
SITE_NAMES: dict[str, str] = {
    "01646500": "Potomac River at Point of Rocks, MD",
    "02087500": "Neuse River near Clayton, NC",
    "03015500": "Allegheny River at Eldred, PA",
    "03303000": "Ohio River at Louisville, KY",
    "05054000": "Red River of the North at Fargo, ND",
    "06710247": "Cherry Creek at Denver, CO",
    "07374000": "Mississippi River at Baton Rouge, LA",
    "08066500": "Trinity River at Romayor, TX",
    "11425500": "Sacramento River at Verona, CA",
    "12301933": "Clark Fork above Missoula, MT",
    "14211720": "Willamette River at Portland, OR",
}


def site_label(raw_id: float | int) -> tuple[str, str]:
    sid = str(int(raw_id)).zfill(8)
    return sid, SITE_NAMES.get(sid, sid)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--min-p", type=float, default=0.30, help="Min P(high), inclusive")
    parser.add_argument("--max-p", type=float, default=0.70, help="Max P(high), inclusive")
    parser.add_argument(
        "--out",
        type=Path,
        default=ROOT / "results" / "moderate_high_prob_30_70.csv",
    )
    args = parser.parse_args()

    df = pd.read_csv(ROOT / "data/processed/features.csv", parse_dates=["date"])
    df = df.dropna(subset=["target_multiclass"]).copy()
    df["target_multiclass"] = df["target_multiclass"].astype(int)

    artifact = joblib.load(ROOT / "models/lgbm_model.pkl")
    feat_cols = list(artifact["feature_columns"])
    model = artifact["model"]
    proba = model.predict_proba(df[feat_cols])
    classes = list(model.classes_)
    idx_high = classes.index(2) if 2 in classes else proba.shape[1] - 1
    p_high = proba[:, idx_high]

    out = df[["site_id", "date", "target_multiclass"]].copy()
    out["p_high_pct"] = (p_high * 100).round(2)
    out["pred_class"] = model.predict(df[feat_cols])
    mask = (p_high >= args.min_p) & (p_high <= args.max_p)
    out = out.loc[mask].sort_values(["site_id", "date"])

    sids, names = zip(*[site_label(x) for x in out["site_id"]], strict=True)
    out.insert(1, "site_id_str", sids)
    out.insert(2, "river", names)

    args.out.parent.mkdir(parents=True, exist_ok=True)
    out.to_csv(args.out, index=False)

    print(
        f"P(high flood class) between {args.min_p*100:.0f}% and {args.max_p*100:.0f}% "
        f"on rows with labels: {len(out)} day-rows across "
        f"{out['site_id_str'].nunique()} gauges.\n"
    )
    print("Days in band per river:\n")
    cnt = out.groupby("river", sort=False).size().sort_values(ascending=False)
    for river, n in cnt.items():
        print(f"  {n:4}  {river}")

    print(f"\nFull table saved to: {args.out}")


if __name__ == "__main__":
    main()
