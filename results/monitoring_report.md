# Monitoring Report

- Generated at (UTC): `2026-04-20T13:35:57.460673+00:00`
- Overall status: `alert`
- Total alerts: `5`

## Missingness

- Recent rows: `300`
- Reference rows: `1800`
- Alert threshold increase: `10.0 pp`

- `discharge`: recent=0.0%, reference=0.0%, delta=0.0 pp
- `stage`: recent=70.0%, reference=70.111%, delta=-0.111 pp

## Feature Drift (PSI)

- PSI threshold: `0.2`
- `discharge_lag1`: psi=0.5037
- `discharge_roll_mean_7`: psi=0.5264
- `prcp_roll_sum_7`: psi=0.0867
- `month`: psi=12.2597

## Performance

- Best model by test F1: `lightgbm` | val_f1=0.7258278145695364 | test_f1=0.7645739910313901 | test_brier=0.039610024218929625
- Forward-window F1 trend: early=0.7974, late=0.6726, delta=-0.1248

## Alerts

- `drift`: `{"type": "drift", "column": "discharge_lag1", "psi": 0.5037, "threshold": 0.2}`
- `drift`: `{"type": "drift", "column": "discharge_roll_mean_7", "psi": 0.5264, "threshold": 0.2}`
- `drift`: `{"type": "drift", "column": "month", "psi": 12.2597, "threshold": 0.2}`
- `performance_f1_drop`: `{"type": "performance_f1_drop", "early_avg_f1": 0.7974, "late_avg_f1": 0.6726, "drop": 0.1248}`
- `performance_brier_high`: `{"type": "performance_brier_high", "test_brier": 0.0396, "threshold": 0.02}`
