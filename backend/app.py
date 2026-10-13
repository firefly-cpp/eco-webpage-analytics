from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, ConfigDict, Field

from website_data_collection_engine import WebsiteMeasurementEngine
from carbon_footprint_estimation_engine import (
    add_carbon_data,
    carbon_factors,
    get_carbon_factor
)

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
    visitor_location: str = "WORLD"
    hosting_location: str = "WORLD"

class ImageTranscodingData(BaseModel):
    model_config = ConfigDict(extra="allow")

    saved_bytes: int = Field(ge=0, strict=True)


class MeasurementData(BaseModel):
    model_config = ConfigDict(extra="allow")

    url: str
    total_bytes: int = Field(ge=0, strict=True)
    image_transcoding: ImageTranscodingData | None = None


class RecalculateRequest(BaseModel):
    url: str
    visitor_location: str = "WORLD"
    hosting_location: str = "WORLD"

    baseline: MeasurementData
    full_scroll: MeasurementData
    without_third_party: MeasurementData

@app.get("/api/locations")
def get_locations():
    locations = []

    for location_code, factor in carbon_factors.items():
        locations.append({
            "location_code": location_code,
            "name": factor["name"],
            "carbon_intensity": factor["carbon_intensity"],
            "year": factor["year"]
        })

    #sort alphabetically by their displayed name
    locations.sort(key=lambda location: location["name"])

    return locations

@app.post("/api/analyze")
def analyze(data: AnalyzeRequest):
    visitor_location = data.visitor_location.strip().upper()
    hosting_location = data.hosting_location.strip().upper()

    try:
        get_carbon_factor(visitor_location)
        get_carbon_factor(hosting_location)
        get_carbon_factor("WORLD")
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    try:
        measurement = engine.measure_url(data.url)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    return {
        "url": measurement["url"],
        "baseline": add_carbon_data(measurement["baseline"], visitor_location, hosting_location),
        "full_scroll": add_carbon_data(measurement["full_scroll"], visitor_location, hosting_location),
        "without_third_party": add_carbon_data(measurement["without_third_party"], visitor_location, hosting_location)
    }

@app.post("/api/recalculate")
def recalculate(data: RecalculateRequest):
    visitor_location = data.visitor_location.strip().upper()
    hosting_location = data.hosting_location.strip().upper()

    try:
        get_carbon_factor(visitor_location)
        get_carbon_factor(hosting_location)
        get_carbon_factor("WORLD")

        return {
            "url": data.url,

            "baseline": add_carbon_data(
                data.baseline.model_dump(exclude_none=True),
                visitor_location,
                hosting_location
            ),

            "full_scroll": add_carbon_data(
                data.full_scroll.model_dump(exclude_none=True),
                visitor_location,
                hosting_location
            ),

            "without_third_party": add_carbon_data(
                data.without_third_party.model_dump(exclude_none=True),
                visitor_location,
                hosting_location
            )
        }

    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc