from fastapi import FastAPI
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


class AnalyzeRequest(BaseModel):
    url: str


@app.post("/api/analyze")
def analyze(data: AnalyzeRequest):
    engine = WebsiteMeasurementEngine()

    measurement_result = engine.measure_urls(
        [data.url],
        repeat_runs=1
    )

    measurement = measurement_result[0]

    carbon_result = calculate_co2(measurement)

    return {
        **measurement,
        **carbon_result
    }