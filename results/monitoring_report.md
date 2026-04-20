# Monitoring Report

- Generated at (UTC): `2026-04-20T14:51:27.604103+00:00`
- Overall status: `alert`
- Total alerts: `4`

## Missingness

- Recent rows: `297`
- Reference rows: `1800`
- Alert threshold increase: `10.0 pp`

- `discharge`: recent=0.337%, reference=0.333%, delta=0.003 pp
- `stage`: recent=69.697%, reference=70.333%, delta=-0.636 pp

## Feature Drift (PSI)

- PSI threshold: `0.2`
- `discharge_lag1`: psi=0.241
- `discharge_roll_mean_7`: psi=0.2922
- `prcp_roll_sum_7`: psi=0.0
- `month_sin`: psi=9.9185
- `month_cos`: psi=13.2306

## Performance

- Best model by test F1: `lightgbm_multiclass` | val_f1=None | test_f1=None | test_brier=None

## Alerts

- `drift`: `{"type": "drift", "column": "discharge_lag1", "psi": 0.241, "threshold": 0.2}`
- `drift`: `{"type": "drift", "column": "discharge_roll_mean_7", "psi": 0.2922, "threshold": 0.2}`
- `drift`: `{"type": "drift", "column": "month_sin", "psi": 9.9185, "threshold": 0.2}`
- `drift`: `{"type": "drift", "column": "month_cos", "psi": 13.2306, "threshold": 0.2}`
