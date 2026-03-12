from fastapi import FastAPI, HTTPException

from app.agent import split_itinerary
from app.models import ItineraryRequest, ItineraryResponse

app = FastAPI(
    title="Itinerary Optimizer",
    description="AI-powered flight itinerary splitting for Amadeus searches",
    version="0.1.0",
)


@app.post("/split", response_model=ItineraryResponse, response_model_exclude_none=True, response_model_exclude_defaults=True)
async def split(request: ItineraryRequest) -> ItineraryResponse:
    """Split a multi-leg itinerary into optimized Amadeus search groups."""
    try:
        return await split_itinerary(request)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@app.get("/health")
async def health() -> dict:
    return {"status": "ok"}
