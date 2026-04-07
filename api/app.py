from __future__ import annotations

from typing import Optional

from fastapi import FastAPI, Query

from api.predict import load_model_artifact, predict_from_recent_discharge


app = FastAPI(title="Flood Risk Prediction API", version="0.1.0")

_artifact = None


@app.on_event("startup")
def _startup() -> None:
    global _artifact
    _artifact = load_model_artifact("models/model.pkl")


@app.get("/predict")
def predict(
    site_id: str = Query(..., description="USGS site id (currently not used by baseline model)"),
    recent_discharge: str = Query(
        ...,
        description="Comma-separated discharge values ordered oldest->newest (need >=7). Example: 100,110,120,130,140,150,160",
    ),
    as_of_date: Optional[str] = Query(None, description="YYYY-MM-DD used for month feature; defaults to today (UTC)."),
):
    global _artifact
    if _artifact is None:
        _artifact = load_model_artifact("models/model.pkl")

    recent = [float(x.strip()) for x in recent_discharge.split(",") if x.strip() != ""]
    pred = predict_from_recent_discharge(artifact=_artifact, recent_discharge=recent, as_of_date=as_of_date)

    return {
        "site_id": site_id,
        "prediction": pred,
    }

