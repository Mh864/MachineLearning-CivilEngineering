from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MODELS_DIR = ROOT / "models"
OPS_DIR = ROOT / "results" / "ops"
STATUS_PATH = OPS_DIR / "last_refresh_status.json"
LOGS_DIR = OPS_DIR / "logs"
BACKUP_DIR = OPS_DIR / "model_backups"
MODEL_FILES = ["model.pkl", "lgbm_model.pkl"]


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _ts_slug(dt: datetime) -> str:
    return dt.strftime("%Y%m%dT%H%M%SZ")


def _run_pipeline(
    *,
    start_date: str,
    end_date: str,
    model_type: str,
    skip_fetch: bool,
    no_calibration: bool,
    log_path: Path,
) -> tuple[int, list[str]]:
    cmd: list[str] = [
        sys.executable,
        "run_pipeline.py",
        "--start-date",
        start_date,
        "--end-date",
        end_date,
        "--model-type",
        model_type,
    ]
    if skip_fetch:
        cmd.append("--skip-fetch")
    if no_calibration:
        cmd.append("--no-calibration")

    proc = subprocess.run(
        cmd,
        cwd=ROOT,
        capture_output=True,
        text=True,
    )
    combined = []
    if proc.stdout:
        combined.append(proc.stdout)
    if proc.stderr:
        combined.append("\n[stderr]\n")
        combined.append(proc.stderr)
    log_path.write_text("".join(combined), encoding="utf-8")
    return proc.returncode, cmd


def _backup_models(timestamp: str) -> list[dict[str, str]]:
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    MODELS_DIR.mkdir(parents=True, exist_ok=True)
    records: list[dict[str, str]] = []
    for model_name in MODEL_FILES:
        src = MODELS_DIR / model_name
        if not src.exists():
            continue
        dst = BACKUP_DIR / f"{timestamp}_{model_name}"
        shutil.copy2(src, dst)
        records.append({"model": model_name, "backup_path": str(dst.relative_to(ROOT))})
    return records


def _restore_models(backups: list[dict[str, str]]) -> list[str]:
    restored: list[str] = []
    MODELS_DIR.mkdir(parents=True, exist_ok=True)
    for rec in backups:
        rel = rec["backup_path"]
        src = ROOT / rel
        dst = MODELS_DIR / rec["model"]
        if src.exists():
            shutil.copy2(src, dst)
            restored.append(rec["model"])
    return restored


def _write_status(payload: dict) -> None:
    OPS_DIR.mkdir(parents=True, exist_ok=True)
    STATUS_PATH.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def build_arg_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="Daily operational refresh wrapper around run_pipeline.py")
    p.add_argument("--start-date", type=str, default="2018-01-01")
    p.add_argument("--end-date", type=str, default="2024-12-31")
    p.add_argument("--model-type", choices=["baseline", "lightgbm", "both"], default="both")
    p.add_argument("--skip-fetch", action="store_true", help="Skip USGS fetch step in run_pipeline.py")
    p.add_argument("--no-calibration", action="store_true", help="Train uncalibrated models")
    return p


def main() -> int:
    args = build_arg_parser().parse_args()
    LOGS_DIR.mkdir(parents=True, exist_ok=True)
    started_at = _utc_now()
    stamp = _ts_slug(started_at)
    log_path = LOGS_DIR / f"refresh_{stamp}.log"

    backups = _backup_models(stamp)

    code, cmd = _run_pipeline(
        start_date=args.start_date,
        end_date=args.end_date,
        model_type=args.model_type,
        skip_fetch=bool(args.skip_fetch),
        no_calibration=bool(args.no_calibration),
        log_path=log_path,
    )

    finished_at = _utc_now()
    status: dict[str, object] = {
        "status": "success" if code == 0 else "failed",
        "started_at_utc": started_at.isoformat(),
        "finished_at_utc": finished_at.isoformat(),
        "duration_seconds": round((finished_at - started_at).total_seconds(), 2),
        "command": cmd,
        "log_path": str(log_path.relative_to(ROOT)),
        "args": {
            "start_date": args.start_date,
            "end_date": args.end_date,
            "model_type": args.model_type,
            "skip_fetch": bool(args.skip_fetch),
            "no_calibration": bool(args.no_calibration),
        },
        "model_backups": backups,
    }

    if code != 0:
        restored = _restore_models(backups)
        status["restored_models_after_failure"] = restored
        status["reason"] = "Pipeline command failed; previous model artifacts were restored from backups."
    _write_status(status)

    print(json.dumps(status, indent=2))
    return code


if __name__ == "__main__":
    raise SystemExit(main())
