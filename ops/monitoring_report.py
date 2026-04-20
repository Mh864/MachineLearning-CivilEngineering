from __future__ import annotations

import argparse
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CONFIG_PATH = ROOT / "ops" / "monitoring_config.json"
DEFAULT_OUT_JSON = ROOT / "results" / "monitoring_report.json"
DEFAULT_OUT_MD = ROOT / "results" / "monitoring_report.md"


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _psi(reference: pd.Series, recent: pd.Series, bins: int = 10) -> float:
    ref = pd.to_numeric(reference, errors="coerce").dropna()
    rec = pd.to_numeric(recent, errors="coerce").dropna()
    if ref.empty or rec.empty:
        return 0.0
    quantiles = np.linspace(0, 1, bins + 1)
    edges = np.quantile(ref, quantiles)
    edges = np.unique(edges)
    if len(edges) <= 2:
        return 0.0
    ref_hist, _ = np.histogram(ref, bins=edges)
    rec_hist, _ = np.histogram(rec, bins=edges)
    ref_pct = ref_hist / max(ref_hist.sum(), 1)
    rec_pct = rec_hist / max(rec_hist.sum(), 1)
    eps = 1e-6
    ref_pct = np.clip(ref_pct, eps, None)
    rec_pct = np.clip(rec_pct, eps, None)
    return float(np.sum((rec_pct - ref_pct) * np.log(rec_pct / ref_pct)))


def _split_recent_reference(df: pd.DataFrame, date_col: str, recent_days: int, reference_days: int) -> tuple[pd.DataFrame, pd.DataFrame]:
    if df.empty:
        return df.copy(), df.copy()
    dmax = pd.to_datetime(df[date_col], errors="coerce").max()
    if pd.isna(dmax):
        return df.iloc[0:0].copy(), df.iloc[0:0].copy()
    recent_start = dmax - timedelta(days=recent_days - 1)
    ref_end = recent_start - timedelta(days=1)
    ref_start = ref_end - timedelta(days=reference_days - 1)
    d = pd.to_datetime(df[date_col], errors="coerce")
    recent = df[(d >= recent_start) & (d <= dmax)].copy()
    reference = df[(d >= ref_start) & (d <= ref_end)].copy()
    return recent, reference


def _build_missingness_section(clean_df: pd.DataFrame, config: dict[str, Any]) -> dict[str, Any]:
    recent_days = int(config["recent_window_days"])
    reference_days = int(config["reference_window_days"])
    threshold_pp = float(config["missingness_alert_increase_pp"])
    columns = list(config["missingness_columns"])

    recent, reference = _split_recent_reference(clean_df, "date", recent_days, reference_days)
    per_col: dict[str, Any] = {}
    alerts: list[dict[str, Any]] = []

    for col in columns:
        if col not in clean_df.columns:
            continue
        recent_missing = float(recent[col].isna().mean() * 100) if len(recent) else 0.0
        ref_missing = float(reference[col].isna().mean() * 100) if len(reference) else 0.0
        delta = recent_missing - ref_missing
        rec = {
            "recent_missing_pct": round(recent_missing, 3),
            "reference_missing_pct": round(ref_missing, 3),
            "delta_pp": round(delta, 3),
        }
        per_col[col] = rec
        if delta > threshold_pp:
            alerts.append({"type": "missingness", "column": col, **rec})

    return {
        "recent_rows": int(len(recent)),
        "reference_rows": int(len(reference)),
        "threshold_increase_pp": threshold_pp,
        "columns": per_col,
        "alerts": alerts,
    }


def _build_drift_section(features_df: pd.DataFrame, config: dict[str, Any]) -> dict[str, Any]:
    recent_days = int(config["recent_window_days"])
    reference_days = int(config["reference_window_days"])
    psi_threshold = float(config["psi_alert_threshold"])
    columns = list(config["feature_drift_columns"])

    recent, reference = _split_recent_reference(features_df, "date", recent_days, reference_days)
    per_col: dict[str, Any] = {}
    alerts: list[dict[str, Any]] = []

    for col in columns:
        if col not in features_df.columns:
            continue
        score = _psi(reference[col], recent[col])
        rec = {"psi": round(score, 4), "threshold": psi_threshold}
        per_col[col] = rec
        if score > psi_threshold:
            alerts.append({"type": "drift", "column": col, **rec})

    return {
        "recent_rows": int(len(recent)),
        "reference_rows": int(len(reference)),
        "psi_threshold": psi_threshold,
        "columns": per_col,
        "alerts": alerts,
    }


def _build_performance_section(config: dict[str, Any], results_dir: Path) -> dict[str, Any]:
    f1_drop_threshold = float(config["performance_drop_f1_threshold"])
    brier_up_threshold = float(config["performance_brier_increase_threshold"])
    alerts: list[dict[str, Any]] = []
    section: dict[str, Any] = {
        "threshold_f1_drop": f1_drop_threshold,
        "threshold_brier_increase": brier_up_threshold,
    }

    comparison_path = results_dir / "comparison.json"
    if comparison_path.exists():
        comp = _load_json(comparison_path)
        model_name = comp.get("summary", {}).get("best_model_by_test_f1")
        model_blob = comp.get(model_name or "", {})
        test_f1 = model_blob.get("test", {}).get("f1")
        val_f1 = model_blob.get("validation", {}).get("f1")
        test_brier = model_blob.get("test_brier")
        section["comparison_snapshot"] = {
            "best_model_by_test_f1": model_name,
            "validation_f1": val_f1,
            "test_f1": test_f1,
            "test_brier": test_brier,
        }

    fws_path = results_dir / "forward_window_stability.json"
    if fws_path.exists():
        fws = _load_json(fws_path)
        windows = fws.get("windows", [])
        f1s = [w.get("metrics", {}).get("f1") for w in windows]
        f1s = [x for x in f1s if isinstance(x, (int, float))]
        if len(f1s) >= 2:
            early = float(np.mean(f1s[: max(1, len(f1s) // 2)]))
            late = float(np.mean(f1s[len(f1s) // 2 :]))
            delta = late - early
            section["forward_window_f1"] = {
                "early_avg_f1": round(early, 4),
                "late_avg_f1": round(late, 4),
                "delta": round(delta, 4),
            }
            if (early - late) > f1_drop_threshold:
                alerts.append(
                    {
                        "type": "performance_f1_drop",
                        "early_avg_f1": round(early, 4),
                        "late_avg_f1": round(late, 4),
                        "drop": round(early - late, 4),
                    }
                )

    if "comparison_snapshot" in section:
        val_f1 = section["comparison_snapshot"].get("validation_f1")
        test_f1 = section["comparison_snapshot"].get("test_f1")
        test_brier = section["comparison_snapshot"].get("test_brier")
        if isinstance(val_f1, (int, float)) and isinstance(test_f1, (int, float)):
            if (val_f1 - test_f1) > f1_drop_threshold:
                alerts.append(
                    {
                        "type": "performance_validation_to_test_drop",
                        "validation_f1": round(float(val_f1), 4),
                        "test_f1": round(float(test_f1), 4),
                        "drop": round(float(val_f1) - float(test_f1), 4),
                    }
                )
        if isinstance(test_brier, (int, float)) and test_brier > brier_up_threshold:
            alerts.append(
                {
                    "type": "performance_brier_high",
                    "test_brier": round(float(test_brier), 4),
                    "threshold": brier_up_threshold,
                }
            )

    section["alerts"] = alerts
    return section


def _to_markdown(report: dict[str, Any]) -> str:
    lines: list[str] = []
    lines.append("# Monitoring Report")
    lines.append("")
    lines.append(f"- Generated at (UTC): `{report['generated_at_utc']}`")
    lines.append(f"- Overall status: `{report['status']}`")
    lines.append(f"- Total alerts: `{len(report['alerts'])}`")
    lines.append("")

    lines.append("## Missingness")
    lines.append("")
    missing = report["missingness"]
    lines.append(f"- Recent rows: `{missing['recent_rows']}`")
    lines.append(f"- Reference rows: `{missing['reference_rows']}`")
    lines.append(f"- Alert threshold increase: `{missing['threshold_increase_pp']} pp`")
    lines.append("")
    for col, rec in missing["columns"].items():
        lines.append(
            f"- `{col}`: recent={rec['recent_missing_pct']}%, reference={rec['reference_missing_pct']}%, delta={rec['delta_pp']} pp"
        )

    lines.append("")
    lines.append("## Feature Drift (PSI)")
    lines.append("")
    drift = report["drift"]
    lines.append(f"- PSI threshold: `{drift['psi_threshold']}`")
    for col, rec in drift["columns"].items():
        lines.append(f"- `{col}`: psi={rec['psi']}")

    lines.append("")
    lines.append("## Performance")
    lines.append("")
    perf = report["performance"]
    comp = perf.get("comparison_snapshot")
    if comp:
        lines.append(
            f"- Best model by test F1: `{comp.get('best_model_by_test_f1')}` | val_f1={comp.get('validation_f1')} | test_f1={comp.get('test_f1')} | test_brier={comp.get('test_brier')}"
        )
    fw = perf.get("forward_window_f1")
    if fw:
        lines.append(
            f"- Forward-window F1 trend: early={fw['early_avg_f1']}, late={fw['late_avg_f1']}, delta={fw['delta']}"
        )

    lines.append("")
    lines.append("## Alerts")
    lines.append("")
    if not report["alerts"]:
        lines.append("- No alerts triggered.")
    else:
        for alert in report["alerts"]:
            lines.append(f"- `{alert['type']}`: `{json.dumps(alert, ensure_ascii=True)}`")
    lines.append("")
    return "\n".join(lines)


def build_arg_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="Generate monitoring report (missingness, drift, and performance trend).")
    p.add_argument("--config-path", type=str, default=str(DEFAULT_CONFIG_PATH))
    p.add_argument("--clean-path", type=str, default="data/processed/clean_data.csv")
    p.add_argument("--features-path", type=str, default="data/processed/features.csv")
    p.add_argument("--results-dir", type=str, default="results")
    p.add_argument("--out-json", type=str, default=str(DEFAULT_OUT_JSON))
    p.add_argument("--out-md", type=str, default=str(DEFAULT_OUT_MD))
    return p


def main() -> int:
    args = build_arg_parser().parse_args()
    config = _load_json(Path(args.config_path))
    clean_df = pd.read_csv(ROOT / args.clean_path, dtype={"site_id": "string"})
    features_df = pd.read_csv(ROOT / args.features_path, dtype={"site_id": "string"})
    clean_df["date"] = pd.to_datetime(clean_df["date"], errors="coerce")
    features_df["date"] = pd.to_datetime(features_df["date"], errors="coerce")

    missing = _build_missingness_section(clean_df, config)
    drift = _build_drift_section(features_df, config)
    perf = _build_performance_section(config, ROOT / args.results_dir)

    alerts = []
    alerts.extend(missing["alerts"])
    alerts.extend(drift["alerts"])
    alerts.extend(perf["alerts"])

    report = {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "status": "alert" if alerts else "ok",
        "alerts": alerts,
        "missingness": missing,
        "drift": drift,
        "performance": perf,
        "config_used": config,
    }

    out_json = Path(args.out_json)
    out_md = Path(args.out_md)
    out_json.parent.mkdir(parents=True, exist_ok=True)
    out_md.parent.mkdir(parents=True, exist_ok=True)
    out_json.write_text(json.dumps(report, indent=2), encoding="utf-8")
    out_md.write_text(_to_markdown(report), encoding="utf-8")
    print(f"Wrote {out_json.as_posix()}")
    print(f"Wrote {out_md.as_posix()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
