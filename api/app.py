from __future__ import annotations

from typing import Optional

from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware

from api.predict import load_model_artifact, predict_from_recent_discharge


app = FastAPI(title="Flood Risk Prediction API", version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

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
    recent_prcp: Optional[str] = Query(
        None,
        description="Optional comma-separated PRCP(mm) values oldest->newest (>=7). Defaults to zeros when omitted.",
    ),
    tmax: Optional[float] = Query(None, description="Optional same-day max temperature."),
    tmin: Optional[float] = Query(None, description="Optional same-day min temperature."),
    awnd: Optional[float] = Query(None, description="Optional average wind speed."),
    snow: Optional[float] = Query(None, description="Optional snowfall amount."),
    snow_depth: Optional[float] = Query(None, description="Optional snow depth."),
    heavy_rain_threshold: float = Query(20.0, description="Threshold for heavy_rain_flag_1d from PRCP."),
):
    global _artifact
    if _artifact is None:
        _artifact = load_model_artifact("models/model.pkl")

    recent = [float(x.strip()) for x in recent_discharge.split(",") if x.strip() != ""]
    pred = predict_from_recent_discharge(
        artifact=_artifact,
        recent_discharge=recent,
        as_of_date=as_of_date,
        recent_prcp=recent_prcp,
        tmax=tmax,
        tmin=tmin,
        awnd=awnd,
        snow=snow,
        snow_depth=snow_depth,
        heavy_rain_threshold=heavy_rain_threshold,
    )

    return {
        "site_id": site_id,
        "prediction": pred,
    }

