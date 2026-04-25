# Monitoring Report

- Generated at (UTC): `2026-04-25T13:37:14.770860+00:00`
- Overall status: `alert`
- Total alerts: `4`

## Missingness

- Recent rows: `330`
- Reference rows: `1980`
- Alert threshold increase: `10.0 pp`

- `discharge`: recent=0.0%, reference=0.0%, delta=0.0 pp
- `stage`: recent=63.636%, reference=63.737%, delta=-0.101 pp

## Feature Drift (PSI)

- PSI threshold: `0.2`
- `discharge_lag1`: psi=1.4487
- `discharge_roll_mean_7`: psi=1.5739
- `prcp_roll_sum_7`: psi=0.0874
- `month_sin`: psi=8.9283
- `month_cos`: psi=12.2597

## Performance

- Best model by test F1: `lightgbm_multiclass` | val_f1=None | test_f1=None | test_brier=None

## Alerts

- `drift`: `{"type": "drift", "column": "discharge_lag1", "psi": 1.4487, "threshold": 0.2}`
- `drift`: `{"type": "drift", "column": "discharge_roll_mean_7", "psi": 1.5739, "threshold": 0.2}`
- `drift`: `{"type": "drift", "column": "month_sin", "psi": 8.9283, "threshold": 0.2}`
- `drift`: `{"type": "drift", "column": "month_cos", "psi": 12.2597, "threshold": 0.2}`
