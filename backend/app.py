from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from website_data_collection_engine import WebsiteMeasurementEngine
from carbon_footprint_estimation_engine import calculate_co2

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:8080",
        "http://127.0.0.1:8080",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

engine = WebsiteMeasurementEngine()

class AnalyzeRequest(BaseModel):
    url: str


@app.post("/api/analyze")
def analyze(data: AnalyzeRequest):
    try:
        measurement = engine.measure_url(data.url)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    carbon_result = calculate_co2(measurement)

    return {
        **measurement,
        **carbon_result
    }