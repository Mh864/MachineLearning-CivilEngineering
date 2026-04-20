"""
run_ops.py - one-command operational run.

This wrapper runs:
1) refresh pipeline (with backup/rollback/status via ops/daily_refresh.py)
2) monitoring report generation (ops/monitoring_report.py)

It keeps core ML code unchanged and gives a clean single command for demos/scheduling.
"""
from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).parent


def _run(cmd: list[str], label: str) -> int:
    print(f"\n{'=' * 60}")
    print(f"  {label}")
    print(f"{'=' * 60}")
    return subprocess.run([sys.executable] + cmd, cwd=ROOT).returncode


def build_arg_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="One-command run: refresh + monitoring")
    p.add_argument("--start-date", type=str, default="2018-01-01")
    p.add_argument("--end-date", type=str, default="2024-12-31")
    p.add_argument("--model-type", choices=["baseline", "lightgbm", "both"], default="both")
    p.add_argument("--skip-fetch", action="store_true")
    p.add_argument("--no-calibration", action="store_true")
    p.add_argument("--with-stage", action="store_true", help="Include stage regression training/evaluation.")
    p.add_argument("--skip-monitoring", action="store_true", help="Only run refresh, skip monitoring report.")
    return p


def main() -> int:
    args = build_arg_parser().parse_args()

    refresh_cmd = [
        "ops/daily_refresh.py",
        "--start-date",
        args.start_date,
        "--end-date",
        args.end_date,
        "--model-type",
        args.model_type,
    ]
    if args.skip_fetch:
        refresh_cmd.append("--skip-fetch")
    if args.no_calibration:
        refresh_cmd.append("--no-calibration")
    if args.with_stage:
        refresh_cmd.append("--with-stage")

    refresh_code = _run(refresh_cmd, "Step A: Refresh data/models/evaluation")
    if refresh_code != 0:
        print("\nRefresh failed. Monitoring step will not run.")
        return refresh_code

    if not args.skip_monitoring:
        monitor_code = _run(["ops/monitoring_report.py"], "Step B: Generate monitoring report")
        if monitor_code != 0:
            print("\nMonitoring failed.")
            return monitor_code

    print("\nOne-command operational run complete.")
    print("Artifacts:")
    print("  - results/ops/last_refresh_status.json")
    print("  - results/ops/logs/")
    if not args.skip_monitoring:
        print("  - results/monitoring_report.json")
        print("  - results/monitoring_report.md")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
