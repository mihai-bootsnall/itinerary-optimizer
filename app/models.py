from __future__ import annotations

from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class CabinClass(str, Enum):
    ECONOMY = "Y"
    PREMIUM_ECONOMY = "W"
    BUSINESS = "C"
    FIRST = "F"


class PassengerType(str, Enum):
    ADULT = "ADT"
    CHILD = "CHD"
    INFANT = "INF"


class Passenger(BaseModel):
    type: PassengerType
    count: int = Field(ge=1)


class Leg(BaseModel):
    origin: str = Field(min_length=3, max_length=3, description="IATA airport code")
    destination: str = Field(min_length=3, max_length=3, description="IATA airport code")
    date: str = Field(description="Departure date in Y-m-d format")
    surface_segment: bool = False
    cabin_class: CabinClass | None = None
    flexible_date: bool | None = None
    allow_airport_change: bool | None = None
    allow_nearby_locations: bool | None = None
    preferred_airlines: list[str] = Field(default_factory=list)
    excluded_airlines: list[str] = Field(default_factory=list)


class GlobalSettings(BaseModel):
    cabin_class: CabinClass = CabinClass.ECONOMY
    flexible_date: bool = False
    allow_airport_change: bool = False
    allow_nearby_locations: bool = False
    preferred_airlines: list[str] = Field(default_factory=list)
    excluded_airlines: list[str] = Field(default_factory=list)
    passengers: list[Passenger] = Field(default_factory=lambda: [Passenger(type=PassengerType.ADULT, count=1)])


class Strategy(str, Enum):
    BEST_PRICE = "best_price"
    SHORTEST_TIME = "shortest_time"
    FEWEST_STOPS = "fewest_stops"
    BEST_CHOICE = "best_choice"


class ItineraryRequest(BaseModel):
    legs: list[Leg] = Field(min_length=1)
    settings: GlobalSettings = Field(default_factory=GlobalSettings)
    strategies: list[Strategy] = Field(
        default_factory=list,
        description="Which strategies to compute. Empty = use server default (all four if unconfigured).",
    )
    verbose: bool = Field(
        default=False,
        description="Include AI reasoning and per-group notes in response.",
    )


class SearchGroup(BaseModel):
    """A single Amadeus search request — up to 6 legs."""
    legs: list[Leg]
    note: str = Field(default="", description="Why this grouping was chosen")


class SplitOption(BaseModel):
    """One way to split the full itinerary into Amadeus-searchable groups."""
    strategy: Strategy
    searches: list[SearchGroup]


class ItineraryResponse(BaseModel):
    options: list[SplitOption]
    total_legs: int
    raw_reasoning: str = Field(default="", description="AI agent's reasoning (verbose mode only)")
