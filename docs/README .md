# Flood Risk Prediction System
Civil Engineering Machine Learning Project — 2025-2026
Team: Jerome Chaker · Mia Hajjar · Hady Souaiby · Yoanna Maroun

===================================================================

## What is this?

We built a system that predicts whether a river will flood tomorrow
using real government data. You pick a river station, the system
automatically loads the last 7 days of real discharge and weather
data, runs it through a trained machine learning model, and gives
you a flood risk prediction for the next day.

The prediction comes in three levels:
- Normal — the river is within its usual range, nothing to worry about
- Medium — the river is higher than normal, worth monitoring
- High — the river is in flood territory, risk is real

This is a real end-to-end system — real data, real models, real API,
real dashboard. Not a notebook.

========================================================================

## Team

| Name | Branch |
|------|--------|
| Jerome Chaker | jerome_chaker |
| Mia Hajjar | mia_hajjar |
| Hady Souaiby | Hady_Souaiby |
| Yoanna Maroun | yoanna_maroun |

=======================================================================

## The 11 river stations

We cover 11 gauge stations across the United States, chosen to
represent diverse climates, river sizes, and hydrological behaviors:

| Site ID | River | State |
|---------|-------|-------|
| 01646500 | Potomac River | MD |
| 02087500 | Neuse River | NC |
| 03015500 | Allegheny River | PA |
| 03303000 | Ohio River | KY |
| 05054000 | Red River | ND |
| 06710247 | Cherry Creek | CO |
| 07374000 | Mississippi River | LA |
| 08066500 | Trinity River | TX |
| 11425500 | Sacramento River | CA |
| 12301933 | Clark Fork | MT |
| 14211720 | Willamette River | OR |

===================================================================

## Data sources

USGS (United States Geological Survey):
Daily river discharge (ft³/s) and stage (ft) for all 11 stations
from 2018 to 2024. Around 28,000 daily observations total.
Source: https://api.waterdata.usgs.gov/

NOAA (National Oceanic and Atmospheric Administration):
Daily weather data including precipitation, temperature, wind speed,
and snowfall matched to each river station.
Source: https://www.ncdc.noaa.gov/cdo-web/

=====================================================================

## Results

| Model | Validation F1 | Test F1 |
|-------|--------------|---------|
| Logistic Regression (baseline) | 0.843 | 0.867 |
| LightGBM (strong model) | 0.886 | 0.904 |

The model predicts flood risk reliably at 1-2 day horizons.
Accuracy drops significantly beyond 3 days which is expected
for river forecasting systems.

======================================================================

## Requirements

- Python 3.10+
- Node.js 18+
- pip packages: see `requirements.txt`

========================================================================

## How to install

```bash
pip install -r requirements.txt
```

==========================================================================

## How to run

You need two terminals open at the same time.

Terminal 1 — Start the backend:
```bash
python run_api.py
```
API runs at `http://localhost:8000`
Docs at `http://localhost:8000/docs`

Terminal 2 — Start the frontend:
```bash
cd frontend1
npm install
npm run dev
```
Dashboard runs at `http://localhost:3000`

==================================================================

## How to use the dashboard

1. Open `http://localhost:3000` in your browser
2. Select a river station from the list
3. The last 7 days of real data loads automatically
4. Click "Predict" to get the flood risk for tomorrow
5. The result shows the probability of Normal, Medium and High risk
   along with a discharge trend chart and stage forecast

=======================================================================

## Run the full pipeline

To retrain everything from scratch with one command:

```bash
python run_pipeline.py --skip-fetch
```

This automatically runs data cleaning, feature engineering,
training both models, evaluation and comparison in the correct order.

If you also want to re-download the data:

```bash
python run_pipeline.py --start-date 2018-01-01 --end-date 2024-12-31
```

========================================================================

## API endpoints

| Endpoint | What it does |
|----------|-------------|
| `GET /health` | Check if the API is running and which model is loaded |
| `GET /latest?site_id=01646500` | Get last 7 days of real discharge and weather |
| `GET /predict?site_id=01646500&recent_discharge=...` | Get flood risk probabilities |
| `GET /predict-stage?site_id=01646500&recent_stage=...` | Get predicted river height tomorrow |

Example prediction:
GET /predict?site_id=02087500&recent_discharge=500,600,800,1000,1500,2000,3000

Response:
```json
{
  "site_id": "02087500",
  "prediction": 2,
  "probability": {
    "normal": 0.05,
    "medium": 0.18,
    "high": 0.77
  }
}
```

================================================================================

## Project structure
├── api/                  FastAPI backend (endpoints + inference)
├── data/
│   ├── raw/usgs/         Raw USGS discharge CSV files
│   ├── raw/noaa/         NOAA weather CSV files per station
│   └── processed/        Cleaned and feature-engineered data
├── data_ingestion/       Scripts to download USGS and NOAA data
├── data_processing/      Script to clean and align raw data
├── modeling/             Feature engineering, training, evaluation
├── models/               Trained model artifacts (.pkl files)
├── ops/                  Monitoring and automated refresh scripts
├── frontend/             Next.js dashboard
├── results/              Metrics, comparisons, monitoring reports
├── tests/                Feature parity tests
└── run_pipeline.py       Runs the full ML pipeline in one command

==================================================================================

## Monitoring

```bash
python run_ops.py
```

Checks for feature drift, data quality issues, and model performance
degradation. Results saved in `results/monitoring_report.md`.

==================================================================================

## Tests

```bash
python -m pytest tests/test_feature_parity.py -v
```

Verifies that the API uses exactly the same features the model
was trained on.

================================================================================

## Docker

```bash
docker pull hadysouaiby/flood-risk-prediction:latest
docker run -p 8000:8000 hadysouaiby/flood-risk-prediction:latest
```

See `docker/README.md` for full Docker deployment instructions.